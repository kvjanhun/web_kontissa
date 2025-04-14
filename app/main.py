from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from cowsay import get_output_string
import requests
import time

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////app/data/site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

_cached_commit_time = None
_cached_commit_timestamp = 0
CACHE_TTL = 60 * 60 * 6  # 6 hours

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.String, nullable=True)

    #def update_timestamp(self):
    #    self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_latest_commit_date():
    global _cached_commit_time, _cached_commit_timestamp
    now = time.time()
    
    if _cached_commit_time and now - _cached_commit_timestamp < CACHE_TTL:
        return _cached_commit_time
    
    url = "https://api.github.com/repos/kvjanhun/web_kontissa/commits/main"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        commit_date = response.json()["commit"]["author"]["date"]
        _cached_commit_time = commit_date
        _cached_commit_timestamp = now
        return commit_date
    except Exception as e:
        print("Error getting commit date:", e)
        return _cached_commit_time

@app.route("/")
def index():
    sections = Section.query.all()

    last_updated = get_latest_commit_date()
    update_date = datetime.fromisoformat(last_updated).strftime("%Y-%m-%d") if last_updated else "2025"

    return render_template("index.html", sections=sections, update_date=update_date)

@app.route("/api/cowsay")
def cowsay_route():
    try:
        output = get_output_string("cow", "moo")
        return jsonify({"output":output})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
