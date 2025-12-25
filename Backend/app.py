from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from author_rag import rag_author_rewrite, get_authors

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


@app.get("/authors")
def list_authors():
    return {"authors": get_authors()}
    
@app.post("/rewrite")
def rewrite(req: RewriteRequest):
    try:
        print("Rewrite request received")
        result = rag_author_rewrite(req.text, req.author, req.force_lang)
        print("Rewrite completed")
        return result
    except Exception as e:
        print("Rewrite error:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

