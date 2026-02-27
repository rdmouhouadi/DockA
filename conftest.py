# conftest.py
# Adds the project root to sys.path so that
# imports like `from Ingestion.core.checksum import ...` work in tests

import sys
import os

sys.path.insert(0, os.path.abspath("."))