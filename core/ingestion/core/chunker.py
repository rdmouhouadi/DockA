"""
Chunker — split a document into overlapping, token-bounded chunks.

Pure logic, no I/O: the caller supplies token offsets (see tokenizer.py),
which keeps this module testable without downloading a model.

Sliding window over tokens:

    tokens:  [0 ............................................ n)
    chunk 0: [0 ........ max)
    chunk 1:        [stride ........ stride+max)
    chunk 2:                [2*stride ........ 2*stride+max)
                     <-->
                    overlap        stride = max_tokens - overlap

Overlap keeps a sentence that straddles a boundary retrievable from
either side.
"""

import os

# ---------------------------------------------------------------------------
# Defaults
#
# 500, not 512: multilingual-e5-base accepts 512 tokens, of which
# 2 are special tokens (<s>, </s>) and 2 are the "passage: " prefix e5
# expects at embedding time (M2) → 508 usable. 500 keeps a small margin.
# ---------------------------------------------------------------------------
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "500"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))


def chunk_text(
    text: str,
    offsets: list[tuple[int, int]],
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
) -> list[dict]:
    """
    Split text into chunks of at most max_tokens tokens.

    Args:
        text:       normalized document text
        offsets:    (start_char, end_char) per token, from token_offsets(text)
        max_tokens: maximum tokens per chunk
        overlap:    tokens shared by consecutive chunks

    Returns:
        List of chunks, each with:
        - chunk_index : 0-based position in the document
        - content     : text[start_char:end_char] (sliced from the original)
        - start_char  : first character of the chunk in the document
        - end_char    : character after the last one (exclusive)
        - token_count : number of tokens in the chunk
    """
    if max_tokens <= 0:
        raise ValueError(f"max_tokens must be positive, got {max_tokens}")
    if not 0 <= overlap < max_tokens:
        raise ValueError(
            f"overlap must be in [0, max_tokens), got overlap={overlap}, max_tokens={max_tokens}"
        )

    if not text or not offsets:
        return []

    stride = max_tokens - overlap
    n_tokens = len(offsets)
    chunks = []

    for chunk_index, start in enumerate(range(0, n_tokens, stride)):
        end = min(start + max_tokens, n_tokens)

        start_char = offsets[start][0]
        end_char = offsets[end - 1][1]

        chunks.append({
            "chunk_index": chunk_index,
            "content": text[start_char:end_char],
            "start_char": start_char,
            "end_char": end_char,
            "token_count": end - start,
        })

        # Last window reached the end — stop, or the next window would be
        # a pure-overlap duplicate of this chunk's tail
        if end == n_tokens:
            break

    return chunks
