"""
Unit Tests — DocKA Retention

Tests for retention.py:
- expiry_for      : upload choice → expiry timestamp
- merged_expiry   : re-upload of known content only ever extends retention
- describe_expiry : sidebar label

No database, no Elasticsearch, no Docker.

Run with:
    pytest core/tests/test_retention.py -v
"""

from datetime import datetime, timedelta, timezone

import pytest

from ingestion.core.retention import (
    TEMPORARY_DURATIONS,
    DEFAULT_TEMPORARY_DURATION,
    expiry_for,
    merged_expiry,
    describe_expiry,
)

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


# =============================================================================
# expiry_for
# =============================================================================

class TestExpiryFor:
    """Upload retention choice → expires_at."""

    def test_until_removed_never_expires(self):
        assert expiry_for(None, NOW) is None

    @pytest.mark.parametrize("label", list(TEMPORARY_DURATIONS))
    def test_temporary_adds_duration(self, label):
        assert expiry_for(label, NOW) == NOW + TEMPORARY_DURATIONS[label]

    def test_default_duration_is_offered(self):
        assert DEFAULT_TEMPORARY_DURATION in TEMPORARY_DURATIONS

    def test_result_is_timezone_aware(self):
        assert expiry_for("1 hour").tzinfo is not None

    def test_unknown_label_raises(self):
        with pytest.raises(ValueError):
            expiry_for("forever-ish", NOW)


# =============================================================================
# merged_expiry
# =============================================================================

class TestMergedExpiry:
    """Re-uploading the same content never shortens retention."""

    def test_permanent_wins_over_temporary(self):
        assert merged_expiry(None, NOW) is None
        assert merged_expiry(NOW, None) is None

    def test_later_expiry_wins(self):
        later = NOW + timedelta(days=1)
        assert merged_expiry(NOW, later) == later
        assert merged_expiry(later, NOW) == later


# =============================================================================
# describe_expiry
# =============================================================================

class TestDescribeExpiry:
    """Human-readable label for the sidebar."""

    def test_permanent(self):
        assert describe_expiry(None, NOW) == "until removed"

    def test_minutes(self):
        assert describe_expiry(NOW + timedelta(minutes=30), NOW) == "expires in 30 min"

    def test_hours(self):
        assert describe_expiry(NOW + timedelta(hours=5), NOW) == "expires in 5 h"

    def test_days(self):
        assert describe_expiry(NOW + timedelta(days=7), NOW) == "expires in 7 days"

    def test_past_is_pending_removal(self):
        assert describe_expiry(NOW - timedelta(seconds=1), NOW) == "expired — pending removal"
