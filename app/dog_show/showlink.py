import requests
import structlog
from bs4 import BeautifulSoup

from .config import BASE_URL, REQUEST_HEADERS, REQUEST_TIMEOUT

logger = structlog.get_logger(__name__)

def _source_url(show_id, group="", breed=""):
    url = f"{BASE_URL}?Id={show_id}"
    if group:
        url += f"&R={group}"
    if breed:
        url += f"&RO={breed}"
    return url

def _fetch_page(url):
    """Fetch a page from Showlink with timeout and logging."""
    logger.info("showlink_request", url=url)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")
