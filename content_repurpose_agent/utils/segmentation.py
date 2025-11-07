"""Segment text into manageable, editable chunks."""

from __future__ import annotations

from typing import List

import nltk
from nltk.tokenize import word_tokenize


MIN_WORDS_PER_SEGMENT = 100


def _ensure_nltk_resource(resource: str) -> None:
    """Ensure the requested NLTK resource is available."""

    try:
        nltk.data.find(f"tokenizers/{resource}")
    except LookupError:
        nltk.download(resource)


def word_count(text: str) -> int:
    """Return the number of word tokens in the provided text."""
    try:
        _ensure_nltk_resource("punkt")
        tokens = word_tokenize(text)
        return len(tokens)
    except Exception:
        # Fallback: basic whitespace tokenization if NLTK resources are missing/corrupted
        return len([token for token in text.split() if token.strip()])


def split_into_segments(text: str, min_words: int = MIN_WORDS_PER_SEGMENT) -> List[str]:
    """Split text by double newlines and merge segments that are too small."""

    paragraphs = [segment.strip() for segment in text.split("\n\n") if segment.strip()]

    if not paragraphs:
        return []

    segments: List[str] = []
    buffer = ""

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer.strip():
            segments.append(buffer.strip())
            buffer = ""

    for paragraph in paragraphs:
        if word_count(paragraph) >= min_words:
            if buffer:
                flush_buffer()
            segments.append(paragraph)
        else:
            buffer = f"{buffer}\n\n{paragraph}".strip()
            if word_count(buffer) >= min_words:
                flush_buffer()

    flush_buffer()
    return segments


__all__ = ["split_into_segments", "word_count", "MIN_WORDS_PER_SEGMENT"]

