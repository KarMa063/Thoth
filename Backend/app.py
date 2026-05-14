from contextlib import asynccontextmanager
from io import BytesIO
from typing import List
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from rag import ArtifactStore, EmbedderService, AuthorRegistry, RetrieverService, UserTextStore
from rag.user_text_store import clean_uploaded_text, count_words
from generation import LLMLoader, PromptBuilder, Reranker, GenerationService
from analysis import StyleAnalyser


SUPPORTED_AUTHOR_FILE_TYPES = (".txt", ".docx")


def sync_user_authors(request: Request) -> None:
    store: ArtifactStore = request.app.state.store
    registry: AuthorRegistry = request.app.state.registry
    user_text_store: UserTextStore = request.app.state.user_text_store
    embedder: EmbedderService = request.app.state.embedder
    cfg: Config = request.app.state.config
    revision = user_text_store.database_revision()
    if revision == getattr(request.app.state, "user_db_revision", None):
        return

    user_text_store.backfill_embeddings(embedder, cfg.embed_model)
    store.set_user_chunks(user_text_store.list_chunks())
    registry.build()
    request.app.state.user_db_revision = user_text_store.database_revision()


def extract_uploaded_text(filename: str, raw_bytes: bytes) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(".txt"):
        try:
            return raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw_bytes.decode("cp1252", errors="ignore")

    if lower_name.endswith(".docx"):
        try:
            from docx import Document
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail="DOCX upload support is not installed. Run pip install -r requirements.txt.",
            ) from exc

        doc = Document(BytesIO(raw_bytes))
        paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return "\n\n".join(paragraphs)

    raise HTTPException(status_code=400, detail="Please upload a .txt or .docx file.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = Config()
    
    # 1. RAG Components
    store = ArtifactStore(cfg)
    store.load()

    user_text_store = UserTextStore(cfg)
    user_text_store.init_db()
    
    emb = EmbedderService(cfg)
    emb.load()
    user_text_store.seed_base_corpus_embeddings(
        store.base_chunks,
        store.faiss_index,
        cfg.embed_model,
        embedder=emb,
    )
    user_text_store.backfill_embeddings(emb, cfg.embed_model)
    store.add_chunks(user_text_store.list_chunks())
    
    registry = AuthorRegistry(cfg, store, emb)
    registry.build()
    
    retriever = RetrieverService(cfg, store, emb)
    
    # 2. Generation Components
    loader = LLMLoader(cfg)
    loader.load()
    
    prompt_builder = PromptBuilder()
    reranker = Reranker(cfg, emb, registry)
    
    app.state.gen_service = GenerationService(cfg, registry, retriever, loader, prompt_builder, reranker)
    app.state.analyser = StyleAnalyser(emb, registry)
    app.state.registry = registry
    app.state.store = store
    app.state.user_text_store = user_text_store
    app.state.config = cfg
    app.state.embedder = emb
    app.state.user_db_revision = user_text_store.database_revision()
    
    yield

app = FastAPI(title="Thoth Author Tone Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RewriteRequest(BaseModel):
    text: str
    author: str

class ContinueRequest(BaseModel):
    text: str
    author: str

class AnalyzeRequest(BaseModel):
    text: str
    use_llm: bool = False
    include_centroid: bool = True


@app.get("/authors")
def list_authors(request: Request):
    print("Authors request received", flush=True)
    registry: AuthorRegistry = request.app.state.registry
    return {"authors": registry.get_authors()}

@app.post("/authors/reload")
def reload_authors(request: Request):
    print("Authors reload requested", flush=True)
    sync_user_authors(request)
    registry: AuthorRegistry = request.app.state.registry
    return {"authors": registry.get_authors()}

@app.post("/authors")
async def add_author_sample(
    request: Request,
    author: str = Form(...),
    files: List[UploadFile] = File(...),
):
    author = author.strip()
    if len(author) < 2:
        raise HTTPException(status_code=400, detail="Author name must be at least 2 characters.")
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one .txt or .docx file.")

    try:
        cfg: Config = request.app.state.config
        user_text_store: UserTextStore = request.app.state.user_text_store
        store: ArtifactStore = request.app.state.store
        registry: AuthorRegistry = request.app.state.registry
        embedder: EmbedderService = request.app.state.embedder

        filenames = []
        extracted_texts = []
        for file in files:
            if not file.filename or not file.filename.lower().endswith(SUPPORTED_AUTHOR_FILE_TYPES):
                raise HTTPException(status_code=400, detail="Please upload only .txt or .docx files.")

            raw_bytes = await file.read()
            raw_text = extract_uploaded_text(file.filename, raw_bytes)
            cleaned_part = clean_uploaded_text(raw_text)
            if cleaned_part:
                filenames.append(file.filename)
                extracted_texts.append(cleaned_part)

        cleaned_text = clean_uploaded_text("\n\n".join(extracted_texts))
        word_count = count_words(cleaned_text)
        if word_count < cfg.min_author_sample_words:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Uploaded files have {word_count} words after cleaning. "
                    f"Please upload at least {cfg.min_author_sample_words} words."
                ),
            )

        source_filename = ", ".join(filenames)
        chunks = user_text_store.add_sample(
            author,
            cleaned_text,
            source_filename,
            embedder=embedder,
            embedding_model=cfg.embed_model,
        )
        store.add_chunks(chunks)
        registry.build()

        return {
            "author": author,
            "filenames": filenames,
            "files_processed": len(filenames),
            "word_count": word_count,
            "chunks_added": len(chunks),
            "authors": registry.get_authors(),
        }
    except HTTPException:
        raise
    except Exception as e:
        print("Add author sample error:", repr(e), flush=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/rewrite")
def rewrite(req: RewriteRequest, request: Request):
    try:
        print("Rewrite request received", flush=True)
        gen_service: GenerationService = request.app.state.gen_service
        result = gen_service.rewrite(req.text, req.author)
        print("Rewrite completed", flush=True)
        # Frontend expects 'rewritten' key
        result["rewritten"] = result.get("output", "")
        return result
    except Exception as e:
        print("Rewrite error:", repr(e), flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/continue")
def continue_text(req: ContinueRequest, request: Request):
    try:
        print(f"Continuation request received for author: {req.author}", flush=True)
        gen_service: GenerationService = request.app.state.gen_service
        result = gen_service.continue_text(req.text, req.author)
        # result is a dict with 'output' key; frontend expects 'continuation' as a string
        continuation_text = result.get("output", "") if isinstance(result, dict) else str(result)
        print("Continuation completed", flush=True)
        return {"continuation": continuation_text, "author": req.author}
    except Exception as e:
        print("Continuation error:", repr(e), flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
def analyze_text(req: AnalyzeRequest, request: Request):
    try:
        print("Analysis request received", flush=True)
        analyser: StyleAnalyser = request.app.state.analyser
        result = analyser.analyse(req.text)
        print("Analysis completed", flush=True)
        return result
    except Exception as e:
        print("Analysis error:", repr(e), flush=True)
        raise HTTPException(status_code=500, detail=str(e))
