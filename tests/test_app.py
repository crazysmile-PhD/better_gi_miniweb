from __future__ import annotations

import base64
import importlib
import sys
from pathlib import Path

import pytest

from bettergi_miniweb import PostData, create_app, db, save_webhook_payload


PYTHON_SOURCE_FILES = (
    "app.py",
    "main.py",
    "run.py",
    "init_database.py",
    "test.py",
    "bettergi_miniweb/__init__.py",
    "bettergi_miniweb/app_factory.py",
    "bettergi_miniweb/config.py",
    "bettergi_miniweb/extensions.py",
    "bettergi_miniweb/models.py",
    "bettergi_miniweb/routes/__init__.py",
    "bettergi_miniweb/routes/dashboard.py",
    "bettergi_miniweb/routes/health.py",
    "bettergi_miniweb/routes/image.py",
    "bettergi_miniweb/routes/webhook.py",
    "bettergi_miniweb/services/__init__.py",
    "bettergi_miniweb/services/webhook_service.py",
    "tests/test_app.py",
)


@pytest.fixture(autouse=True)
def project_database_is_not_created():
    project_db = Path("bettergi.db")
    assert not project_db.exists()
    yield
    assert not project_db.exists()


@pytest.fixture
def app(tmp_path):
    database_path = tmp_path / "test.db"
    flask_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def transparent_png_base64():
    return base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05"
        b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode("ascii")


def post_payload(client, payload: dict[str, str | None]) -> int:
    response = client.post("/", json=payload)
    assert response.status_code == 201
    return response.get_json()["id"]


def test_python_sources_keep_normal_line_structure():
    for filename in PYTHON_SOURCE_FILES:
        path = Path(filename)
        assert path.exists(), f"{filename} does not exist"

        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines, f"{filename} is empty"
        assert max(len(line) for line in lines) <= 160, f"{filename} appears compressed"
        assert not any(
            line.startswith(("<<<<<<<", "=======", ">>>>>>>")) for line in lines
        ), f"{filename} contains unresolved merge conflict markers"

    assert len(Path("app.py").read_text(encoding="utf-8").splitlines()) > 2
    assert len(Path("bettergi_miniweb/app_factory.py").read_text(encoding="utf-8").splitlines()) > 2
    assert len(Path("bettergi_miniweb/__init__.py").read_text(encoding="utf-8").splitlines()) > 2
    assert len(Path("tests/test_app.py").read_text(encoding="utf-8").splitlines()) > 2


def test_webhook_rejects_non_json_request(client):
    response = client.post("/", data="not json", content_type="text/plain")

    assert response.status_code == 400
    assert response.get_json()["msg"] == "error"


def test_webhook_rejects_json_array(client):
    response = client.post("/", json=["not", "an", "object"])

    assert response.status_code == 400
    assert response.get_json()["msg"] == "error"


def test_webhook_rejects_missing_event(client):
    response = client.post("/", json={"message": "missing event"})

    assert response.status_code == 400
    assert response.get_json()["msg"] == "error"


def test_webhook_rejects_blank_event(client):
    response = client.post("/", json={"event": "   "})

    assert response.status_code == 400
    assert response.get_json()["msg"] == "error"


def test_webhook_persists_valid_payload(client, app):
    payload = {
        "event": "notification",
        "result": "success",
        "timestamp": "2026-05-07T00:00:00Z",
        "message": "Hello\nDetails",
    }
    response = client.post("/", json=payload)

    assert response.status_code == 201
    response_body = response.get_json()
    assert response_body["msg"] == "OK"
    assert "id" in response_body

    with app.app_context():
        post = db.session.get(PostData, response_body["id"])
        assert post is not None
        assert post.event == "notification"
        assert post.result == "success"
        assert post.timestamp == "2026-05-07T00:00:00Z"
        assert post.message == "Hello\nDetails"


def test_dashboard_page_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "BetterGI" in response.get_data(as_text=True)


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_image_endpoint_returns_404_when_post_has_no_image(client):
    post_id = post_payload(client, {"event": "no-screenshot"})

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 404


def test_image_endpoint_returns_422_for_invalid_base64(client):
    post_id = post_payload(client, {"event": "bad-screenshot", "screenshot": "not base64"})

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 422


def test_image_endpoint_serves_base64_png(client, transparent_png_base64):
    post_id = post_payload(
        client,
        {"event": "screenshot", "screenshot": transparent_png_base64},
    )

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_app_and_main_compatibility_exports(monkeypatch, tmp_path):
    database_path = tmp_path / "compat.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    sys.modules.pop("main", None)
    sys.modules.pop("app", None)

    app_module = importlib.import_module("app")
    main_module = importlib.import_module("main")

    assert app_module.app is main_module.app
    assert app_module.create_app is create_app
    assert app_module.db is db
    assert app_module.PostData is PostData
    assert app_module.save_webhook_payload is save_webhook_payload
    assert main_module.Post_data is PostData
    assert main_module.save_data is save_webhook_payload


def test_route_method_list_contains_public_api(app):
    routes = {
        (rule.rule, tuple(sorted(rule.methods - {"HEAD", "OPTIONS"})))
        for rule in app.url_map.iter_rules()
    }

    assert ("/", ("GET",)) in routes
    assert ("/", ("POST",)) in routes
    assert ("/health", ("GET",)) in routes
    assert ("/image/<int:image_id>", ("GET",)) in routes
