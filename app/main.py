from flask import Flask, render_template
from flask_pymongo import PyMongo
from flask import jsonify
from cowsay import get_output_string

app = Flask(__name__)

app.config["MONGO_URI"] = "mongodb://mongo:27017/site"
mongo = PyMongo(app)

@app.route("/")
def index():
    sections = mongo.db.sections.find()
    return render_template("index.html", sections=sections)

@app.route("/seed")
def seed():
    if mongo.db.sections.count_documents({}) == 0:
        mongo.db.sections.insert_many([
            {"slug": "who", "title": "Who", "content": "Konsta Janhunen, currently working as an Integration Developer at Digia Finland Oy, also a computer science student at University of Helsinki. My most common nickname throughout the years has been erezac."},
            {"slug": "what", "title":"What", "content": "<p>Integrations is all about tying multiple systems together with various technologies. My part involves a lot of trouble tackling and information hunting, SQL queries being an important tool. Transferring data securely is essential and I've become well-versed in the practicalities of encryption, for example, with GnuPG.</p><p>On my free-time I tend to mostly stare at screens a bit more. Thankfully, our young flat-coated retriever keeps me active and forces me outside. I'm an avid PC gamer and my favourites include games in several genres from RPGs to FPSes, roguelikes to 4Xes.</p><p>I also like reading about technology and trying new stuff. This site is self-hosted on an Intel NUC running Red Hat Linux. The server is currently used only to host this project and an SSH server for easy access in LAN. DNS server and email-forwarding are provided by Domainhotelli and ImprovMX</p><p>The site is rendered by Flask, served by Gunicorn, powered by MongoDB and containerised with Docker Compose. Changes to GitHub remote are automatically deployed with a webhook.</p>"},
            {"slug": "where", "title":"Where", "content": "You can email me to konsta at erez.ac or message me in Telegram. I have a LinkedIn profile but I'm inactive there. I'm currently not looking for a new job."}
        ])
        return "Seeded!"
    else:
        return "The database is already seeded."

@app.route("/api/cowsay")
def cowsay_route():
    try:
        output = get_output_string("cow", "moo")
        return jsonify({"output":output})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
