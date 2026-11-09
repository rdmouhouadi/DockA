from pathlib import Path


class TXTExtractor:
    @staticmethod
    def extract(file_path: Path) -> str:
        """
        Extract raw text from a plain text file.

        Tries UTF-8 first, falls back to latin-1 to handle
        files with non-standard encodings (common in older documents).
        """
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="latin-1")