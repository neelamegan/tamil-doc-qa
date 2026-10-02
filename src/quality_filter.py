# src/quality_filter.py
import re

def tamil_ratio(text: str) -> float:
    if not text.strip():
        return 0.0
    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
    total_chars = len(re.sub(r'\s', '', text))
    return tamil_chars / total_chars if total_chars else 0.0

def is_valid(text: str, min_ratio=0.3, min_len=20) -> bool:
    return len(text.strip()) >= min_len and tamil_ratio(text) >= min_ratio