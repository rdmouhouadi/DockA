# conftest.py
# Adds core/ to sys.path so that imports like
# `from ingestion.core.checksum import ...` and `from app.backend_api ...`
# work in tests. Core packages live under core/ since the core + verticals
# restructure; verticals will add their own paths when they gain code.

import sys
import os

# Resolve relative to this file (not the CWD) so pytest works from any directory
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))