from pathlib import Path
import docx


class DOCXExtractor:
    @staticmethod
    def extract(file_path: Path) -> str:
        """
        Extract raw text from a Word document (.docx).

        Extracts text paragraph by paragraph, preserving
        the natural reading order of the document.

        Requires: python-docx
        """

        doc = docx.Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)