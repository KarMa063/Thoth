from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from author_rag import rag_author_rewrite, get_authors
from continuation import rag_author_continue
from style_analysis import analyze_text_style

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Thoth Author Tone Backend")

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
    force_lang: str | None = None

class ContinueRequest(BaseModel):
    text: str
    author: str

class AnalyzeRequest(BaseModel):
    text: str
    use_llm: bool = False
    include_centroid: bool = True


@app.get("/authors")
def list_authors():
    print("Authors request received", flush=True)
    return {"authors": get_authors()}
    
@app.post("/rewrite")
def rewrite(req: RewriteRequest):
    try:
        print("Rewrite request received", flush=True)
        result = rag_author_rewrite(req.text, req.author, req.force_lang)
        print("Rewrite completed", flush=True)
        return result
    except Exception as e:
        print("Rewrite error:", repr(e), flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/continue")
def continue_text(req: ContinueRequest):
    try:
        print(f"Continuation request received for author: {req.author}", flush=True)
        continuation = rag_author_continue(req.text, req.author)
        print("Continuation completed", flush=True)
        return {"continuation": continuation, "author": req.author}
    except Exception as e:
        print("Continuation error:", repr(e), flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
def analyze_text(req: AnalyzeRequest):
    try:
        print("Analysis request received", flush=True)
        result = analyze_text_style(req.text)
        print("Analysis completed", flush=True)
        return result
    except Exception as e:
        print("Analysis error:", repr(e), flush=True)
        raise HTTPException(status_code=500, detail=str(e))


