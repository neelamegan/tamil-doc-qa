# src/api.py
import json
import numpy as np
import faiss
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from fastembed import TextEmbedding

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

app = FastAPI(title="Tamil Thirukkural Doc-QA")

model = TextEmbedding(model_name="intfloat/multilingual-e5-large")
index = faiss.read_index(str(DATA_DIR / "index.faiss"))
chunks = json.load(open(DATA_DIR / "meta.json", encoding="utf-8"))


class Query(BaseModel):
    question: str
    k: int = 5


@app.get("/health")
def health():
    return {"status": "ok", "chunks_loaded": len(chunks)}


@app.post("/query")
def query(q: Query):
    qvec = np.array(list(model.embed([f"query: {q.question}"])), dtype="float32")
    faiss.normalize_L2(qvec)
    scores, idxs = index.search(qvec, q.k)

    results = [
        {"page": chunks[i]["page_start"], "text": chunks[i]["text"], "score": float(s)}
        for i, s in zip(idxs[0], scores[0])
    ]
    return {"question": q.question, "results": results}

# src/api.py — add these imports and lines
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ... your existing app = FastAPI(...) and model/index loading stays as-is ...

app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("src/static/index.html")