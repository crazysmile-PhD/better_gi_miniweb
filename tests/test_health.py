import pytest

pytest.importorskip('flask')
pytest.importorskip('flask_sqlalchemy')

from init_database import app


def test_healthz():
    client = app.test_client()

    response = client.get('/api/healthz')

    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}
