from .pdf import PDFExtractor
from .txt import TXTExtractor
from .docx import DOCXExtractor
from .html import HTMLExtractor


EXTRACTOR_REGISTRY = {
    ".pdf":  PDFExtractor,
    ".txt":  TXTExtractor,
    ".docx": DOCXExtractor,
    ".html": HTMLExtractor,
}