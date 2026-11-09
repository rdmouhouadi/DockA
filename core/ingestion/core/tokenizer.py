"""
Tokenizer adapter — the embedding model's own tokenizer.

Chunk sizes are measured in the tokens the embedding model actually sees,
so a "500-token chunk" is never silently truncated at embedding time.

Only the tokenizer is loaded here (transformers without PyTorch); the full
embedding model arrives in Phase 2 M2.
"""

import os
from functools import lru_cache

from transformers import AutoTokenizer

# Must match the embedding model used in M2 — the tokenizer defines the token budget
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")


@lru_cache(maxsize=1)
def get_tokenizer():
    """
    Load the tokenizer once per process.

    First call downloads the tokenizer files from Hugging Face
    (cached locally afterwards).
    """
    return AutoTokenizer.from_pretrained(EMBEDDING_MODEL)


def token_offsets(text: str) -> list[tuple[int, int]]:
    """
    Tokenize text and return each token's (start_char, end_char) span.

    - add_special_tokens=False: <s> / </s> are added per chunk at embed time,
      not per document
    - Offsets let the chunker slice the ORIGINAL text, so chunks contain no
      tokenizer decode artefacts and keep exact positions for citations
    """
    if not text:
        return []

    encoding = get_tokenizer()(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
    )
    return [tuple(span) for span in encoding["offset_mapping"]]
