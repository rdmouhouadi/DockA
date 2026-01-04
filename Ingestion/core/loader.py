from pathlib import Path
from Ingestion.extractors import EXTRACTOR_REGISTRY

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".txt"}

def scan_directory(base_path: str):
    base = Path(base_path)
    for file in base.rglob("*"):
        if file.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield file

def load_file(file_path):
    suffix = file_path.suffix.lower()

    if suffix not in EXTRACTOR_REGISTRY:
        raise ValueError(f"Unsupported file type: {suffix}")
    
    extractor = EXTRACTOR_REGISTRY[suffix]
    raw_text = extractor.extract(file_path)

    return raw_text