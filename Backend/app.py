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

@app.get("/authors")
def list_authors():
    return {"authors": get_authors()}

@app.post("/rewrite")
def rewrite(req: RewriteRequest):
    try:
        result = rag_author_rewrite(req.text, req.author)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
