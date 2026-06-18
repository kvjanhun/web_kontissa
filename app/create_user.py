"""Utility script to create users and reset passwords.

Local:
    npm run user:create -- konsta konsta@example.com --role admin
    npm run user:reset -- konsta@example.com

Production:
    docker compose exec web python3 -m app.create_user create konsta konsta@example.com --role admin
    docker compose exec web python3 -m app.create_user reset-password konsta@example.com
"""

import argparse
import getpass
import sys

from app import app
from app.models import db, User

VALID_ROLES = {"admin", "user"}


def create(username, email, password, role="user"):
    with app.app_context():
        db.create_all()
        if role not in VALID_ROLES:
            print(f"Invalid role '{role}'. Use one of: {', '.join(sorted(VALID_ROLES))}.")
            return False

        if User.query.filter_by(email=email).first():
            print(f"User with email {email} already exists.")
            return False

        if User.query.filter_by(username=username).first():
            print(f"User with username {username} already exists.")
            return False

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"{role.capitalize()} user '{username}' created successfully.")
        return True


def reset_password(email, password):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            print(f"User with email {email} does not exist.")
            return False

        user.set_password(password)
        db.session.commit()
        print(f"Password reset for user '{user.username}'.")
        return True


def _prompt_password():
    password = getpass.getpass("Password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        raise SystemExit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        raise SystemExit(1)

    return password


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create users and reset passwords.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a user")
    create_parser.add_argument("username")
    create_parser.add_argument("email")
    create_parser.add_argument("--role", choices=sorted(VALID_ROLES), default="user")

    reset_parser = subparsers.add_parser("reset-password", help="Reset a user's password")
    reset_parser.add_argument("email")

    args = parser.parse_args(argv)
    password = _prompt_password()

    if args.command == "create":
        ok = create(args.username, args.email, password, role=args.role)
    else:
        ok = reset_password(args.email, password)

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
