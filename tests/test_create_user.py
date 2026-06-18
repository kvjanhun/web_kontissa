from app.models import User, db


def test_create_user_and_reset_password(app):
    from app.create_user import create, reset_password

    with app.app_context():
        assert create("localadmin", "local@example.com", "oldpass", role="admin") is True

        user = User.query.filter_by(email="local@example.com").first()
        assert user is not None
        assert user.role == "admin"
        assert user.check_password("oldpass") is True

        assert reset_password("local@example.com", "newpass") is True
        db.session.refresh(user)
        assert user.check_password("newpass") is True


def test_create_user_rejects_duplicate_email(app):
    from app.create_user import create

    with app.app_context():
        assert create("first", "same@example.com", "pass") is True
        assert create("second", "same@example.com", "pass") is False


def test_reset_password_rejects_missing_user(app):
    from app.create_user import reset_password

    with app.app_context():
        assert reset_password("missing@example.com", "pass") is False
