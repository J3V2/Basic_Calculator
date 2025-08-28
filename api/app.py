import os
import logging
from decimal import Decimal
from typing import Any, Dict

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from expr_eval import ExpressionEvaluator  # your safe evaluator

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Configure rate-limit storage via env var. For production set RATELIMIT_STORAGE_URL to e.g. redis://redis:6379
storage_uri = os.getenv("RATELIMIT_STORAGE_URL", "memory://")

# Initialize limiter in a robust way (explicit storage_uri avoids warning when provided)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute", "1000/day"],
    storage_uri=storage_uri,
)
limiter.init_app(app)

# evaluator instance
_evaluator = ExpressionEvaluator(allow_ans=True)


def validate_payload(payload: Dict) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "JSON object expected"
    if "expr" not in payload:
        return False, "Missing 'expr' field"
    if not isinstance(payload["expr"], str):
        return False, "'expr' must be a string"
    if "decimal" in payload and not isinstance(payload["decimal"], bool):
        return False, "'decimal' must be boolean"
    if "variables" in payload and not isinstance(payload["variables"], dict):
        return False, "'variables' must be an object mapping names to numbers"
    return True, ""


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/eval", methods=["POST"])
@limiter.limit("30/minute")
def eval_expr():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    ok, msg = validate_payload(payload)
    if not ok:
        return jsonify({"error": msg}), 400

    expr = payload["expr"]
    ans = payload.get("ans", None)
    variables = payload.get("variables", None)
    decimal_flag = payload.get("decimal", False)

    # Security: simple expression length limit
    if len(expr) > 2000:
        return jsonify({"error": "Expression too long"}), 400

    try:
        result = _evaluator.eval(
            expr, ans=ans, variables=variables, decimal=decimal_flag)
        if isinstance(result, Decimal):
            result_out: Any = str(result)  # preserve Decimal precision
        else:
            result_out = result
        return jsonify({"result": result_out}), 200
    except ZeroDivisionError:
        return jsonify({"error": "division by zero"}), 400
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        app.logger.exception("Unexpected error evaluating expression")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/batch", methods=["POST"])
@limiter.limit("10/minute")
def batch_eval():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if not isinstance(payload, list):
        return jsonify({"error": "Expected a JSON array"}), 400

    results = []
    for item in payload:
        if not isinstance(item, dict) or "expr" not in item:
            results.append({"error": "invalid item"})
            continue
        try:
            res = _evaluator.eval(
                item["expr"],
                ans=item.get("ans"),
                variables=item.get("variables"),
                decimal=item.get("decimal", False),
            )
            results.append(
                {"result": str(res) if isinstance(res, Decimal) else res})
        except Exception as e:
            results.append({"error": str(e)})
    return jsonify(results), 200


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "rate limit exceeded"}), 429


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
