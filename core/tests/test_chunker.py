"""
Unit Tests — DocKA Chunker

Tests for the token-based sliding-window chunker:
- chunker.py   : pure chunking logic (fake one-token-per-word offsets)
- tokenizer.py : real e5 tokenizer, only if it is already cached locally

No database, no Elasticsearch, no network required.

Run with:
    pytest core/tests/test_chunker.py -v
"""

import re

import pytest

from ingestion.core.chunker import chunk_text


# =============================================================================
# Helpers
# =============================================================================

def word_offsets(text: str) -> list[tuple[int, int]]:
    """Fake tokenizer: one token per whitespace-separated word."""
    return [m.span() for m in re.finditer(r"\S+", text)]


def make_text(n_words: int) -> str:
    """Deterministic text of n distinct words: 'w0 w1 w2 ...'."""
    return " ".join(f"w{i}" for i in range(n_words))


# =============================================================================
# chunk_text
# =============================================================================

class TestChunkText:
    """Sliding-window chunking over token offsets."""

    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("", [], max_tokens=10, overlap=2) == []

    def test_short_text_is_single_chunk(self):
        text = make_text(5)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=2)

        assert len(chunks) == 1
        assert chunks[0]["content"] == text
        assert chunks[0]["token_count"] == 5

    def test_text_exactly_max_tokens_is_single_chunk(self):
        text = make_text(10)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=2)

        assert len(chunks) == 1

    def test_chunks_never_exceed_max_tokens(self):
        text = make_text(97)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=3)

        assert len(chunks) > 1
        assert all(c["token_count"] <= 10 for c in chunks)

    def test_consecutive_chunks_share_overlap_tokens(self):
        text = make_text(30)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=3)

        for prev, nxt in zip(chunks, chunks[1:]):
            prev_words = prev["content"].split()
            next_words = nxt["content"].split()
            assert prev_words[-3:] == next_words[:3]

    def test_zero_overlap_partitions_text(self):
        text = make_text(25)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=0)

        words = [w for c in chunks for w in c["content"].split()]
        assert words == text.split()

    def test_content_matches_char_offsets(self):
        text = "Compteur  Diehl\n\nfuite d'eau détectée sur le réseau principal."
        chunks = chunk_text(text, word_offsets(text), max_tokens=3, overlap=1)

        for c in chunks:
            assert c["content"] == text[c["start_char"]:c["end_char"]]

    def test_chunk_indexes_are_sequential(self):
        text = make_text(50)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=2)

        assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))

    def test_covers_whole_text(self):
        text = make_text(43)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=4)

        assert chunks[0]["start_char"] == 0
        assert chunks[-1]["end_char"] == len(text)

    def test_no_duplicate_tail_chunk(self):
        # 18 tokens, stride 8: windows [0,10) and [8,18) — no third window
        text = make_text(18)
        chunks = chunk_text(text, word_offsets(text), max_tokens=10, overlap=2)

        assert len(chunks) == 2

    @pytest.mark.parametrize("max_tokens, overlap", [(10, 10), (10, 12), (10, -1), (0, 0)])
    def test_invalid_parameters_raise(self, max_tokens, overlap):
        with pytest.raises(ValueError):
            chunk_text("a b c", word_offsets("a b c"), max_tokens=max_tokens, overlap=overlap)


# =============================================================================
# Real tokenizer (optional — skipped unless the e5 tokenizer is cached)
# =============================================================================

def _tokenizer_cached() -> bool:
    try:
        from transformers import AutoTokenizer
        from ingestion.core.tokenizer import EMBEDDING_MODEL
        AutoTokenizer.from_pretrained(EMBEDDING_MODEL, local_files_only=True)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _tokenizer_cached(), reason="embedding tokenizer not cached locally")
class TestRealTokenizer:
    """End-to-end chunking with the multilingual-e5-base tokenizer."""

    def test_chunks_fit_model_token_budget(self):
        from ingestion.core.tokenizer import token_offsets, get_tokenizer

        text = "Le compteur Diehl transmet un index de consommation. " * 200
        chunks = chunk_text(text, token_offsets(text), max_tokens=500, overlap=50)

        assert len(chunks) > 1
        for c in chunks:
            # Re-tokenize the chunk as the embedder will: prefix + special tokens
            n = len(get_tokenizer()("passage: " + c["content"])["input_ids"])
            assert n <= 512
            assert c["content"] == text[c["start_char"]:c["end_char"]]
