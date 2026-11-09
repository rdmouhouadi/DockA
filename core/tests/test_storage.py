"""
Unit Tests — DocKA Upload Storage

Tests for storage.py:
- source_upload_dir : user source tag → folder inside the upload root (no traversal)
- stored_path       : path recorded in PostgreSQL for kept / not-kept uploads

No database, no Elasticsearch, no Docker.

Run with:
    pytest core/tests/test_storage.py -v
"""

from pathlib import Path

import pytest

from ingestion.core.storage import source_upload_dir, stored_path


# =============================================================================
# source_upload_dir
# =============================================================================

class TestSourceUploadDir:
    """Source tags map to a direct child folder of the upload root."""

    def test_simple_tag_is_child_of_root(self, tmp_path):
        assert source_upload_dir("my_reports", tmp_path) == (tmp_path / "my_reports").resolve()

    def test_tag_with_spaces_is_allowed(self, tmp_path):
        result = source_upload_dir("Effective Pandas", tmp_path)
        assert result.name == "Effective Pandas"

    def test_surrounding_whitespace_is_stripped(self, tmp_path):
        assert source_upload_dir("  docs  ", tmp_path).name == "docs"

    @pytest.mark.parametrize("tag", ["", "   ", "..", "../outside", "a/b", "../../etc/passwd", "."])
    def test_invalid_tags_raise(self, tmp_path, tag):
        with pytest.raises(ValueError):
            source_upload_dir(tag, tmp_path)

    def test_absolute_path_tag_raises(self, tmp_path):
        with pytest.raises(ValueError):
            source_upload_dir(str(tmp_path.parent / "elsewhere"), tmp_path)


# =============================================================================
# stored_path
# =============================================================================

class TestStoredPath:
    """Path written to PostgreSQL for each ingested file."""

    def test_no_stored_root_keeps_real_path(self):
        file_path = Path("/data/samples/x/doc.pdf")
        assert stored_path(file_path, Path("/data/samples"), None) == str(file_path)

    def test_stored_root_rebases_temp_path(self):
        result = stored_path(
            Path("/tmp/staging123/sub/doc.pdf"),
            Path("/tmp/staging123"),
            Path("/data/uploads/reports"),
        )
        assert result == str(Path("/data/uploads/reports/sub/doc.pdf"))
