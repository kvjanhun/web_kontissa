"""Utility script to create a user.

Usage:
    python -c "from app.create_admin import create; create('konsta', 'konsta@erez.ac', 'PASSWORD')"
    python -c "from app.create_admin import create; create('someone', 'someone@erez.ac', 'PASSWORD', role='user')"

Or via docker:
    docker compose exec web python3 -c "from app.create_admin import create; create('konsta', 'konsta@erez.ac', 'PASSWORD')"
    docker compose exec web python3 -c "from app.create_admin import create; create('someone', 'someone@erez.ac', 'PASSWORD', role='user')"
"""

from app import app
from app.models import db, User


def create(username, email, password, role="admin"):
    with app.app_context():
        db.create_all()
        if User.query.filter_by(email=email).first():
            print(f"User with email {email} already exists.")
            return

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"{role.capitalize()} user '{username}' created successfully.")
