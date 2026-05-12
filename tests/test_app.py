from __future__ import annotations

import base64
import sqlite3
import hmac
import importlib
import json
from hashlib import sha256
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config

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
            "SCREENSHOT_STORAGE_DIR": str(tmp_path / "screenshots"),
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
        conflict_markers = tuple(marker * 7 for marker in ("<", "=", ">"))
        assert not any(line.startswith(conflict_markers) for line in lines), (
            f"{filename} contains unresolved merge conflict markers"
        )

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


def test_webhook_accepts_configured_bearer_token(tmp_path):
    database_path = tmp_path / "token.db"
    flask_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "WEBHOOK_TOKEN": "secret-token",
        }
    )

    with flask_app.test_client() as token_client:
        rejected = token_client.post("/", json={"event": "missing-token"})
        accepted = token_client.post(
            "/",
            json={"event": "with-token"},
            headers={"Authorization": "Bearer secret-token"},
        )

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()

    assert rejected.status_code == 401
    assert rejected.get_json()["msg"] == "error"
    assert accepted.status_code == 201


def test_webhook_accepts_configured_hmac_signature(tmp_path):
    database_path = tmp_path / "signature.db"
    secret = "signature-secret"
    flask_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "WEBHOOK_SIGNATURE_SECRET": secret,
        }
    )
    body = json.dumps({"event": "signed"}, separators=(",", ":")).encode("utf-8")
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()

    with flask_app.test_client() as signature_client:
        rejected = signature_client.post(
            "/",
            data=body,
            content_type="application/json",
            headers={"X-Webhook-Signature": "sha256=bad"},
        )
        accepted = signature_client.post(
            "/",
            data=body,
            content_type="application/json",
            headers={"X-Webhook-Signature": signature},
        )

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()

    assert rejected.status_code == 401
    assert rejected.get_json()["msg"] == "error"
    assert accepted.status_code == 201


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
    assert response.cache_control.no_store
    assert response.cache_control.max_age == 0
    assert "BetterGI" in response.get_data(as_text=True)


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert not response.cache_control.public
    assert response.cache_control.max_age is None


def test_image_endpoint_returns_404_when_post_has_no_image(client):
    post_id = post_payload(client, {"event": "no-screenshot"})

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 404


def test_image_endpoint_returns_422_for_invalid_base64(client):
    post_id = post_payload(client, {"event": "bad-screenshot", "screenshot": "not base64"})

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 422


def test_image_endpoint_serves_file_backed_png(client, app, transparent_png_base64):
    post_id = post_payload(
        client,
        {"event": "screenshot", "screenshot": transparent_png_base64},
    )

    with app.app_context():
        post = db.session.get(PostData, post_id)
        assert post is not None
        assert post.screenshot is None
        assert post.screenshot_path == f"post_{post_id}.png"
        screenshot_file = Path(app.config["SCREENSHOT_STORAGE_DIR"]) / post.screenshot_path
        assert screenshot_file.is_file()

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_image_endpoint_serves_legacy_base64_png(client, app, transparent_png_base64):
    with app.app_context():
        legacy_post = PostData(event="legacy-screenshot", screenshot=transparent_png_base64)
        db.session.add(legacy_post)
        db.session.commit()
        post_id = legacy_post.id

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_image_endpoint_rejects_unsafe_screenshot_path_without_legacy_fallback(
    client, app, transparent_png_base64
):
    with app.app_context():
        unsafe_post = PostData(
            event="unsafe-screenshot",
            screenshot=transparent_png_base64,
            screenshot_path="../secret.png",
        )
        db.session.add(unsafe_post)
        db.session.commit()
        post_id = unsafe_post.id

    response = client.get(f"/image/{post_id}")

    assert response.status_code == 404


def test_webhook_cleans_up_screenshot_file_when_commit_fails(
    app, monkeypatch, transparent_png_base64
):
    def fail_commit():
        raise RuntimeError("commit failed")

    with app.app_context():
        monkeypatch.setattr(db.session, "commit", fail_commit)

        with pytest.raises(RuntimeError, match="commit failed"):
            save_webhook_payload(
                {"event": "commit-fails", "screenshot": transparent_png_base64}
            )

        screenshot_dir = Path(app.config["SCREENSHOT_STORAGE_DIR"])
        assert list(screenshot_dir.glob("*.png")) == []


def test_alembic_migrations_create_post_data_schema(monkeypatch, tmp_path):
    database_path = tmp_path / "alembic.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("SCREENSHOT_STORAGE_DIR", str(tmp_path / "migration-screenshots"))
    alembic_config = Config("alembic.ini")

    command.upgrade(alembic_config, "head")

    with sqlite3.connect(database_path) as connection:
        columns = [row[1] for row in connection.execute("pragma table_info(post_data)")]

    assert columns == [
        "id",
        "event",
        "result",
        "timestamp",
        "screenshot",
        "create_time",
        "message",
        "screenshot_path",
    ]


def test_alembic_upgrade_existing_baseline_database_after_stamp(monkeypatch, tmp_path):
    database_path = tmp_path / "existing.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "create table post_data ("
            "id integer primary key autoincrement, "
            "event text not null, "
            "result text, "
            "timestamp text, "
            "screenshot text, "
            "create_time datetime not null, "
            "message text"
            ")"
        )

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("SCREENSHOT_STORAGE_DIR", str(tmp_path / "existing-screenshots"))
    alembic_config = Config("alembic.ini")

    command.stamp(alembic_config, "202605110001")
    command.upgrade(alembic_config, "head")

    with sqlite3.connect(database_path) as connection:
        columns = [row[1] for row in connection.execute("pragma table_info(post_data)")]
        version = connection.execute("select version_num from alembic_version").fetchone()[0]

    assert "screenshot_path" in columns
    assert version == "202605110002"


def test_dashboard_supports_pagination_search_result_and_date_filters(client, app):
    with app.app_context():
        for index in range(12):
            result = "success" if index % 2 == 0 else "failure"
            post = PostData(
                event=f"event-{index}",
                result=result,
                message=f"message-{index}",
                create_time=datetime(2026, 5, index + 1, tzinfo=timezone.utc),
            )
            db.session.add(post)
        db.session.commit()

    page_response = client.get("/?page=2&per_page=5")
    search_response = client.get("/?q=message-11")
    result_response = client.get("/?result=success&per_page=20")
    date_response = client.get("/?date_from=2026-05-10&date_to=2026-05-12")

    page_text = page_response.get_data(as_text=True)
    search_text = search_response.get_data(as_text=True)
    result_text = result_response.get_data(as_text=True)
    date_text = date_response.get_data(as_text=True)

    assert page_response.status_code == 200
    assert "第 2 / 3 頁" in page_text
    assert "message-6" in page_text
    assert search_response.status_code == 200
    assert "message-11" in search_text
    assert "message-10" not in search_text
    assert result_response.status_code == 200
    assert "结果：success" in result_text
    assert "结果：failure" not in result_text
    assert date_response.status_code == 200
    assert "message-11" in date_text
    assert "message-9" in date_text
    assert "message-8" not in date_text


def test_dashboard_reports_invalid_date_and_renders_refresh_meta(client):
    response = client.get("/?date_from=not-a-date&refresh=30")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "date_from must use YYYY-MM-DD format" in text
    assert '<meta http-equiv="refresh" content="30">' in text


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
