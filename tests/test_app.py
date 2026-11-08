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


# --- /loans and /loans/{id}/return ---

def test_full_loan_workflow_from_assignment(client):
    # 1. create book with 1 copy
    book_res = client.post(
        "/books",
        json={
            "title": "Structuri de date",
            "author": "N. Wirth",
            "isbn": "9780130220059",
            "copies": 1,
        },
    )
    assert book_res.status_code == 201
    assert book_res.get_json()["available_copies"] == 1

    # 2. borrow the book: due_date must be 2026-10-15 (2026-10-01 + 14 days)
    loan_res = client.post(
        "/loans",
        json={
            "book_id": 1,
            "borrower": "Ana Pop",
            "loan_date": "2026-10-01",
        },
    )
    assert loan_res.status_code == 201
    loan = loan_res.get_json()
    assert loan["id"] == 1
    assert loan["due_date"] == "2026-10-15"
    assert loan["return_date"] is None
    assert loan["days_overdue"] == 0

    # Book available copies is now 0
    books = client.get("/books").get_json()
    assert books[0]["available_copies"] == 0

    # 3. second loan fails with 409 because available_copies is 0
    second_loan_res = client.post(
        "/loans",
        json={
            "book_id": 1,
            "borrower": "Ion Popescu",
            "loan_date": "2026-10-02",
        },
    )
    assert second_loan_res.status_code == 409
    assert second_loan_res.get_json()["error"] == "conflict"

    # 4. return exactly on due date: days_overdue must be 0, not 1
    ret_res = client.post("/loans/1/return", json={"return_date": "2026-10-15"})
    assert ret_res.status_code == 200
    ret_body = ret_res.get_json()
    assert ret_body["return_date"] == "2026-10-15"
    assert ret_body["days_overdue"] == 0

    # Book available copies is back to 1
    books = client.get("/books").get_json()
    assert books[0]["available_copies"] == 1

    # 5. second return on same loan returns 409
    second_ret_res = client.post("/loans/1/return", json={"return_date": "2026-10-16"})
    assert second_ret_res.status_code == 409
    assert second_ret_res.get_json()["error"] == "conflict"


def test_loan_return_overdue_calculation(client):
    client.post(
        "/books",
        json={"title": "Python 101", "author": "Guido", "isbn": "9781234567890", "copies": 1},
    )
    client.post(
        "/loans",
        json={"book_id": 1, "borrower": "Alice", "loan_date": "2026-10-01"},
    )
    # due date is 2026-10-15; return on 2026-10-18 -> 3 days overdue
    ret = client.post("/loans/1/return", json={"return_date": "2026-10-18"})
    assert ret.status_code == 200
    assert ret.get_json()["days_overdue"] == 3


def test_create_loan_validation_errors(client):
    # Book not found
    res = client.post(
        "/loans",
        json={"book_id": 999, "borrower": "Bob", "loan_date": "2026-10-01"},
    )
    assert res.status_code == 404
    assert res.get_json()["error"] == "not_found"

    # Invalid book_id type
    res = client.post(
        "/loans",
        json={"book_id": "not_an_int", "borrower": "Bob", "loan_date": "2026-10-01"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Missing / empty borrower
    client.post(
        "/books",
        json={"title": "Book", "author": "A", "isbn": "9781111111111", "copies": 1},
    )
    res = client.post(
        "/loans",
        json={"book_id": 1, "borrower": "   ", "loan_date": "2026-10-01"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Invalid date format
    res = client.post(
        "/loans",
        json={"book_id": 1, "borrower": "Bob", "loan_date": "01-10-2026"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Non-string date
    res = client.post(
        "/loans",
        json={"book_id": 1, "borrower": "Bob", "loan_date": 12345},
    )
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Invalid calendar numbers (month 99)
    res = client.post(
        "/loans",
        json={"book_id": 1, "borrower": "Bob", "loan_date": "2026-99-99"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Non-dict JSON
    res = client.post("/loans", data="invalid", content_type="application/json")
    assert res.status_code == 400


def test_return_loan_validation_errors(client):
    # Loan not found
    res = client.post("/loans/999/return", json={"return_date": "2026-10-15"})
    assert res.status_code == 404
    assert res.get_json()["error"] == "not_found"

    client.post(
        "/books",
        json={"title": "Book", "author": "A", "isbn": "9781111111111", "copies": 1},
    )
    client.post(
        "/loans",
        json={"book_id": 1, "borrower": "Bob", "loan_date": "2026-10-05"},
    )

    # Return date earlier than loan date
    res = client.post("/loans/1/return", json={"return_date": "2026-10-01"})
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Invalid date format
    res = client.post("/loans/1/return", json={"return_date": "invalid-date"})
    assert res.status_code == 400
    assert res.get_json()["error"] == "validation"

    # Invalid body
    res = client.post("/loans/1/return", data="bad", content_type="application/json")
    assert res.status_code == 400


def test_list_loans_filters_and_as_of(client):
    client.post(
        "/books",
        json={"title": "Book 1", "author": "A", "isbn": "9781111111111", "copies": 5},
    )
    # Loan 1: active, loan_date 2026-10-01 -> due_date 2026-10-15
    client.post("/loans", json={"book_id": 1, "borrower": "User 1", "loan_date": "2026-10-01"})
    # Loan 2: returned, loan_date 2026-10-01 -> returned 2026-10-10
    client.post("/loans", json={"book_id": 1, "borrower": "User 2", "loan_date": "2026-10-01"})
    client.post("/loans/2/return", json={"return_date": "2026-10-10"})

    # Filter active=true
    active_loans = client.get("/loans?active=true").get_json()
    assert len(active_loans) == 1
    assert active_loans[0]["id"] == 1

    # Filter active=false
    closed_loans = client.get("/loans?active=false").get_json()
    assert len(closed_loans) == 1
    assert closed_loans[0]["id"] == 2

    # Check as_of on active loan:
    # On 2026-10-15 (due date) -> overdue=false (0 days overdue)
    res_due = client.get("/loans?as_of=2026-10-15&active=true").get_json()
    assert res_due[0]["days_overdue"] == 0

    # On 2026-10-17 -> overdue=true (2 days overdue)
    res_late = client.get("/loans?as_of=2026-10-17&overdue=true").get_json()
    assert len(res_late) == 1
    assert res_late[0]["id"] == 1
    assert res_late[0]["days_overdue"] == 2

    # On 2026-10-17 with overdue=false -> only Loan 2 (which was returned without delay)
    res_not_late = client.get("/loans?as_of=2026-10-17&overdue=false").get_json()
    assert len(res_not_late) == 1
    assert res_not_late[0]["id"] == 2

    # Invalid query parameters return 400
    assert client.get("/loans?active=not_bool").status_code == 400
    assert client.get("/loans?overdue=not_bool").status_code == 400
    assert client.get("/loans?as_of=bad-date").status_code == 400


# --- Extensia 2: /admin/stats ---

def test_admin_stats_unauthorized_when_env_not_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_USER", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    response = client.get("/admin/stats")
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_admin_stats_unauthorized_when_credentials_missing(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")
    response = client.get("/admin/stats")
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_admin_stats_unauthorized_when_credentials_wrong(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")
    # Wrong password
    response = client.get("/admin/stats", auth=("admin", "wrong_pass"))
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"

    # Wrong user
    response = client.get("/admin/stats", auth=("hacker", "secret123"))
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_admin_stats_success_empty_store(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")
    response = client.get("/admin/stats", auth=("admin", "secret123"))
    assert response.status_code == 200
    body = response.get_json()
    assert body["total_books"] == 0
    assert body["total_copies"] == 0
    assert body["available_copies"] == 0
    assert body["total_loans"] == 0
    assert body["active_loans"] == 0
    assert body["returned_loans"] == 0
    assert body["overdue_loans"] == 0


def test_admin_stats_calculates_all_metrics_correctly(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")

    # Add 2 books: Book 1 has 3 copies, Book 2 has 2 copies (total copies = 5)
    client.post("/books", json={"title": "B1", "author": "A", "isbn": "1111111111111", "copies": 3})
    client.post("/books", json={"title": "B2", "author": "A", "isbn": "2222222222222", "copies": 2})

    # Loan 1: Book 1 borrowed, remains active
    client.post("/loans", json={"book_id": 1, "borrower": "Alice", "loan_date": "2026-10-01"})

    # Loan 2: Book 1 borrowed, returned on time (due 2026-10-15, ret 2026-10-15 -> days_overdue = 0)
    client.post("/loans", json={"book_id": 1, "borrower": "Bob", "loan_date": "2026-10-01"})
    client.post("/loans/2/return", json={"return_date": "2026-10-15"})

    # Loan 3: Book 2 borrowed, returned late (due 2026-10-15, ret 2026-10-18 -> days_overdue = 3)
    client.post("/loans", json={"book_id": 2, "borrower": "Charlie", "loan_date": "2026-10-01"})
    client.post("/loans/3/return", json={"return_date": "2026-10-18"})

    # Fetch stats
    response = client.get("/admin/stats", auth=("admin", "secret123"))
    assert response.status_code == 200
    stats = response.get_json()

    assert stats["total_books"] == 2
    assert stats["total_copies"] == 5
    # Active loans = 1 (on Book 1), so available_copies = 5 - 1 = 4
    assert stats["available_copies"] == 4
    assert stats["total_loans"] == 3
    assert stats["active_loans"] == 1
    assert stats["returned_loans"] == 2
    assert stats["overdue_loans"] == 1
