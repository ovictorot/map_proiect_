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


# --- /books ---

def test_create_book_success(client):
    payload = {
        "title": "Structuri de date",
        "author": "N. Wirth",
        "isbn": "9780130220059",
        "copies": 3,
    }
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 1
    assert body["title"] == "Structuri de date"
    assert body["author"] == "N. Wirth"
    assert body["isbn"] == "9780130220059"
    assert body["copies"] == 3
    assert body["available_copies"] == 3


def test_create_book_duplicate_isbn_returns_409(client):
    payload = {
        "title": "Book 1",
        "author": "Author A",
        "isbn": "9780130220059",
        "copies": 1,
    }
    assert client.post("/books", json=payload).status_code == 201

    payload_duplicate = {
        "title": "Book 2",
        "author": "Author B",
        "isbn": "9780130220059",
        "copies": 2,
    }
    response = client.post("/books", json=payload_duplicate)
    assert response.status_code == 409
    body = response.get_json()
    assert body["error"] == "conflict"


def test_create_book_invalid_isbn_length_or_format(client):
    # 12 digits
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "123456789012", "copies": 1})
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # 14 digits
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "12345678901234", "copies": 1})
    assert res.status_code == 400

    # Non-digit
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "978013022005X", "copies": 1})
    assert res.status_code == 400


def test_create_book_invalid_copies(client):
    # Zero
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "9780130220059", "copies": 0})
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Negative
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "9780130220059", "copies": -5})
    assert res.status_code == 400

    # Boolean (True in Python is an int subclass, but must be rejected)
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "9780130220059", "copies": True})
    assert res.status_code == 400

    # String instead of int
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "9780130220059", "copies": "5"})
    assert res.status_code == 400


def test_create_book_missing_or_empty_fields(client):
    # Empty title
    res = client.post("/books", json={"title": "   ", "author": "A", "isbn": "9780130220059", "copies": 1})
    assert res.status_code == 400

    # Empty author
    res = client.post("/books", json={"title": "T", "author": "", "isbn": "9780130220059", "copies": 1})
    assert res.status_code == 400

    # Missing copies
    res = client.post("/books", json={"title": "T", "author": "A", "isbn": "9780130220059"})
    assert res.status_code == 400

    # Invalid JSON body (not a dict)
    res = client.post("/books", data="not json", content_type="application/json")
    assert res.status_code == 400


def test_list_books_empty(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_sorted_by_title_and_id(client):
    b1 = {"title": "Zeta", "author": "Author 1", "isbn": "1111111111111", "copies": 1}
    b2 = {"title": "Alpha", "author": "Author 2", "isbn": "2222222222222", "copies": 2}
    b3 = {"title": "Alpha", "author": "Author 3", "isbn": "3333333333333", "copies": 3}
    b4 = {"title": "Beta", "author": "Author 4", "isbn": "4444444444444", "copies": 4}

    client.post("/books", json=b1)  # id 1, title Zeta
    client.post("/books", json=b2)  # id 2, title Alpha
    client.post("/books", json=b3)  # id 3, title Alpha
    client.post("/books", json=b4)  # id 4, title Beta

    response = client.get("/books")
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 4
    # Expected ordering: Alpha (id 2), Alpha (id 3), Beta (id 4), Zeta (id 1)
    assert [b["id"] for b in books] == [2, 3, 4, 1]


def test_reset_clears_books_and_resets_ids(client):
    payload = {"title": "Book", "author": "Author", "isbn": "9780130220059", "copies": 1}
    client.post("/books", json=payload)

    # Reset
    assert client.post("/reset").status_code == 204
    assert client.get("/books").get_json() == []

    # New book gets id 1 again
    res = client.post("/books", json=payload)
    assert res.status_code == 201
    assert res.get_json()["id"] == 1
