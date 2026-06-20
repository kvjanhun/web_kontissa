import os

BASE_URL = "https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset"
REQUEST_HEADERS = {"User-Agent": "erez.ac-dog-show-browser/1.0 (+https://erez.ac/dog/about-crawler)"}
REQUEST_TIMEOUT = 10

SHOW_LIST_TTL = 1800
SHOW_DETAIL_TTL = 600
BREED_RESULT_TTL = 600
SHOW_ALL_RESULTS_TTL = 86400

RESULT_CACHE_LIVE_TTL = int(os.environ.get("DOG_RESULT_LIVE_TTL", "120"))
RESULT_CACHE_BIS_FINAL_GRACE_SECONDS = int(os.environ.get("DOG_RESULT_BIS_FINAL_GRACE_SECONDS", "1800"))
RESULT_CACHE_ACTIVE_TTL = int(os.environ.get("DOG_RESULT_ACTIVE_TTL", "21600"))
RESULT_CACHE_SETTLED_TTL = int(os.environ.get("DOG_RESULT_SETTLED_TTL", "604800"))
RESULT_CACHE_SETTLED_AFTER_DAYS = int(os.environ.get("DOG_RESULT_SETTLED_AFTER_DAYS", "2"))
RESULT_AUTO_WINDOW_DAYS = int(os.environ.get("DOG_RESULT_AUTO_WINDOW_DAYS", "7"))
RESULT_CACHE_VERSION = 1
RESULT_RETRY_AFTER_SECONDS = 2
RESULT_JOB_STALE_SECONDS = 1800
RESULT_JOB_BACKOFF_SECONDS = 300
RESULT_CRAWL_DEFAULT_DELAY = 0.4
RESULT_CRAWL_DEFAULT_WORKERS = 3
RESULT_LIVE_PROBE_BREED_LIMIT = int(os.environ.get("DOG_RESULT_LIVE_PROBE_BREED_LIMIT", "64"))
RESULT_LIVE_JOB_STALE_SECONDS = int(os.environ.get("DOG_RESULT_LIVE_JOB_STALE_SECONDS", str(RESULT_CACHE_LIVE_TTL)))
RESULT_IMMEDIATE_MAX_ACTIVE = int(os.environ.get("DOG_RESULT_IMMEDIATE_MAX_ACTIVE", "1"))
RESULT_IMMEDIATE_WARMUP_DEFAULT = os.environ.get("DOG_RESULT_IMMEDIATE_WARMUP", "true").lower() != "false"
RESULT_SHOW_MORNING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_MORNING_HOUR", "6"))
RESULT_SHOW_EVENING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_EVENING_HOUR", "21"))
RESULT_LOCAL_TIMEZONE = os.environ.get("DOG_RESULT_TIMEZONE", "Europe/Helsinki")

INDEX_DIR = os.environ.get("DOG_INDEX_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
INDEX_PATH = os.path.join(INDEX_DIR, "dog_show_index.json")
RESULT_CACHE_DIR = os.environ.get("DOG_RESULT_CACHE_DIR", os.path.join(INDEX_DIR, "dog_result_cache"))
RESULT_JOBS_PATH = os.environ.get("DOG_RESULT_JOBS_PATH", os.path.join(INDEX_DIR, "dog_result_jobs.json"))

FINNISH_MONTHS = [
    "tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu",
    "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"
]
