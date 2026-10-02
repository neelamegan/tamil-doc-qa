# src/normalize.py
import json
import re
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u200c", "").replace("\u200d", "")  # ZWNJ/ZWJ
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tamil_ratio(text: str) -> float:
    """Fraction of non-whitespace characters that fall in the Tamil Unicode block."""
    if not text.strip():
        return 0.0
    tamil_chars = len(re.findall(r"[\u0B80-\u0BFF]", text))
    total_chars = len(re.sub(r"\s", "", text))
    return tamil_chars / total_chars if total_chars else 0.0


def is_valid(text: str, min_ratio: float = 0.3, min_len: int = 20) -> bool:
    """Flags pages that are too short or too low in actual Tamil content
    (OCR noise, decorative pages, English-only footnote pages, etc.)."""
    return len(text.strip()) >= min_len and tamil_ratio(text) >= min_ratio


def run(
        in_path="data/raw_ocr.jsonl",
        out_path="data/normalized.jsonl",
        dropped_path="data/normalized_dropped.jsonl",
        min_ratio=0.3,
        min_len=20,
):
    records = [json.loads(l) for l in open(in_path, encoding="utf-8")]

    kept, dropped = [], []
    for r in records:
        r["text"] = normalize(r["text"])
        if is_valid(r["text"], min_ratio=min_ratio, min_len=min_len):
            kept.append(r)
        else:
            dropped.append(r)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(dropped_path, "w", encoding="utf-8") as f:
        for r in dropped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"kept {len(kept)} pages -> {out_path}")
    print(f"dropped {len(dropped)} pages -> {dropped_path}")
    print("dropped page numbers:", [r["page"] for r in dropped])


if __name__ == "__main__":
    run()