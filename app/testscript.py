from main import app, db, Section
from sqlalchemy import text

with app.app_context():
    # Method 1: ORM
    rows = Section.query.all()
    for row in rows:
        print(f"{row.id}: {row.slug} → {row.title}")

    # Method 2: Raw SQL
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM sections"))
        for row in result:
            print(dict(row))
