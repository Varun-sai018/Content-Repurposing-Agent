"""Utilities for ingesting and validating user-provided content."""

from __future__ import annotations

from io import BytesIO
from typing import Optional, Tuple

import docx
import PyPDF2


DEFAULT_MAX_WORDS = 20_000


def _normalize_text(text: str) -> str:
    """Return text with consistent new lines and stripped trailing spaces."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.strip() for line in cleaned.split("\n"))


def _word_count(text: str) -> int:
    """Simple whitespace-based word count."""
    return len([token for token in text.split() if token.strip()])


def extract_text_from_pdf(file_bytes: BytesIO) -> str:
    """Extract text from a PDF file represented as a BytesIO object."""
    reader = PyPDF2.PdfReader(file_bytes)
    pages = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        pages.append(extracted)
    return "\n".join(pages)


def extract_text_from_docx(file_bytes: BytesIO) -> str:
    """Extract text from a DOCX file represented as a BytesIO object."""
    document = docx.Document(file_bytes)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(paragraphs)


def read_uploaded_file(uploaded_file) -> str:  # type: ignore[override]
    """Return plain text extracted from a Streamlit UploadedFile."""

    if uploaded_file is None:
        return ""

    buffer = BytesIO(uploaded_file.getvalue())
    name = uploaded_file.name.lower()
    mime_type = getattr(uploaded_file, "type", "").lower()

    if name.endswith(".pdf") or "pdf" in mime_type:
        return extract_text_from_pdf(buffer)

    if name.endswith(".docx") or "word" in mime_type or "docx" in mime_type:
        return extract_text_from_docx(buffer)

    raise ValueError("Unsupported file type. Please upload a PDF or DOCX file.")


def enforce_word_limit(text: str, max_words: int = DEFAULT_MAX_WORDS) -> Tuple[str, int]:
    """Trim text to the maximum word limit and return the text with its word count."""
    words = [token for token in text.split() if token.strip()]
    if len(words) <= max_words:
        return text, len(words)

    limited_text = " ".join(words[:max_words])
    return limited_text, max_words


def prepare_text(
    pasted_text: str,
    uploaded_file,
    max_words: int = DEFAULT_MAX_WORDS,
) -> Tuple[str, int]:
    """Combine pasted and uploaded content, clean it, and enforce word limits."""

    extracted_text = read_uploaded_file(uploaded_file)

    combined = "\n".join(filter(None, [pasted_text.strip(), extracted_text.strip()]))
    cleaned = _normalize_text(combined)

    if not cleaned.strip():
        return "", 0

    limited_text, count = enforce_word_limit(cleaned, max_words)
    return limited_text, count


def preview_text(text: str, preview_length: int = 400) -> str:
    """Return a short preview of the text to display in the UI."""
    snippet = text[:preview_length].strip()
    if len(text) > preview_length:
        snippet += "..."
    return snippet


__all__ = [
    "DEFAULT_MAX_WORDS",
    "prepare_text",
    "preview_text",
    "read_uploaded_file",
    "enforce_word_limit",
    "extract_text_from_pdf",
    "extract_text_from_docx",
]

