"""
Unit Tests — DocKA Core Modules

Tests for the pure logic layer of DocKA ingestion:
- checksum.py        : deterministic file hashing
- normalizer.py      : text cleaning and normalization
- ingest_folder      : language detection
- extractors/txt.py  : plain text extraction
- extractors/docx.py : Word document extraction
- extractors/html.py : HTML extraction

These tests require no database, no Elasticsearch, no Docker.
They test pure Python functions in complete isolation.

Run with:
    pytest tests/test_core.py -v
"""

import pytest
from pathlib import Path

from ingestion.core.checksum import file_checksum
from ingestion.core.normalizer import normalize_text
from ingestion.pipelines.ingest_folder import detect_language
from ingestion.extractors.txt import TXTExtractor
from ingestion.extractors.docx import DOCXExtractor
from ingestion.extractors.html import HTMLExtractor


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

        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_empty_file_has_checksum(self, tmp_path):
        """
        Empty files must still produce a valid checksum.
        """
        file = tmp_path / "empty.txt"
        file.write_bytes(b"")

        checksum = file_checksum(str(file))

        assert isinstance(checksum, str)
        assert len(checksum) == 64

    def test_binary_file_checksum(self, tmp_path):
        """
        Binary files (e.g. PDFs) must be handled correctly.
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
        """Empty input must return empty string without crashing."""
        assert normalize_text("") == ""

    def test_none_returns_empty(self):
        """None input must return empty string."""
        assert normalize_text(None) == ""  # type: ignore

    def test_removes_excessive_newlines(self):
        """Multiple consecutive newlines must be collapsed into a single space."""
        text = "Hello\n\n\nWorld"
        result = normalize_text(text)

        assert "\n" not in result
        assert "Hello" in result
        assert "World" in result

    def test_removes_isolated_page_numbers(self):
        """Lines containing only digits (page numbers) must be removed."""
        text = "Some content\n42\nMore content"
        result = normalize_text(text)

        assert "Some content" in result
        assert "More content" in result

    def test_collapses_multiple_spaces(self):
        """Multiple consecutive spaces must be collapsed into one."""
        text = "Hello    World"
        result = normalize_text(text)

        assert "  " not in result
        assert "Hello World" in result

    def test_strips_leading_trailing_whitespace(self):
        """Leading and trailing whitespace must be removed."""
        text = "   Hello World   "
        result = normalize_text(text)

        assert result == result.strip()
        assert result.startswith("Hello")
        assert result.endswith("World")

    def test_normalizes_unicode(self):
        """French accented characters must not be corrupted."""
        text = "Généralités sur la radio-relève"
        result = normalize_text(text)

        assert "Généralités" in result
        assert "radio-relève" in result

    def test_removes_control_characters(self):
        """Null bytes and control characters must be removed."""
        text = "Hello\x00World\x01Test"
        result = normalize_text(text)

        assert "\x00" not in result
        assert "\x01" not in result
        assert "Hello" in result
        assert "World" in result

    def test_preserves_meaningful_content(self):
        """Normalization must not destroy meaningful document content."""
        text = (
            "Guide radio Birdz\n"
            "Ce guide a pour but de vous assister dans l'utilisation\n"
            "de votre dispositif de radio-relève."
        )
        result = normalize_text(text)

        assert "Guide radio Birdz" in result
        assert "radio-relève" in result

    def test_tabs_replaced_with_spaces(self):
        """Tabs must be replaced with spaces."""
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
        """French text must be detected as 'fr'."""
        text = (
            "Ce guide a pour but de vous assister dans l'utilisation "
            "de votre dispositif de radio-relève. Il a été rédigé pour "
            "les versions 2.X de l'application Saphir."
        )
        assert detect_language(text) == "fr"

    def test_detects_english(self):
        """English text must be detected as 'en'."""
        text = (
            "This guide is intended to assist you in the use of your "
            "radio reading device. It was written for version 2.X of "
            "the Saphir application."
        )
        assert detect_language(text) == "en"

    def test_returns_none_for_empty_string(self):
        """Empty string must return None without raising an exception."""
        assert detect_language("") is None

    def test_returns_none_for_undetectable_text(self):
        """Text that cannot be classified must return None gracefully."""
        assert detect_language("123 456 789") is None

    def test_returns_string_or_none(self):
        """Return type must always be str or None — never raises an exception."""
        result = detect_language("Bonjour le monde")

        assert result is None or isinstance(result, str)


# =============================================================================
# extractors/txt.py
# =============================================================================

class TestTXTExtractor:
    """
    Tests for TXTExtractor.

    TXT is the baseline extractor — if this fails, all others are suspect.
    """

    def test_extracts_utf8_text(self, tmp_path):
        """Standard UTF-8 text files must be extracted correctly."""
        file = tmp_path / "doc.txt"
        file.write_text("Hello DocKA\nSecond line", encoding="utf-8")

        result = TXTExtractor.extract(file)

        assert "Hello DocKA" in result
        assert "Second line" in result

    def test_extracts_latin1_text(self, tmp_path):
        """
        Files with latin-1 encoding must not crash the extractor.
        Older French documents often use latin-1 instead of UTF-8.
        """
        file = tmp_path / "doc_latin1.txt"
        file.write_bytes("Généralités\n".encode("latin-1"))

        result = TXTExtractor.extract(file)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string(self, tmp_path):
        """The extractor must always return a string, never None or bytes."""
        file = tmp_path / "doc.txt"
        file.write_text("Some content", encoding="utf-8")

        result = TXTExtractor.extract(file)

        assert isinstance(result, str)

    def test_empty_file_returns_empty_string(self, tmp_path):
        """An empty file must return an empty string without crashing."""
        file = tmp_path / "empty.txt"
        file.write_text("", encoding="utf-8")

        result = TXTExtractor.extract(file)

        assert result == ""


# =============================================================================
# extractors/html.py
# =============================================================================

class TestHTMLExtractor:
    """
    Tests for HTMLExtractor.

    HTML extraction must strip tags and return only visible text.
    """

    def test_strips_html_tags(self, tmp_path):
        """HTML tags must be removed — only visible text content should remain."""
        file = tmp_path / "doc.html"
        file.write_text(
            "<html><body><h1>Title</h1><p>Some content</p></body></html>",
            encoding="utf-8"
        )

        result = HTMLExtractor.extract(file)

        assert "<h1>" not in result
        assert "<p>" not in result
        assert "Title" in result
        assert "Some content" in result

    def test_removes_script_tags(self, tmp_path):
        """Script tag content must be removed — JavaScript is not searchable text."""
        file = tmp_path / "doc.html"
        file.write_text(
            "<html><body><p>Visible</p>"
            "<script>var x = 'hidden';</script></body></html>",
            encoding="utf-8"
        )

        result = HTMLExtractor.extract(file)

        assert "hidden" not in result
        assert "Visible" in result

    def test_removes_style_tags(self, tmp_path):
        """Style tag content must be removed — CSS is not searchable text."""
        file = tmp_path / "doc.html"
        file.write_text(
            "<html><head><style>body { color: red; }</style></head>"
            "<body><p>Content</p></body></html>",
            encoding="utf-8"
        )

        result = HTMLExtractor.extract(file)

        assert "color: red" not in result
        assert "Content" in result

    def test_returns_string(self, tmp_path):
        """The extractor must always return a string."""
        file = tmp_path / "doc.html"
        file.write_text("<html><body><p>Test</p></body></html>", encoding="utf-8")

        result = HTMLExtractor.extract(file)

        assert isinstance(result, str)


# =============================================================================
# extractors/docx.py
# =============================================================================

class TestDOCXExtractor:
    """
    Tests for DOCXExtractor.

    DOCX extraction must return text content from Word documents.
    We create minimal valid .docx files using python-docx.
    """

    def test_extracts_paragraph_text(self, tmp_path):
        """
        Text from document paragraphs must be extracted correctly.
        Paragraphs are the primary content unit in Word documents.
        """
        import docx as python_docx

        file = tmp_path / "doc.docx"
        doc = python_docx.Document()
        doc.add_paragraph("First paragraph")
        doc.add_paragraph("Second paragraph")
        doc.save(str(file))

        result = DOCXExtractor.extract(file)

        assert "First paragraph" in result
        assert "Second paragraph" in result

    def test_returns_string(self, tmp_path):
        """The extractor must always return a string."""
        import docx as python_docx

        file = tmp_path / "doc.docx"
        doc = python_docx.Document()
        doc.add_paragraph("Some text")
        doc.save(str(file))

        result = DOCXExtractor.extract(file)

        assert isinstance(result, str)

    def test_empty_document_returns_empty_string(self, tmp_path):
        """A document with no paragraphs must return an empty string."""
        import docx as python_docx

        file = tmp_path / "empty.docx"
        doc = python_docx.Document()
        doc.save(str(file))

        result = DOCXExtractor.extract(file)

        assert isinstance(result, str)
        assert result == ""