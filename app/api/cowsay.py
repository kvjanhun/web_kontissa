from flask import jsonify
from cowsay import get_output_string
from app import app

@app.route("/api/cowsay")
def cowsay_route():
    try:
        output = get_output_string("cow", "moo")
        return jsonify({"output": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
