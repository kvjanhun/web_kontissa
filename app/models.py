from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.String, nullable=True)
