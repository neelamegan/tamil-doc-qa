import json

with open("../data/raw_ocr.jsonl", encoding="utf-8") as f:
    records = [json.loads(l) for l in f]

lengths = [len(r["text"]) for r in records]
print("pages:", len(records))
print("empty or near-empty pages:", [r["page"] for r in records if len(r["text"]) < 20])
print("avg chars/page:", sum(lengths)/len(lengths))