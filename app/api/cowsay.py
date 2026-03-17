import structlog
from flask import Blueprint, jsonify, request
from cowsay import get_output_string, char_names, CHARS
from cowsay.main import generate_char

logger = structlog.get_logger(__name__)

cowsay_bp = Blueprint('cowsay', __name__)


def _generate_think_bubble(text):
    """Generate a think bubble with ( ) instead of | | and o connectors."""
    import re
    from cowsay.main import wrap_lines

    lines = [line.strip() for line in text.split('\n')]
    lines = wrap_lines([line for line in lines if line])
    text_width = max(len(line) for line in lines)

    output = ["  " + "_" * text_width]
    if len(lines) > 1:
        output.append(" (" + " " * text_width + ")")
    for line in lines:
        output.append("( " + line + " " * (text_width - len(line) + 1) + ")")
    if len(lines) > 1:
        output.append(" (" + " " * text_width + ")")
    output.append("  " + "-" * text_width)

    return output


def _get_think_output(char, text):
    """Generate cowthink output: think bubble + character with o connector."""
    bubble = _generate_think_bubble(text)
    text_width = max(len(line) for line in bubble) - 4
    char_lines = generate_char(CHARS[char], text_width)
    # Replace the backslash connector with 'o' for think mode
    result = '\n'.join(bubble + char_lines)
    result = result.replace('\\', 'o', 2)
    return result


@cowsay_bp.route("/api/cowsay")
def cowsay_route():
    try:
        message = request.args.get("message", "moo")
        message = message[:200].replace("\n", " ").replace("\r", "")
        if not message.strip():
            message = "moo"

        character = request.args.get("character", "cow")
        if character not in char_names:
            return jsonify({"error": f"Unknown character: {character}. Use /api/cowsay/characters for a list."}), 400

        think = request.args.get("think", "").lower() in ("true", "1")

        if think:
            output = _get_think_output(character, message)
        else:
            output = get_output_string(character, message)

        return jsonify({"output": output})
    except Exception:
        logger.exception("cowsay_error")
        return jsonify({"error": "Internal server error"}), 500


@cowsay_bp.route("/api/cowsay/characters")
def cowsay_characters():
    return jsonify({"characters": list(char_names)})
