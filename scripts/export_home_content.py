"""Export the database-backed home content to the build snapshot.

`nuxt generate` bakes `frontend/locales/home-content.snapshot.json` into the
static output for a correct first paint / SEO; the client then re-fetches
`/api/home-content` for freshness. Run this at deploy time (against the host
data volume) so the baked snapshot reflects the current DB. If it fails, the
build falls back to the committed snapshot.

The snapshot shape is `{ "<locale>": <overlay map>, ... }`, where each overlay
map is exactly what `GET /api/home-content?locale=<locale>` returns.

Usage:
    DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 scripts/export_home_content.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(ROOT, "frontend", "locales", "home-content.snapshot.json")

os.environ.setdefault("DATABASE_URI", f"sqlite:///{os.path.join(ROOT, 'app', 'data', 'site.db')}")

from app import app  # noqa: E402
from app.models import db  # noqa: E402
from app.home_content import _home_content_map, LOCALES  # noqa: E402


def export(out_path=SNAPSHOT_PATH):
    with app.app_context():
        db.engine.dispose()
        snapshot = {loc: _home_content_map(loc) for loc in LOCALES}

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
        f.write("\n")

    counts = ", ".join(f"{loc}: {len(snapshot[loc])} keys / {len(snapshot[loc]['home.projects'])} projects" for loc in LOCALES)
    print(f"Wrote {out_path} ({counts})")


def _out_path_from_argv():
    # `--out PATH` lets the deploy write to the shared /app/data volume from
    # inside the running container, so it lands on the host build context.
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return SNAPSHOT_PATH


if __name__ == "__main__":
    export(_out_path_from_argv())
