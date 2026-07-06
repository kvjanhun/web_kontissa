import os

BASE_URL = "https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset"
REQUEST_HEADERS = {"User-Agent": "erez.ac-dog-show-browser/1.0 (+https://erez.ac/dog/about-crawler)"}
REQUEST_TIMEOUT = 10

SHOW_LIST_TTL = 1800
SHOW_DETAIL_TTL = 600
SHOW_ALL_RESULTS_TTL = 86400

# The "recent" window: shows whose data still changes and is therefore worth
# re-checking (breed lists / entry counts firm up before a show; results and
# judges arrive through the show weekend). The crawler re-indexes recent shows
# on its maintenance pass; everything outside the window is settled history.
# Date-range based (see utils._show_is_recent); roughly the old current-or-
# previous-month label heuristic, made explicit.
SHOW_RECENT_PAST_DAYS = int(os.environ.get("DOG_SHOW_RECENT_PAST_DAYS", "45"))
SHOW_RECENT_FUTURE_DAYS = int(os.environ.get("DOG_SHOW_RECENT_FUTURE_DAYS", "31"))

RESULT_CACHE_LIVE_TTL = int(os.environ.get("DOG_RESULT_LIVE_TTL", "120"))
# Finals overtime: after the evening cutoff on a show's final day, a show that
# still owes its terminal award (main BIS, or the last groups' RYP) keeps
# fetching at a slower cadence instead of going quiet at 21:00, until the hard
# nightly stop. The finals are published in the 21:00–23:30 window, so this is
# where the old evening cutoff silently stranded them.
RESULT_CACHE_OVERTIME_TTL = int(os.environ.get("DOG_RESULT_OVERTIME_TTL", "600"))
# Finals overtime and rescue fetching stop at this Finnish local hour (hard
# nightly stop) and resume at RESULT_SHOW_MORNING_HOUR.
RESULT_FINALS_NIGHT_STOP_HOUR = int(os.environ.get("DOG_RESULT_FINALS_NIGHT_STOP_HOUR", "1"))
# Rescue: a past show still owing its terminal award (crawler was down when the
# finals published) keeps re-fetching the targeted finals pages at this cadence
# during fetch hours, until the settle deadline.
RESULT_CACHE_RESCUE_TTL = int(os.environ.get("DOG_RESULT_RESCUE_TTL", "900"))
# Hard deadline: days after a show's final day past which the cache settles even
# if its terminal award never appeared (the source itself is sometimes
# incomplete). Settling then is logged as settled_incomplete, not silent.
RESULT_SETTLE_DEADLINE_DAYS = int(os.environ.get("DOG_RESULT_SETTLE_DEADLINE_DAYS", "2"))
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
# judged. While a show still owes finals, re-check a bounded, rotating chunk of
# the *targeted* breeds per pass (groups still missing RYP-1, then the RYP-1
# winners' pages for the main BIS) so the finals land within a few passes without
# re-crawling the whole show. The candidate set is derived structurally in
# finals.py, so this only caps how many are re-checked per pass.
RESULT_FINALS_SWEEP_BREED_LIMIT = int(os.environ.get("DOG_RESULT_FINALS_SWEEP_BREED_LIMIT", "30"))
RESULT_LIVE_JOB_STALE_SECONDS = int(os.environ.get("DOG_RESULT_LIVE_JOB_STALE_SECONDS", str(RESULT_CACHE_LIVE_TTL)))
RESULT_SHOW_MORNING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_MORNING_HOUR", "6"))
RESULT_SHOW_EVENING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_EVENING_HOUR", "21"))

# A multi-day show enters the "Jatkuu" (paused) display state during its nightly
# hiatus, or once its results have stalled for this long in the evening wind-down.
# RESULT_PAUSE_EVENING_HOUR floors the stall trigger so a slow midday breed ring
# (or crawler scheduling lag) can't fake a pause during active daytime judging.
RESULT_PAUSE_STALL_SECONDS = int(os.environ.get("DOG_RESULT_PAUSE_STALL_SECONDS", "7200"))
RESULT_PAUSE_EVENING_HOUR = int(os.environ.get("DOG_RESULT_PAUSE_EVENING_HOUR", "17"))

# Per-show stats cache TTL (seconds). The /dog page polls /api/dog/shows every 15s
# whenever a live show is present, and a live show's stats reconstruct its whole-show
# result doc (thousands of rows) from SQLite. Caching the computed stats this long
# decouples that cost from the poll rate (and from the number of viewers). Stats
# only shift when the result cache refreshes (~every live TTL) or the clock crosses
# a phase hour, so a few seconds of staleness is invisible.
SHOW_STATS_CACHE_TTL = float(os.environ.get("DOG_SHOW_STATS_CACHE_TTL", "20"))
RESULT_LOCAL_TIMEZONE = os.environ.get("DOG_RESULT_TIMEZONE", "Europe/Helsinki")

INDEX_DIR = os.environ.get("DOG_INDEX_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))

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
