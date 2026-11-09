"""
Retention — how long an uploaded document stays searchable.

Two independent choices per upload (see the UI upload tab):
1. Keep the original file?      → file_retained (storage.py)
2. How long is it searchable?   → expires_at (this module)
     - temporary: removed everywhere (search index, PostgreSQL incl. chunks,
       kept file) once expires_at has passed
     - until removed: expires_at = NULL, stays until the user removes the source

Pure logic, no I/O — the purge itself lives in pipelines/purge_expired.py.
"""

from datetime import datetime, timedelta, timezone

# Durations offered for temporary uploads (label shown in the UI → duration)
TEMPORARY_DURATIONS: dict[str, timedelta] = {
    "1 hour": timedelta(hours=1),
    "24 hours": timedelta(hours=24),
    "7 days": timedelta(days=7),
}

DEFAULT_TEMPORARY_DURATION = "24 hours"


def expiry_for(duration_label: str | None, now: datetime | None = None) -> datetime | None:
    """
    Expiry timestamp for an upload.

    Args:
        duration_label: a key of TEMPORARY_DURATIONS, or None for
                        "searchable until I remove it"
        now:            injectable clock (tests); defaults to current UTC time

    Returns:
        timezone-aware UTC datetime, or None (never expires)

    Raises:
        ValueError: unknown duration label
    """
    if duration_label is None:
        return None
    if duration_label not in TEMPORARY_DURATIONS:
        raise ValueError(f"Unknown retention duration: {duration_label!r}")

    now = now or datetime.now(timezone.utc)
    return now + TEMPORARY_DURATIONS[duration_label]


def merged_expiry(existing: datetime | None, new: datetime | None) -> datetime | None:
    """
    Expiry to keep when the same content is uploaded again.

    Retention is only ever extended, never shortened: a re-upload must not
    make a document that someone else wanted to keep disappear earlier.
    - either side None (until removed) → None
    - otherwise                        → the later of the two
    """
    if existing is None or new is None:
        return None
    return max(existing, new)


def describe_expiry(expires_at: datetime | None, now: datetime | None = None) -> str:
    """Short human-readable retention label for the UI sidebar."""
    if expires_at is None:
        return "until removed"

    now = now or datetime.now(timezone.utc)
    remaining = expires_at - now
    if remaining <= timedelta(0):
        return "expired — pending removal"

    hours = remaining.total_seconds() / 3600
    if hours < 1:
        return f"expires in {max(1, int(remaining.total_seconds() // 60))} min"
    if hours < 48:
        return f"expires in {int(hours)} h"
    return f"expires in {int(hours // 24)} days"
