import json
import numpy as np
import faiss
from fastembed import TextEmbedding

model = TextEmbedding(model_name="intfloat/multilingual-e5-large")
index = faiss.read_index("data/index.faiss")
chunks = json.load(open("../data/meta.json", encoding="utf-8"))

def search(query, k=5):
    # when embedding a query (retrieve.py):
    qvec = np.array(list(model.embed([f"query: {query}"])), dtype="float32")
    faiss.normalize_L2(qvec)
    scores, idxs = index.search(qvec, k)
    return [(chunks[i], float(s)) for i, s in zip(idxs[0], scores[0])]

if __name__ == "__main__":
    results = search("குறள் இன்பம் பற்றி என்ன கூறுகிறது")
    for c, s in results:
        print(s, c["page_start"], c["text"][:100])