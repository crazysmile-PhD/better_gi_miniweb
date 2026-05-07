"""Production-friendly launcher for Better GI MiniWeb."""

from __future__ import annotations

import os
import sys
from importlib import import_module

MIN_PYTHON = (3, 14)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "222"))
BETTERGI_VERSION = "0.40+"


def ensure_supported_python() -> None:
    """Fail early with a clear message when Python is too old."""

    if sys.version_info < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        current = sys.version.split()[0]
        raise SystemExit(
            f"Python {required}+ is required; current interpreter is {current}. "
            "Create a fresh virtual environment with the latest stable Python and reinstall requirements."
        )


def import_runtime_dependencies() -> tuple[object, object]:
    """Import runtime dependencies and explain how to install them if missing."""

    try:
        pywsgi = import_module("gevent.pywsgi")
        application_module = import_module("app")
    except ModuleNotFoundError as exc:
        missing = exc.name or "a required package"
        raise SystemExit(
            f"Missing dependency: {missing}. Install dependencies with:\n"
            f"  {sys.executable} -m pip install -r requirements.txt"
        ) from exc

    return pywsgi, application_module


def main() -> None:
    ensure_supported_python()
    pywsgi, application_module = import_runtime_dependencies()

    with application_module.app.app_context():
        application_module.db.create_all()

    banner = f"""
BetterGI 前端展示頁（適用於 BetterGI {BETTERGI_VERSION}）
=================
Web Dashboard: http://127.0.0.1:{PORT}/
Webhook URL:   http://127.0.0.1:{PORT}/
Health Check:  http://127.0.0.1:{PORT}/health
=================
""".strip()
    print(banner, flush=True)
    print("服務已啟動。按 Ctrl+C 停止。", flush=True)

    server = pywsgi.WSGIServer((HOST, PORT), application_module.app)
    server.serve_forever()


if __name__ == "__main__":
    main()
