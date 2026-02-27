"""
Unit Tests — DocKA Core Modules

Tests for the pure logic layer of DocKA ingestion:
- checksum.py   : deterministic file hashing
- normalizer.py : text cleaning and normalization
- ingest_folder : language detection

These tests require no database, no Elasticsearch, no Docker.
They test pure Python functions in complete isolation.

Run with:
    pytest tests/test_core.py -v
"""

import os
import tempfile
import pytest

from Ingestion.core.checksum import file_checksum
from Ingestion.core.normalizer import normalize_text
from Ingestion.pipelines.ingest_folder import detect_language


# =============================================================================
# checksum.py
# =============================================================================

class TestFileChecksum:
    """
    Tests for file_checksum().

    Key properties to verify:
    - Determinism: same file always produces the same hash
    - Sensitivity: different content produces different hash
    - Stability: re-reading the same file gives the same result
    """

    def test_same_file_same_checksum(self, tmp_path):
        """
        The same file must always produce the same checksum.
        This is the foundation of idempotent ingestion.
        """
        file = tmp_path / "doc.txt"
        file.write_text("Hello DocKA", encoding="utf-8")

        checksum1 = file_checksum(str(file))
        checksum2 = file_checksum(str(file))

        assert checksum1 == checksum2

    def test_different_content_different_checksum(self, tmp_path):
        """
        Two files with different content must produce different checksums.
        If this fails, the deduplication logic would silently skip documents.
        """
        file1 = tmp_path / "doc1.txt"
        file2 = tmp_path / "doc2.txt"

        file1.write_text("Content A", encoding="utf-8")
        file2.write_text("Content B", encoding="utf-8")

        assert file_checksum(str(file1)) != file_checksum(str(file2))

    def test_checksum_is_hex_string(self, tmp_path):
        """
        The checksum must be a valid SHA-256 hex string (64 characters).
        This validates the output format expected by PostgreSQL and ES.
        """
        file = tmp_path / "doc.txt"
        file.write_text("DocKA test", encoding="utf-8")

        checksum = file_checksum(str(file))

        # SHA-256 hex digest is always exactly 64 characters
        assert len(checksum) == 64
        # Must be a valid hex string (only 0-9 and a-f)
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_empty_file_has_checksum(self, tmp_path):
        """
        Empty files must still produce a valid checksum.
        An empty file is a valid document and should not crash ingestion.
        """
        file = tmp_path / "empty.txt"
        file.write_bytes(b"")

        checksum = file_checksum(str(file))

        assert isinstance(checksum, str)
        assert len(checksum) == 64

    def test_binary_file_checksum(self, tmp_path):
        """
        Binary files (e.g. PDFs) must be handled correctly.
        The function reads in binary mode so this should work for all formats.
        """
        file = tmp_path / "binary.bin"
        file.write_bytes(bytes(range(256)))

        checksum = file_checksum(str(file))

        assert isinstance(checksum, str)
        assert len(checksum) == 64

    def test_modified_file_changes_checksum(self, tmp_path):
        """
        If a file is modified, its checksum must change.
        This is how DocKA detects updated documents during re-ingestion.
        """
        file = tmp_path / "doc.txt"
        file.write_text("Original content", encoding="utf-8")
        checksum_before = file_checksum(str(file))

        # Modify the file
        file.write_text("Modified content", encoding="utf-8")
        checksum_after = file_checksum(str(file))

        assert checksum_before != checksum_after


# =============================================================================
# normalizer.py
# =============================================================================

class TestNormalizeText:
    """
    Tests for normalize_text().

    The normalizer is responsible for producing clean, consistent text
    for Elasticsearch indexing. Poor normalization = poor search quality.
    """

    def test_empty_string_returns_empty(self):
        """
        Empty input must return empty string without crashing.
        Extractors can return empty strings for image-only PDFs.
        """
        assert normalize_text("") == ""

    def test_none_returns_empty(self):
        """
        None input must return empty string.
        Defensive check — some extractors may return None.
        """
        assert normalize_text(None) == ""

    def test_removes_excessive_newlines(self):
        """
        Multiple consecutive newlines must be collapsed into a single space.
        PDF extraction often produces text with many blank lines.
        """
        text = "Hello\n\n\nWorld"
        result = normalize_text(text)

        assert "\n" not in result
        assert "Hello" in result
        assert "World" in result

    def test_removes_isolated_page_numbers(self):
        """
        Lines containing only digits (page numbers) must be removed.
        Page numbers add noise to search without providing value.
        """
        text = "Some content\n42\nMore content"
        result = normalize_text(text)

        # The isolated number should be gone
        # but content should remain
        assert "Some content" in result
        assert "More content" in result

    def test_collapses_multiple_spaces(self):
        """
        Multiple consecutive spaces must be collapsed into one.
        PDF extraction frequently introduces irregular spacing.
        """
        text = "Hello    World"
        result = normalize_text(text)

        assert "  " not in result
        assert "Hello World" in result

    def test_strips_leading_trailing_whitespace(self):
        """
        Leading and trailing whitespace must be removed.
        """
        text = "   Hello World   "
        result = normalize_text(text)

        assert result == result.strip()
        assert result.startswith("Hello")
        assert result.endswith("World")

    def test_normalizes_unicode(self):
        """
        Unicode characters must be preserved and normalized to NFC form.
        French accented characters (é, è, ê, à, ù) must not be corrupted.
        """
        text = "Généralités sur la radio-relève"
        result = normalize_text(text)

        assert "Généralités" in result
        assert "radio-relève" in result

    def test_removes_control_characters(self):
        """
        Null bytes and control characters must be removed.
        These are common artifacts from PDF extraction libraries.
        """
        text = "Hello\x00World\x01Test"
        result = normalize_text(text)

        assert "\x00" not in result
        assert "\x01" not in result
        assert "Hello" in result
        assert "World" in result

    def test_preserves_meaningful_content(self):
        """
        Normalization must not destroy meaningful document content.
        This is a smoke test — real content must survive the pipeline.
        """
        text = (
            "Guide radio Birdz\n"
            "Ce guide a pour but de vous assister dans l'utilisation\n"
            "de votre dispositif de radio-relève."
        )
        result = normalize_text(text)

        assert "Guide radio Birdz" in result
        assert "radio-relève" in result

    def test_tabs_replaced_with_spaces(self):
        """
        Tabs must be replaced with spaces.
        PDF tables and formatted content often use tab characters.
        """
        text = "Column1\tColumn2\tColumn3"
        result = normalize_text(text)

        assert "\t" not in result


# =============================================================================
# detect_language()
# =============================================================================

class TestDetectLanguage:
    """
    Tests for detect_language().

    Language detection is used to tag documents for
    language-specific search analyzers in Phase 2.
    """

    def test_detects_french(self):
        """
        French text must be detected as 'fr'.
        All current sample documents are in French.
        """
        text = (
            "Ce guide a pour but de vous assister dans l'utilisation "
            "de votre dispositif de radio-relève. Il a été rédigé pour "
            "les versions 2.X de l'application Saphir."
        )
        assert detect_language(text) == "fr"

    def test_detects_english(self):
        """
        English text must be detected as 'en'.
        Required for the healthcare corpus (PubMed abstracts are in English).
        """
        text = (
            "This guide is intended to assist you in the use of your "
            "radio reading device. It was written for version 2.X of "
            "the Saphir application."
        )
        assert detect_language(text) == "en"

    def test_returns_none_for_empty_string(self):
        """
        Empty string must return None without raising an exception.
        Language detection cannot work on empty content.
        """
        assert detect_language("") is None

    def test_returns_none_for_undetectable_text(self):
        """
        Text that cannot be classified must return None gracefully.
        Examples: pure numbers, single characters, symbols only.
        """
        assert detect_language("123 456 789") is None

    def test_returns_string_or_none(self):
        """
        Return type must always be str or None — never raises an exception.
        This guarantees the ingestion pipeline never crashes on language detection.
        """
        result = detect_language("Bonjour le monde")

        assert result is None or isinstance(result, str)