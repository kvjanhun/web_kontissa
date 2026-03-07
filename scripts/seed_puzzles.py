"""One-time script: seed KennoPuzzle + KennoConfig from initial_puzzles.json.

Usage:
    DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 scripts/seed_puzzles.py

Skips slots that already exist in the DB.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URI", "sqlite:////app/data/site.db")

from datetime import datetime, timezone
from app import app
from app.models import db, KennoConfig, KennoPuzzle

SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_puzzles.json")

with app.app_context():
    with open(SEED_PATH, encoding="utf-8") as f:
        seed_data = json.load(f)

    added = 0
    for idx, puzzle in enumerate(seed_data):
        if not db.session.get(KennoPuzzle, idx):
            now = datetime.now(timezone.utc)
            letters_csv = ",".join(puzzle["letters"])
            db.session.add(KennoPuzzle(slot=idx, letters=letters_csv,
                                       created_at=now, updated_at=now))
            added += 1
        if not KennoConfig.query.filter_by(key=f"center_{idx}").first():
            db.session.add(KennoConfig(key=f"center_{idx}",
                                       value=puzzle["center"]))

    if added:
        db.session.commit()
        print(f"Seeded {added} puzzle slots.")
    else:
        print("All slots already populated, nothing to do.")
