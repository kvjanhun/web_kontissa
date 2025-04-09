from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from cowsay import get_output_string

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////app/data/site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.String, nullable=True)

    #def update_timestamp(self):
    #    self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route("/")
def index():
    sections = Section.query.all()

    updated_sections = [s for s in sections if s.last_updated]
    last_updated = max(updated_sections, key=lambda s: s.last_updated).last_updated if updated_sections else None

    update_date = datetime.fromisoformat(last_updated).strftime("%Y-%m-%d") if last_updated else "2025"

    return render_template("index.html", sections=sections, last_updated=update_date)

@app.route("/api/cowsay")
def cowsay_route():
    try:
        output = get_output_string("cow", "moo")
        return jsonify({"output":output})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
