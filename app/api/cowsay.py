from flask import jsonify, request
from cowsay import get_output_string
from app import app

@app.route("/api/cowsay")
def cowsay_route():
    try:
        message = request.args.get("message", "moo")
        message = message[:200].replace("\n", " ").replace("\r", "")
        if not message.strip():
            message = "moo"
        output = get_output_string("cow", message)
        return jsonify({"output": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
