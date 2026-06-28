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
# Captured breed results are immutable, so a live refresh re-fetches only newly
# judged breeds — except the show finals (RYP/BIS-1/BIS JUN/VET), which Showlink
# appends onto the winners' already-captured breed rows after every ring is
# judged. Once all breeds are captured but a main BIS is still expected and not
# yet recorded, re-check a bounded, rotating chunk of captured breeds per pass so
# the finals land within a few passes instead of re-crawling the whole show.
RESULT_FINALS_SWEEP_BREED_LIMIT = int(os.environ.get("DOG_RESULT_FINALS_SWEEP_BREED_LIMIT", "30"))
RESULT_LIVE_JOB_STALE_SECONDS = int(os.environ.get("DOG_RESULT_LIVE_JOB_STALE_SECONDS", str(RESULT_CACHE_LIVE_TTL)))
RESULT_IMMEDIATE_MAX_ACTIVE = int(os.environ.get("DOG_RESULT_IMMEDIATE_MAX_ACTIVE", "1"))
RESULT_IMMEDIATE_WARMUP_DEFAULT = os.environ.get("DOG_RESULT_IMMEDIATE_WARMUP", "true").lower() != "false"
RESULT_SHOW_MORNING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_MORNING_HOUR", "6"))
RESULT_SHOW_EVENING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_EVENING_HOUR", "21"))

# A multi-day show enters the "Jatkuu" (paused) display state during its nightly
# hiatus, or once its results have stalled for this long in the evening wind-down.
# RESULT_PAUSE_EVENING_HOUR floors the stall trigger so a slow midday breed ring
# (or crawler scheduling lag) can't fake a pause during active daytime judging.
RESULT_PAUSE_STALL_SECONDS = int(os.environ.get("DOG_RESULT_PAUSE_STALL_SECONDS", "7200"))
RESULT_PAUSE_EVENING_HOUR = int(os.environ.get("DOG_RESULT_PAUSE_EVENING_HOUR", "17"))

# Max shows a single web-worker /api/dog/shows hit may background-index. Keeps a
# cold/empty index from spawning hundreds of Showlink requests per request; the
# dog-crawler service picks up the rest on its 15-minute crawl_index_once pass.
BACKGROUND_INDEX_MAX_PER_CALL = int(os.environ.get("DOG_BACKGROUND_INDEX_MAX_PER_CALL", "5"))
# Minimum seconds between full in-memory index rebuilds per process. The generation
# check is cheap, but a busy live show makes the crawler bump the generation often,
# and one /api/dog/shows hit re-checks it several times (once per live show, via
# _result_cache_due). Without a floor each of those did a full read_index rebuild,
# which starved the request workers. Bounding rebuilds to once per interval costs
# at most this much mirror staleness, invisible to the show list and stats.
INDEX_RELOAD_MIN_INTERVAL = float(os.environ.get("DOG_INDEX_RELOAD_MIN_INTERVAL", "1.0"))
# Per-show stats cache TTL (seconds). The /dog page polls /api/dog/shows every 15s
# whenever a live show is present, and a live show's stats reconstruct its whole-show
# result doc (thousands of rows) from SQLite. Caching the computed stats this long
# decouples that cost from the poll rate (and from the number of viewers). Stats
# only shift when the result cache refreshes (~every live TTL) or the clock crosses
# a phase hour, so a few seconds of staleness is invisible.
SHOW_STATS_CACHE_TTL = float(os.environ.get("DOG_SHOW_STATS_CACHE_TTL", "20"))
RESULT_LOCAL_TIMEZONE = os.environ.get("DOG_RESULT_TIMEZONE", "Europe/Helsinki")

# Phase C all-shows backfill: full-data crawl of historical shows, run only in an
# off-peak window, strictly polite (single worker, deliberate per-request delay),
# oldest-first so the most at-risk history (closest to ageing off Showlink's
# rolling window) is captured first. Disabled unless dog_crawl.py is run with
# --backfill. The window is Finnish local time; the crawler container runs UTC.
BACKFILL_START_HOUR = int(os.environ.get("DOG_BACKFILL_START_HOUR", "0"))
BACKFILL_END_HOUR = int(os.environ.get("DOG_BACKFILL_END_HOUR", "6"))
BACKFILL_DELAY = float(os.environ.get("DOG_BACKFILL_DELAY", "2.0"))
BACKFILL_WORKERS = int(os.environ.get("DOG_BACKFILL_WORKERS", "1"))
BACKFILL_SHOW_LIMIT = int(os.environ.get("DOG_BACKFILL_SHOW_LIMIT", "1"))
# Max breeds a single backfill pass crawls before returning, so a 200+ breed
# historical show is captured across several passes (resuming per-breed) instead
# of holding the crawler loop for one long crawl. ~25 breeds ≈ 50s at 2s spacing,
# comfortably inside the loop cadence and the off-peak window.
BACKFILL_BREED_BUDGET = int(os.environ.get("DOG_BACKFILL_BREED_BUDGET", "25"))

INDEX_DIR = os.environ.get("DOG_INDEX_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
INDEX_PATH = os.path.join(INDEX_DIR, "dog_show_index.json")
RESULT_CACHE_DIR = os.environ.get("DOG_RESULT_CACHE_DIR", os.path.join(INDEX_DIR, "dog_result_cache"))
RESULT_JOBS_PATH = os.environ.get("DOG_RESULT_JOBS_PATH", os.path.join(INDEX_DIR, "dog_result_jobs.json"))

# Dog data lives in its own SQLite database (the /dog-only persistent store),
# separate from the main site.db and not replicated to Litestream. A full
# SQLAlchemy URL can be supplied via DOG_DATABASE_URI; otherwise it defaults to
# dog.db inside DOG_INDEX_DIR (the shared ./app/data bind mount in Docker).
DOG_DATABASE_URI = os.environ.get(
    "DOG_DATABASE_URI",
    "sqlite:///" + os.path.abspath(os.path.join(INDEX_DIR, "dog.db")),
)

FINNISH_MONTHS = [
    "tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu",
    "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"
]
