from .pdf import PDFExtractor


EXTRACTOR_REGISTRY = {
    ".pdf": PDFExtractor,
}
