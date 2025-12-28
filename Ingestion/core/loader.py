from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".txt"}

def scan_directory(base_path: str):
    base = Path(base_path)
    for file in base.rglob("*"):
        if file.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield file
