import requests
import structlog
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

from .config import BASE_URL, REQUEST_HEADERS, REQUEST_TIMEOUT

logger = structlog.get_logger(__name__)

# One keep-alive session shared by every Showlink fetch. Crawling a single show
# fans out to dozens or hundreds of breed-result pages on the same host, so
# reusing the connection skips a fresh TCP + TLS handshake per request — less CPU
# on the NUC and on Showlink, and gentler on the origin than churning a new
# connection each time. The pool is sized to comfortably exceed the result
# crawler's worker ceiling (DOG_RESULT_WORKERS, currently 3) against the single
# Showlink host. requests.Session is thread-safe for concurrent gets, which the
# result workers rely on.
_adapter = HTTPAdapter(pool_connections=4, pool_maxsize=8)
_SESSION = requests.Session()
_SESSION.mount("https://", _adapter)
_SESSION.mount("http://", _adapter)

def _source_url(show_id, group="", breed=""):
    url = f"{BASE_URL}?Id={show_id}"
    if group:
        url += f"&R={group}"
    if breed:
        url += f"&RO={breed}"
    return url

def _fetch_page(url):
    """Fetch a page from Showlink with timeout and logging.

    Uses the shared keep-alive session so back-to-back breed-page fetches reuse
    one connection instead of handshaking per request.
    """
    logger.info("showlink_request", url=url)
    resp = _SESSION.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")
