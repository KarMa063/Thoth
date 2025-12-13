# Author-Tone RAG Rewriter
# Loads:
#   - model/           (FLAN-T5 model + tokenizer)
#   - faiss.index      (vector index of corpus embeddings)
#   - chunks.pkl       (list of corpus text chunks)

import os
import json
import pickle
import re
from typing import List, Dict, Any
from collections import Counter

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer
import faiss


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Paths
MODEL_DIR = "./model"
FAISS_PATH = "./faiss.index"
CHUNKS_PATH = "./chunks.pkl"

# Load FAISS + chunks
if not os.path.exists(CHUNKS_PATH):
    raise RuntimeError("chunks.pkl not found. Place it inside Backend/")

if not os.path.exists(FAISS_PATH):
    raise RuntimeError("faiss.index not found. Place it inside Backend/")

print("[author_rag] Loading chunks.pkl …")
with open(CHUNKS_PATH, "rb") as f:
    corpus_chunks = pickle.load(f)

AUTHORS = sorted({c["author"] for c in corpus_chunks})
print("[author_rag] Authors:", AUTHORS)

print("[author_rag] Loading FAISS index …")
faiss_index = faiss.read_index(FAISS_PATH)

# Load embedding model
print("[author_rag] Loading embedder …")
embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
embedder.max_seq_length = 384

# Load generator model
print("[author_rag] Loading generator model …")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
gen_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR).to(DEVICE)
gen_model.eval()
print("[author_rag] Generator model ready.")

# Stylometric functions
STOP_EN = set("""
the a an and or but if when while as of to for in on at by from with into after before over under again further then once
is are was were be been being it its himself herself themselves itself he him his she her hers we our ours you your yours they them their theirs
that this these those who whom which what where why how not no nor do does did done so such than too very can will just
""".split())

def tokenize_words(text): return re.findall(r"\w+|\S", text)
def sent_split_simple(text): return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

def stylometrics_en(text: str) -> Dict[str, Any]:
    sents = sent_split_simple(text)
    words = re.findall(r"[^\W\d_]+", text)
    T = len(words)
    types = len(set([w.lower() for w in words]))
    avg_len = float(np.mean([len(tokenize_words(s)) for s in sents] or [0]))
    std_len = float(np.std([len(tokenize_words(s)) for s in sents] or [0]))
    puncts = len(re.findall(r"[,:;—–\"'…]", text))
    pden = puncts / max(1, len(text))
    anchors = [w for w,_ in Counter([t.lower() for t in re.findall(r"[^\W\d_]+", text) if t.lower() not in STOP_EN]).most_common(12)]
    
    return {
        "ttr": round(types / T, 4) if T else 0,
        "avg_sent_len": round(avg_len, 2),
        "std_sent_len": round(std_len, 2),
        "punct_density": round(pden, 4),
        "anchors": anchors
    }

# RAG RETRIEVAL
def retrieve_exemplars(query_text: str, target_author: str, top_k: int = 8):
    qv = embedder.encode([query_text], convert_to_numpy=True, normalize_embeddings=True)
    sims, ids = faiss_index.search(qv, k=min(top_k*6, len(corpus_chunks)))
    
    hits = []
    for idx in ids[0]:
        row = corpus_chunks[idx]
        if row["author"].lower() == target_author.lower():
            hits.append(row)
        if len(hits) >= top_k:
            break
    return hits

def summarize_exemplars(exemplars):
    return "\n".join([f"[{ex['author']}] «{ex['chunk'][:200]}…»" for ex in exemplars[:3]])

# Prompt + Generation
def compose_prompt(user_text, style_sheet, exemplars_text, author):
    return f"""
Rewrite the following text in the distinctive literary style of {author}.
Your goal is to preserve meaning but transform the tone, rhythm, mood, and phrasing to match the author's writing style.

STRICT RULES:
- Maintain the original meaning of the user's text.
- Do NOT add random facts about the author.
- Use stylistic and rhetorical patterns seen in the exemplars.
- Do NOT describe the author.
- Do NOT explain who the author is.
- Output only the rewritten text and nothing else.

STYLE GUIDANCE:
Tone tags: {style_sheet['tone_tags']}
Avg sentence length: {style_sheet['avg_sent_len']}
Anchors and thematic hints: {style_sheet['anchors']}

EXEMPLARS (for style only, DO NOT COPY):
{exemplars_text}

TEXT TO REWRITE:
"{user_text}"

Now produce the rewritten paragraph in the style of {author}.
""".strip()

def generate_text(prompt: str):
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True).to(DEVICE)
    output = gen_model.generate(
        **inputs,
        do_sample=True,
        top_p=0.92,
        temperature=0.7,
        max_new_tokens=300,
    )
    return tokenizer.decode(output[0], skip_special_tokens=True)

# Public API
def get_authors() -> List[str]:
    return AUTHORS

def rag_author_rewrite(user_text: str, author: str) -> Dict[str, Any]:
    exemplars = retrieve_exemplars(user_text, author, top_k=8)
    exemplars_text = summarize_exemplars(exemplars)

    style_sheet = {
        "tone_tags": ["literary", "reflective"],
        "avg_sent_len": 18,
        "anchors": []
    }

    prompt = compose_prompt(user_text, style_sheet, exemplars_text, author)
    rewritten = generate_text(prompt)

    analysis = {
        "source_metrics": stylometrics_en(user_text),
        "output_metrics": stylometrics_en(rewritten)
    }

    return {
        "rewritten": rewritten,
        "exemplars_used": [e["path"] for e in exemplars],
        "analysis": analysis,
    }
