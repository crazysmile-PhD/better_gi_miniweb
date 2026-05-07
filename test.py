"""Development helper server that captures raw webhook requests to post_load/."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)
POST_PATH = Path("post_load")
POST_PATH.mkdir(exist_ok=True)


def save_post(request_info: dict[str, Any]) -> Path:
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    filename = f"{current_time}.txt"
    fullpath = POST_PATH / filename
    with fullpath.open("w", encoding="utf-8") as file:
        json.dump(request_info, file, ensure_ascii=False, indent=2)
    return fullpath


@app.post("/")
def main():
    request_info = {
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "args": dict(request.args),
        "form": dict(request.form),
        "json": request.get_json(silent=True) if request.is_json else None,
        "data": request.get_data(as_text=True),
    }

    saved_path = save_post(request_info)
    return jsonify({"msg": "OK", "path": str(saved_path)})


@app.get("/page")
def page():
    return jsonify({"msg": "OK"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=222, debug=False)
