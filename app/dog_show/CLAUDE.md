# Dog Show Backend - Agent Guide

This package owns backend implementation for the `/dog` feature. The Flask route facade is still `app/api/dog.py`; most behavior lives here.

For frontend behavior, read `../../frontend/features/dog/AGENTS.md`. For operations and crawler tuning, read `../../docs/dog-show-browser.md`.

## Fast Map

| Need | Start here |
|------|------------|
| Flask routes, request validation, rate limits | `../api/dog.py` |
| Environment defaults and TTL constants | `config.py` |
| Date parsing, timestamp formatting, judge/breed normalization | `utils.py` |
| Showlink URL building and HTTP fetches | `showlink.py` |
| BeautifulSoup parsing for show lists, breed lists, breed results | `parsers.py` |
| JSON persistence, in-memory caches, result jobs | `store.py` |
| Indexed show stats, judge enrichment, show-detail cache helpers | `indexing.py` |
| Show-list cache refresh | `shows.py` |
| Breed-index crawler passes | `crawler.py` |
| Whole-show result cache, progress, warmup threads | `result_cache.py` |
| Show/breed/judge search assembly | `search.py` |
| CLI crawler process | `../../scripts/dog_crawl.py` |
| Backend tests | `../../tests/test_dog.py` |

## Boundaries

- Keep public endpoint behavior in `app/api/dog.py`.
- Keep Showlink fetching in `showlink.py`; frontend code must not scrape or fan out over breed pages.
- Keep persisted JSON reads/writes in `store.py` so cache paths and atomic writes stay centralized.
- Keep parser changes in `parsers.py` and cover Showlink page-shape changes in `tests/test_dog.py`.
- Keep result-cache orchestration in `result_cache.py`; this is where concurrency, backoff, stale-cache handling, and immediate warmup limits live.
- Keep crawler loop orchestration in `scripts/dog_crawl.py`; reusable crawler pass functions live in `crawler.py` and `result_cache.py`.

## Compatibility Notes

`app/api/dog.py` intentionally re-exports several private helpers and cache objects while the test suite and crawler migrate to the package modules. Do not remove those exports casually; first update `tests/test_dog.py`, `scripts/dog_crawl.py`, and any docs that still point at the facade.

The shared `_show_index` object is mutated in place by `store._load_index()` so imports from `store.py`, `indexing.py`, and `app/api/dog.py` continue seeing the same dictionary.

## Change Checklist

- Preserve all `/api/dog/*` response shapes unless the frontend and E2E tests are changed deliberately.
- Preserve `dog_show_index.json`, `dog_result_cache/<show_id>.json`, and `dog_result_jobs.json` shapes.
- Keep `group` and `breed` validation in the route layer.
- Keep crawler request volume bounded: respect worker limits, request delay, retry backoff, and `retry_after`.
- Run `python3 -m pytest tests/test_dog.py` after backend behavior changes when the app test harness is healthy.
