import pytest
from api.app import app as flask_app
from api.app import limiter  # import limiter instance so we can disable in tests


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    # disable limiter to avoid rate-limiter interference and warnings during tests
    limiter.enabled = False
    with flask_app.test_client() as client:
        yield client


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json == {"status": "ok"}


def test_eval_simple(client):
    r = client.post("/eval", json={"expr": "2+3*4"})
    assert r.status_code == 200
    assert r.json["result"] == 14


def test_eval_div_zero(client):
    r = client.post("/eval", json={"expr": "1/0"})
    assert r.status_code == 400
    assert "division" in r.json["error"]


def test_eval_invalid(client):
    r = client.post("/eval", json={"expr": "__import__('os').system('ls')"})
    assert r.status_code == 400


def test_eval_decimal(client):
    r = client.post("/eval", json={"expr": "0.1 + 0.2", "decimal": True})
    assert r.status_code == 200
    assert isinstance(r.json["result"], str)
