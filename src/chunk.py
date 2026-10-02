# src/chunk.py
import json

def chunk_pages(records, max_chars=1500, overlap=200):
    chunks = []
    buf, buf_pages, chunk_id = "", [], 0
    for r in records:
        buf += r["text"] + "\n"
        buf_pages.append(r["page"])
        if len(buf) >= max_chars:
            chunks.append({
                "chunk_id": chunk_id,
                "text": buf.strip(),
                "page_start": buf_pages[0],
                "page_end": buf_pages[-1],
            })
            chunk_id += 1
            buf = buf[-overlap:]
            buf_pages = [buf_pages[-1]]
    if buf.strip():
        chunks.append({
            "chunk_id": chunk_id, "text": buf.strip(),
            "page_start": buf_pages[0], "page_end": buf_pages[-1],
        })
    return chunks

def run(in_path="data/normalized.jsonl", out_path="data/chunks.jsonl"):
    records = [json.loads(l) for l in open(in_path, encoding="utf-8")]
    chunks = chunk_pages(records)
    with open(out_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(chunks)} chunks → {out_path}")

if __name__ == "__main__":
    run()