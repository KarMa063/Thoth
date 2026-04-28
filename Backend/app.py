from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from rag import ArtifactStore, EmbedderService, AuthorRegistry, RetrieverService
from generation import LLMLoader, PromptBuilder, Reranker, GenerationService
from analysis import StyleAnalyser

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = Config()
    
    # 1. RAG Components
    store = ArtifactStore(cfg)
    store.load()
    
    emb = EmbedderService(cfg)
    emb.load()
    
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
