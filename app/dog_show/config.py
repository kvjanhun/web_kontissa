import os

BASE_URL = "https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset"
REQUEST_HEADERS = {"User-Agent": "erez.ac-dog-show-browser/1.0 (+https://erez.ac/dog/about-crawler)"}
REQUEST_TIMEOUT = 10

SHOW_LIST_TTL = 1800
SHOW_DETAIL_TTL = 600
SHOW_ALL_RESULTS_TTL = 86400

# The "recent" window: shows whose data still changes and is therefore worth
# re-checking (breed lists / entry counts firm up before a show; results and
# judges arrive through the show weekend, with source corrections trailing for
# about a week). The crawler re-indexes recent shows on its maintenance pass;
# everything outside the window is settled, immutable history.
# Date-range based (see utils._show_is_recent).
SHOW_RECENT_PAST_DAYS = int(os.environ.get("DOG_SHOW_RECENT_PAST_DAYS", "7"))
SHOW_RECENT_FUTURE_DAYS = int(os.environ.get("DOG_SHOW_RECENT_FUTURE_DAYS", "31"))

# The index pass runs three jobs that want three different cadences, and running
# them on one budget meant the slowest need set the rate for all of them:
#   - discovery (a show missing from the index, or indexed empty) is nearly free
#     and time-critical, so it is never rate-limited here — the pass interval is
#     its cadence;
#   - a show happening *today* has breeds gaining their check icons through the
#     day, and that is the cheap tier the result crawler steers by, so it wants
#     minutes;
#   - everything else in the recent window drifts over weeks (entry counts firm
#     up before a show, corrections trail it), so hours is plenty and it is what
#     the per-pass budget should mostly not be spent on.
INDEX_LIVE_TTL = int(os.environ.get("DOG_INDEX_LIVE_TTL", "300"))
INDEX_RECENT_TTL = int(os.environ.get("DOG_INDEX_RECENT_TTL", "21600"))

RESULT_CACHE_LIVE_TTL = int(os.environ.get("DOG_RESULT_LIVE_TTL", "120"))
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
# A settled breed capture is final, so a live refresh re-fetches only newly judged
# breeds and the ones still mid-ring — except the show finals (RYP/BIS-1/BIS
# JUN/VET), which Showlink appends onto the winners' already-captured breed rows
# after every ring is judged. While a show still owes finals, re-check a bounded,
# rotating chunk of the *targeted* breeds per pass (groups still missing RYP-1,
# then the RYP-1 winners' pages for the main BIS) so the finals land within a few
# passes without re-crawling the whole show. The candidate set is derived
# structurally in finals.py, so this only caps how many are re-checked per pass.
RESULT_FINALS_SWEEP_BREED_LIMIT = int(os.environ.get("DOG_RESULT_FINALS_SWEEP_BREED_LIMIT", "30"))
# The finals probe: two requests (R=RYP, R=BIS) that read the show's own finals
# pages. They are the only direct view of what has been awarded, so once they
# show anything — or every ring is captured and the finals are imminent — they
# are read every pass. While they are still empty, and the day's rings are the
# only thing moving, this is how long to wait between reads.
RESULT_FINALS_PROBE_TTL = int(os.environ.get("DOG_RESULT_FINALS_PROBE_TTL", "600"))
# Quiescence: how long the show's terminal state must come back unchanged before
# it may settle. It confirms a conclusion the settle ladder already reached; it
# is never the conclusion itself, because a show goes quiet mid-judging — two
# NORD shows observed on 2026-09-19 had gaps of 18, 14, 12, 12 and 10 minutes
# between result rows while judging was plainly still going on, and a lunch break
# can run far longer.
RESULT_QUIESCENCE_SECONDS = int(os.environ.get("DOG_RESULT_QUIESCENCE_SECONDS", "1800"))
# Only *observed* time counts toward that window. A gap longer than this means
# nobody was watching — the night stop, a crawler restart, a run of failures —
# and contributes nothing, or the overnight gap alone would settle every show at
# the morning re-open.
RESULT_QUIESCENCE_MAX_GAP = int(os.environ.get("DOG_RESULT_QUIESCENCE_MAX_GAP", "360"))
# Showlink fills a breed page class by class while the ring is judged, so a breed
# captured the moment its first class appeared holds a fraction of the entry. Such
# a capture is re-fetched until the source calls the ring done (honour roll crowns
# ROP, or every entered dog has a row). This caps how many of those unsettled
# captures one pass re-checks; the rest rotate in on following passes.
RESULT_UNSETTLED_RECHECK_BREED_LIMIT = int(os.environ.get("DOG_RESULT_UNSETTLED_RECHECK_BREED_LIMIT", "48"))
# Tiering of the per-pass breed budget. One judge judges one breed, finishes it,
# and moves to the next, so a show has at most one ring per judge in flight —
# 10 judges over 96 breeds on show 14014. Their queues are a *priority* signal
# only: results are entered by club secretaries who may register a row long after
# its ring finished, so a judge moving on is never evidence that the previous
# breed is complete. The tiers, and the same total budget as the blind rotation
# they replace:
#   hot  — each judge's first unfinished ring; where the data actually is;
#   warm — every other capture that is not final yet, rotating;
#   cool — captures that look final, swept slowly while the show is live, which
#          is what catches a row registered after the ring passed.
RESULT_HOT_BREED_LIMIT = int(os.environ.get("DOG_RESULT_HOT_BREED_LIMIT", "12"))
RESULT_WARM_BREED_LIMIT = int(os.environ.get("DOG_RESULT_WARM_BREED_LIMIT", "24"))
RESULT_COOL_SWEEP_BREED_LIMIT = int(os.environ.get("DOG_RESULT_COOL_SWEEP_BREED_LIMIT", "12"))
# Adaptive backoff, and the fallback wherever the judge queue misfires (judge not
# yet known, a ring judged out of programme order): a breed whose rows grew since
# the last fetch stays hot; one that comes back unchanged this many times cools
# to the warm rotation. Needs no judge and no schedule.
RESULT_BREED_STATIC_FETCH_LIMIT = int(os.environ.get("DOG_RESULT_BREED_STATIC_FETCH_LIMIT", "3"))
RESULT_LIVE_JOB_STALE_SECONDS = int(os.environ.get("DOG_RESULT_LIVE_JOB_STALE_SECONDS", str(RESULT_CACHE_LIVE_TTL)))
# The fetch window, Finnish local hours: the only time anything in this package
# is allowed to reach Showlink. No dog show runs outside it, so a request made
# then is waste. Every path shares it through utils._in_fetch_window — the
# result plan, the crawler's index pass, and the show-list refresh.
RESULT_SHOW_MORNING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_MORNING_HOUR", "8"))
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
