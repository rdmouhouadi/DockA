import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalize extracted document text for indexing.

    Applies a pipeline of cleaning steps:
    1. Normalize unicode (NFC form)
    2. Remove null bytes and control characters
    3. Remove isolated page numbers
    4. Replace newlines and tabs with spaces
    5. Collapse multiple spaces into one
    6. Strip leading/trailing whitespace

    Args:
        text: Raw text extracted from a document

    Returns:
        Cleaned, normalized text ready for indexing
    """
    if not text:
        return ""

    # 1 — Normalize unicode to NFC form
    # Ensures consistent representation of accented characters
    # e.g. "é" as single character vs "e" + combining accent
    text = unicodedata.normalize("NFC", text)

    # 2 — Remove null bytes and control characters
    # PDF extraction often introduces these artifacts
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 3 — Remove isolated page numbers
    # Lines that contain only digits (page numbers from PDFs)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # 4 — Replace newlines and tabs with spaces
    text = text.replace("\n", " ").replace("\t", " ").replace("\r", " ")

    # 5 — Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)

    # 6 — Strip leading/trailing whitespace
    text = text.strip()

    return text