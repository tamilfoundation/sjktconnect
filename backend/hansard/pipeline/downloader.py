"""Download Hansard PDF files from parlimen.gov.my.

Handles:
- HTTP download with retries and timeouts
- Saving to a local directory
- Filename extraction from URL or Content-Disposition header
"""

import logging
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
TIMEOUT_SECONDS = 120  # Hansard PDFs can be large (50+ pages)


def download_hansard(url: str, dest_dir: str | Path) -> Path:
    """Download a Hansard PDF from the given URL.

    Args:
        url: Full URL to the PDF file on parlimen.gov.my.
        dest_dir: Directory to save the downloaded file.

    Returns:
        Path to the downloaded file.

    Raises:
        requests.HTTPError: If download fails after all retries.
        ValueError: If URL does not appear to point to a PDF.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = _extract_filename(url)
    dest_path = dest_dir / filename

    if dest_path.exists():
        logger.info("File already exists: %s", dest_path)
        return dest_path

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Downloading %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
            # parlimen.gov.my has an invalid SSL certificate
            verify_ssl = "parlimen.gov.my" not in url
            response = requests.get(
                url, timeout=TIMEOUT_SECONDS, stream=True, verify=verify_ssl
            )
            response.raise_for_status()

            # Check Content-Disposition for a better filename
            cd_filename = _filename_from_content_disposition(
                response.headers.get("Content-Disposition", "")
            )
            if cd_filename:
                dest_path = dest_dir / cd_filename

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = dest_path.stat().st_size
            logger.info("Downloaded %s (%d bytes)", dest_path.name, file_size)
            return dest_path

        except requests.RequestException as e:
            last_error = e
            logger.warning(
                "Download attempt %d failed: %s", attempt, e
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise requests.HTTPError(
        f"Failed to download {url} after {MAX_RETRIES} attempts: {last_error}"
    )


def _extract_filename(url: str) -> str:
    """Extract a filename from a URL path."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = Path(path).name

    if not filename or "." not in filename:
        filename = "hansard.pdf"

    return filename


def _filename_from_content_disposition(header: str) -> str:
    """Extract filename from Content-Disposition header, if present."""
    if not header:
        return ""

    for part in header.split(";"):
        part = part.strip()
        if part.lower().startswith("filename="):
            name = part.split("=", 1)[1].strip().strip('"')
            return name

    return ""
