"""Utility script to create an admin user.

Usage:
    python -c "from app.create_admin import create; create('konsta', 'konsta@erez.ac', 'PASSWORD')"

Or via docker:
    docker compose exec web python3 -c "from app.create_admin import create; create('konsta', 'konsta@erez.ac', 'PASSWORD')"
"""

from app import app
from app.models import db, User


def create(username, email, password):
    with app.app_context():
        if User.query.filter_by(email=email).first():
            print(f"User with email {email} already exists.")
            return

        user = User(username=username, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Admin user '{username}' created successfully.")
