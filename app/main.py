from flask import Flask, render_template
from flask import jsonify
from cowsay import get_output_string

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/cowsay")
def cowsay_route():
    try:
        output = get_output_string("cow", "moo")
        return jsonify({"output":output})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
