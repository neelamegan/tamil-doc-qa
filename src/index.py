import json
import numpy as np
import faiss
from fastembed import TextEmbedding

def run(chunks_path="data/chunks.jsonl", index_path="data/index.faiss", meta_path="data/meta.json"):
    chunks = [json.loads(l) for l in open(chunks_path, encoding="utf-8")]

    model = TextEmbedding(model_name="intfloat/multilingual-e5-large")
    texts = [f"passage: {c['text']}" for c in chunks]
    embeddings = np.array(list(model.embed(texts)), dtype="float32")   # <-- wrapped in np.array here

    index = faiss.IndexFlatIP(embeddings.shape[1])
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    faiss.write_index(index, index_path)

    json.dump(chunks, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"indexed {len(chunks)} chunks")

if __name__ == "__main__":
    run()