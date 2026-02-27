from pathlib import Path

from bs4 import BeautifulSoup


class HTMLExtractor:
    @staticmethod
    def extract(file_path: Path) -> str:
        """
        Extract visible text from an HTML file.

        Strips all HTML tags and returns clean text content.
        Handles encoding detection via BeautifulSoup.

        Requires: beautifulsoup4
        """

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")

        soup = BeautifulSoup(content, "html.parser")

        # Remove script and style elements — they contain no useful text
        for tag in soup(["script", "style", "meta", "head"]):
            tag.decompose()

        return soup.get_text(separator="\n")