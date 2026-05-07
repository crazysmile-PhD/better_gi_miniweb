from __future__ import annotations

import base64

from app import PostData, create_app, db


def make_test_app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )


def test_health_endpoint_returns_ok():
    app = make_test_app()
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_webhook_persists_payload_and_page_renders():
    app = make_test_app()
    client = app.test_client()

    payload = {
        "event": "notification",
        "result": "success",
        "timestamp": "2026-05-07T00:00:00Z",
        "message": "Hello\nDetails",
    }
    response = client.post("/", json=payload)

    assert response.status_code == 201
    assert response.get_json()["msg"] == "OK"

    with app.app_context():
        post = db.session.get(PostData, response.get_json()["id"])
        assert post is not None
        assert post.event == "notification"
        assert post.message == "Hello\nDetails"

    page = client.get("/")
    assert page.status_code == 200
    assert "BetterGI" in page.get_data(as_text=True)


def test_webhook_rejects_invalid_payload():
    app = make_test_app()
    response = app.test_client().post("/", json={"message": "missing event"})
    assert response.status_code == 400
    assert response.get_json()["msg"] == "error"


def test_image_endpoint_serves_base64_png():
    app = make_test_app()
    client = app.test_client()
    transparent_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05"
        b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode("ascii")

    created = client.post("/", json={"event": "screenshot", "screenshot": transparent_png})
    image = client.get(f"/image/{created.get_json()['id']}")

    assert image.status_code == 200
    assert image.mimetype == "image/png"
