from pathlib import Path
from pypdf import PdfReader


class PDFExtractor:
    @staticmethod
    def extract(file_path: Path) -> str:
        """
        Extract raw text from a PDF file.
        """
        reader = PdfReader(str(file_path))
        text = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)

        return "\n".join(text)
