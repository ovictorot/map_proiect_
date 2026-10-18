"""Tests for the MAP project - Registru de imprumuturi.

Covers the common contract routes (/health, /version, /, /reset)
plus additional edge cases to meet the minimum 10 tests and 50% coverage requirements.
"""
import pytest

from src.app import APP_NAME, APP_VERSION, app, store


@pytest.fixture(autouse=True)
def reset_store():
    """Reset store before each test to ensure isolation."""
    store.reset()
    yield
    store.reset()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


# --- /health ---

def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body


def test_health_uptime_is_non_negative(client):
    body = client.get("/health").get_json()
    assert body["uptime_seconds"] >= 0


def test_health_content_type_is_json(client):
    response = client.get("/health")
    assert response.content_type == "application/json"


# --- /version ---

def test_version_returns_200(client):
    assert client.get("/version").status_code == 200


def test_version_reads_commit_from_env(client, monkeypatch):
    monkeypatch.setenv("APP_COMMIT", "abc1234")
    body = client.get("/version").get_json()
    assert body["commit"] == "abc1234"


def test_version_returns_app_name(client):
    body = client.get("/version").get_json()
    assert body["app"] == APP_NAME


def test_version_returns_version_string(client):
    body = client.get("/version").get_json()
    assert body["version"] == APP_VERSION


def test_version_default_commit_is_dev(client, monkeypatch):
    monkeypatch.delenv("APP_COMMIT", raising=False)
    body = client.get("/version").get_json()
    assert body["commit"] == "dev"


def test_version_reads_built_at_from_env(client, monkeypatch):
    monkeypatch.setenv("APP_BUILT_AT", "2026-10-18T00:00:00Z")
    body = client.get("/version").get_json()
    assert body["built_at"] == "2026-10-18T00:00:00Z"


# --- /reset ---

def test_reset_returns_no_content(client):
    assert client.post("/reset").status_code == 204


def test_reset_rejects_get(client):
    assert client.get("/reset").status_code == 405


def test_reset_clears_store_next_id(client):
    store.next_id = 42
    client.post("/reset")
    assert store.next_id == 1


def test_reset_response_body_is_empty(client):
    response = client.post("/reset")
    assert response.data == b""


# --- / (home) ---

def test_home_returns_200(client):
    assert client.get("/").status_code == 200


def test_home_returns_html(client):
    response = client.get("/")
    assert response.content_type.startswith("text/html")


def test_home_contains_author(client):
    response = client.get("/")
    assert b"Otean Victor" in response.data


def test_home_contains_tema(client):
    response = client.get("/")
    assert b"Tema" in response.data or b"tema" in response.data


def test_home_contains_app_name(client):
    response = client.get("/")
    assert APP_NAME.encode() in response.data


# --- 404 handler ---

def test_unknown_route_returns_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404


def test_unknown_route_returns_not_found_error(client):
    body = client.get("/does-not-exist").get_json()
    assert body["error"] == "not_found"


def test_unknown_route_content_type_is_json(client):
    response = client.get("/nu-exista")
    assert response.content_type == "application/json"
