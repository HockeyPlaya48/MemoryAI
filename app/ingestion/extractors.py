"""Extract text from PDFs and web URLs."""

import logging
from io import BytesIO

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(f"[Page {i + 1}]\n{text}")
        return "\n\n".join(pages)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Could not extract text from PDF: {e}")


def extract_url(url: str) -> str:
    """Fetch and extract clean text from a web URL."""
    try:
        headers = {
            "User-Agent": "MemoryAI/1.0 (knowledge-base crawler)"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script, style, nav, footer elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Get text from main content areas first
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if not main:
            main = soup

        text = main.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    except requests.RequestException as e:
        logger.error(f"URL fetch failed for {url}: {e}")
        raise ValueError(f"Could not fetch URL {url}: {e}")
