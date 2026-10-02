# src/ocr.py
import pymupdf
import pytesseract
from PIL import Image
import io
import json
from pathlib import Path

DPI = 300
PDF_PATH = "../data/Thirukkural_with_meaning.pdf"
OUT_PATH = Path("../data/raw_ocr.jsonl")

doc = pymupdf.open(PDF_PATH)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(dpi=DPI)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="tam+eng")

        record = {"page": i, "text": text}
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if i % 10 == 0:
            print(f"processed page {i}/{len(doc)}")

print("done:", OUT_PATH)