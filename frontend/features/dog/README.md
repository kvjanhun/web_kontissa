# Dog Show Browser

This is the frontend for [`/dog`](https://erez.ac/dog), a Finnish dog-show result browser backed by server-side Showlink crawling and persistent caches.

The page lets visitors browse current and past shows, search by show, breed, or judge, open breed results, and use show-wide filters once the full result cache for a show has been warmed.

## How It Is Built

- `DogBrowser.vue` composes the page.
- `useDogBrowser.js` handles route state, API calls, loading states, and polling.
- `dogResults.js` contains reusable result filtering and formatting helpers.
- `components/` contains the list view, show detail view, result view, filters, and shared state blocks.
- `dog.css` contains the feature styling.

The Nuxt route itself lives at `frontend/pages/dog.vue` and only sets metadata/layout before rendering this feature.

## Data Source

The browser talks to this site's Flask API under `/api/dog/*`. The backend fetches public Showlink pages, normalizes the data, and stores JSON cache files under `app/data` in production. The frontend should not scrape Showlink or request every breed page itself.

For operational details, crawler commands, cache files, freshness policy, and backend endpoints, see [`docs/dog-show-browser.md`](../../../docs/dog-show-browser.md).

## Development

Useful checks while working on this feature:

From the repo root:

```bash
python3 -m pytest tests/test_dog.py
cd frontend && npm run test -- dogResults
cd frontend && CI=1 npm run test:e2e -- dog.spec.js
cd frontend && npm run build
```

Run Playwright with `CI=1` or stop any existing Flask server on port 5001 so the E2E suite uses its own seeded database.
