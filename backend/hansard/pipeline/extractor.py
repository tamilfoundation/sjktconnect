"""Extract text from Hansard PDF files using pdfplumber.

pdfplumber is chosen over PyPDF2 because it handles:
- Complex table layouts (common in parliamentary documents)
- Multi-column text
- Better Unicode handling for Malay/Tamil text

Assumption: Hansard PDFs from parlimen.gov.my are text-based (not scanned images),
so no OCR is needed.
"""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text(pdf_path: str | Path) -> list[tuple[int, str]]:
    """Extract text from a PDF file, page by page.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of (page_number, text) tuples. Page numbers are 1-based.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        pdfplumber.PDFSyntaxError: If the file is not a valid PDF.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        logger.info("Extracting text from %s (%d pages)", pdf_path.name, total)

        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append((i, text))

            if i % 20 == 0:
                logger.info("  Processed %d/%d pages", i, total)

    logger.info("Extraction complete: %d pages, %d with text",
                total, sum(1 for _, t in pages if t.strip()))

    return pages
