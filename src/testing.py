# import fitz
# from pathlib import Path
#
# pdf_path = Path(__file__).parent / "../data/Thirukkural_with_meaning.pdf"  # adjust to actual location
# print("total pages:", len(pdf_path))
# # doc = fitz.open(pdf_path)
# # for p in [0, 50, 150, 164]:
# #     print(p, repr(doc[p].get_text()[:200]))

# import pymupdf  # use this instead of fitz — fitz is just the legacy alias
#
# doc = pymupdf.open("../data/Thirukkural_with_meaning.pdf")
# print("total pages:", len(doc))
#
# page = doc[50]
# fonts = page.get_fonts()
# print(fonts)
#
# pix = page.get_pixmap(dpi=300)
# pix.save("page50.png")

# import pymupdf
#
# doc = pymupdf.open("../data/Thirukkural_with_meaning.pdf")
# problem_pages = []
# for i in range(len(doc)):
#     fonts = doc[i].get_fonts()
#     if fonts:  # has embedded custom fonts — likely glyph-mapped
#         problem_pages.append(i)
#
# print(f"{len(problem_pages)} of {len(doc)} pages have embedded fonts")
# print(problem_pages[:20])
#
# import pytesseract
# from PIL import Image
# import io
#
# def ocr_page(doc, page_num, dpi=300):
#     page = doc[page_num]
#     pix = page.get_pixmap(dpi=dpi)
#     img = Image.open(io.BytesIO(pix.tobytes("png")))
#     text = pytesseract.image_to_string(img, lang="tam")
#     return text
#
# sample = ocr_page(doc, 50)
# print(sample[:500])


# import pymupdf
# import pytesseract
# from PIL import Image
# import io
#
# doc = pymupdf.open("../data/Thirukkural_with_meaning.pdf")
#
# def ocr_page(doc, page_num, dpi=300):
#     page = doc[page_num]
#     pix = page.get_pixmap(dpi=dpi)
#     img = Image.open(io.BytesIO(pix.tobytes("png")))
#     text = pytesseract.image_to_string(img, lang="tam")
#     return text, img
#
# for p in [0, 30, 80, 130]:
#     text, img = ocr_page(doc, p)
#     img.save(f"page_{p}.png")  # save so you can eyeball the source image too
#     print(f"--- page {p} ---")
#     print(text[:300])
#     print()
#
# for dpi in [300, 400, 600]:
#     text, _ = ocr_page(doc, 30, dpi=dpi)
#     print(dpi, "→", text[:150])


import pymupdf
import pytesseract
from PIL import Image
import io
import json
from pathlib import Path

DPI = 300  # use whatever DPI you settled on as best in the last step
OUT_PATH = Path("../data/raw_ocr.jsonl")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

doc = pymupdf.open("../data/Thirukkural_with_meaning.pdf")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(dpi=DPI)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="tam")

        record = {"page": i, "text": text}
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if i % 10 == 0:
            print(f"processed page {i}/{len(doc)}")

print("done:", OUT_PATH)