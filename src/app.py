"""Starter skeleton for the MAP project.

Implements only the common contract: /health, /version, / and /reset.
Add the routes required by your assigned theme in this file or in separate modules.
"""

import datetime
import os
import time

from flask import Flask, jsonify, request

APP_NAME = "map-project"
APP_VERSION = "0.1.0"
LOAN_PERIOD_DAYS = 14

STARTED_AT = time.monotonic()

app = Flask(__name__)


def parse_iso_date(value: object) -> datetime.date | None:
    """Validate and parse a date strictly in YYYY-MM-DD format."""
    if not isinstance(value, str):
        return None
    val = value.strip()
    if len(val) != 10 or val[4] != "-" or val[7] != "-":
        return None
    try:
        return datetime.date.fromisoformat(val)
    except ValueError:
        return None


class Store:
    """Holds the application data in memory.

    Everything is lost when the container restarts.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.next_id = 1
        self.next_book_id = 1
        self.next_loan_id = 1
        self.books: dict[int, dict] = {}
        self.loans: dict[int, dict] = {}

    def get_active_loans_count(self, book_id: int) -> int:
        return sum(
            1 for loan in self.loans.values()
            if loan["book_id"] == book_id and loan["return_date"] is None
        )

    def get_book_representation(self, book: dict) -> dict:
        active_loans = self.get_active_loans_count(book["id"])
        return {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "isbn": book["isbn"],
            "copies": book["copies"],
            "available_copies": max(0, book["copies"] - active_loans),
        }

    def get_loan_representation(
        self, loan: dict, as_of_date: datetime.date | None = None
    ) -> dict:
        due_date = datetime.date.fromisoformat(loan["due_date"])
        if loan["return_date"] is not None:
            days_overdue = loan["days_overdue"]
        elif as_of_date is not None:
            diff = (as_of_date - due_date).days
            days_overdue = max(0, diff)
        else:
            days_overdue = 0

        return {
            "id": loan["id"],
            "book_id": loan["book_id"],
            "borrower": loan["borrower"],
            "loan_date": loan["loan_date"],
            "due_date": loan["due_date"],
            "return_date": loan["return_date"],
            "days_overdue": days_overdue,
        }


store = Store()


@app.get("/health")
def health():
    return jsonify(
        status="ok",
        uptime_seconds=int(time.monotonic() - STARTED_AT),
    )


@app.get("/version")
def version():
    return jsonify(
        app=APP_NAME,
        version=APP_VERSION,
        commit=os.getenv("APP_COMMIT", "dev"),
        built_at=os.getenv("APP_BUILT_AT", "unknown"),
    )


@app.post("/reset")
def reset():
    store.reset()
    return "", 204


@app.get("/")
def home():
    commit = os.getenv("APP_COMMIT", "dev")
    return f"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="utf-8"><title>{APP_NAME}</title></head>
<body>
<h1>{APP_NAME}</h1>
<p>Autor: Otean Victor, grupa 2.1</p>
<p>Tema: 6 - Registru de împrumuturi</p>
<p>Versiune: {APP_VERSION}, commit {commit}</p>
</body></html>"""


@app.post("/books")
def create_book():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="validation", message="Request body must be a JSON object"), 400

    title = data.get("title")
    author = data.get("author")
    isbn = data.get("isbn")
    copies = data.get("copies")

    if not isinstance(title, str) or not title.strip():
        return jsonify(error="validation", message="Field 'title' is required and must be non-empty"), 400

    if not isinstance(author, str) or not author.strip():
        return jsonify(error="validation", message="Field 'author' is required and must be non-empty"), 400

    if not isinstance(isbn, str) or len(isbn.strip()) != 13 or not isbn.strip().isdigit():
        return jsonify(error="validation", message="Field 'isbn' must be exactly 13 digits"), 400

    isbn_clean = isbn.strip()
    for existing in store.books.values():
        if existing["isbn"] == isbn_clean:
            return jsonify(error="conflict", message="A book with this ISBN already exists"), 409

    if type(copies) is not int or copies <= 0:
        return jsonify(error="validation", message="Field 'copies' must be a strictly positive integer"), 400

    book = {
        "id": store.next_book_id,
        "title": title.strip(),
        "author": author.strip(),
        "isbn": isbn_clean,
        "copies": copies,
    }
    store.books[book["id"]] = book
    store.next_book_id += 1

    return jsonify(store.get_book_representation(book)), 201


@app.get("/books")
def list_books():
    books = [store.get_book_representation(book) for book in store.books.values()]
    books.sort(key=lambda b: (b["title"], b["id"]))
    return jsonify(books), 200


@app.post("/loans")
def create_loan():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="validation", message="Request body must be a JSON object"), 400

    book_id = data.get("book_id")
    borrower = data.get("borrower")
    loan_date_str = data.get("loan_date")

    if type(book_id) is not int:
        return jsonify(error="validation", message="Field 'book_id' must be an integer"), 400

    if book_id not in store.books:
        return jsonify(error="not_found", message="Book not found"), 404

    book = store.books[book_id]
    book_rep = store.get_book_representation(book)
    if book_rep["available_copies"] <= 0:
        return jsonify(error="conflict", message="No available copies for this book"), 409

    if not isinstance(borrower, str) or not borrower.strip():
        return jsonify(error="validation", message="Field 'borrower' is required and must be non-empty"), 400

    loan_date_obj = parse_iso_date(loan_date_str)
    if loan_date_obj is None:
        return jsonify(error="validation", message="Field 'loan_date' must be in YYYY-MM-DD format"), 400

    due_date_obj = loan_date_obj + datetime.timedelta(days=LOAN_PERIOD_DAYS)

    loan = {
        "id": store.next_loan_id,
        "book_id": book_id,
        "borrower": borrower.strip(),
        "loan_date": loan_date_obj.isoformat(),
        "due_date": due_date_obj.isoformat(),
        "return_date": None,
        "days_overdue": 0,
    }
    store.loans[loan["id"]] = loan
    store.next_loan_id += 1

    return jsonify(store.get_loan_representation(loan)), 201


@app.post("/loans/<int:loan_id>/return")
def return_loan(loan_id: int):
    if loan_id not in store.loans:
        return jsonify(error="not_found", message="Loan not found"), 404

    loan = store.loans[loan_id]
    if loan["return_date"] is not None:
        return jsonify(error="conflict", message="Loan has already been returned"), 409

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="validation", message="Request body must be a JSON object"), 400

    return_date_str = data.get("return_date")
    ret_date_obj = parse_iso_date(return_date_str)
    if ret_date_obj is None:
        return jsonify(error="validation", message="Field 'return_date' must be in YYYY-MM-DD format"), 400

    loan_date_obj = datetime.date.fromisoformat(loan["loan_date"])
    if ret_date_obj < loan_date_obj:
        return jsonify(error="validation", message="return_date cannot be earlier than loan_date"), 400

    due_date_obj = datetime.date.fromisoformat(loan["due_date"])
    days_diff = (ret_date_obj - due_date_obj).days
    days_overdue = max(0, days_diff)

    loan["return_date"] = ret_date_obj.isoformat()
    loan["days_overdue"] = days_overdue

    return jsonify(store.get_loan_representation(loan)), 200


@app.get("/loans")
def list_loans():
    active_param = request.args.get("active")
    if active_param is not None and active_param.lower() not in ("true", "false"):
        return jsonify(error="validation", message="Parameter 'active' must be 'true' or 'false'"), 400

    as_of_param = request.args.get("as_of")
    as_of_date = None
    if as_of_param is not None:
        as_of_date = parse_iso_date(as_of_param)
        if as_of_date is None:
            return jsonify(error="validation", message="Parameter 'as_of' must be in YYYY-MM-DD format"), 400

    overdue_param = request.args.get("overdue")
    if overdue_param is not None and overdue_param.lower() not in ("true", "false"):
        return jsonify(error="validation", message="Parameter 'overdue' must be 'true' or 'false'"), 400

    results = []
    for loan in store.loans.values():
        loan_rep = store.get_loan_representation(loan, as_of_date=as_of_date)
        is_active = (loan["return_date"] is None)
        is_overdue = (loan_rep["days_overdue"] > 0)

        if active_param is not None:
            expected_active = (active_param.lower() == "true")
            if is_active != expected_active:
                continue

        if overdue_param is not None:
            expected_overdue = (overdue_param.lower() == "true")
            if is_overdue != expected_overdue:
                continue

        results.append(loan_rep)

    results.sort(key=lambda l: l["id"])
    return jsonify(results), 200


@app.get("/admin/stats")
def admin_stats():
    expected_user = os.getenv("ADMIN_USER")
    expected_password = os.getenv("ADMIN_PASSWORD")

    # Credentials must be configured via environment variables and cannot be empty
    if not expected_user or not expected_password:
        return (
            jsonify(error="unauthorized", message="Admin credentials are not configured"),
            401,
            {"WWW-Authenticate": 'Basic realm="Admin Area"'},
        )

    auth = request.authorization
    if not auth or auth.username != expected_user or auth.password != expected_password:
        return (
            jsonify(error="unauthorized", message="Invalid or missing credentials"),
            401,
            {"WWW-Authenticate": 'Basic realm="Admin Area"'},
        )

    total_books = len(store.books)
    total_copies = sum(book["copies"] for book in store.books.values())
    available_copies = sum(
        store.get_book_representation(book)["available_copies"]
        for book in store.books.values()
    )
    total_loans = len(store.loans)
    active_loans = sum(
        1 for loan in store.loans.values() if loan["return_date"] is None
    )
    returned_loans = sum(
        1 for loan in store.loans.values() if loan["return_date"] is not None
    )
    overdue_loans = sum(
        1 for loan in store.loans.values()
        if loan["return_date"] is not None and loan["days_overdue"] > 0
    )

    return jsonify(
        total_books=total_books,
        total_copies=total_copies,
        available_copies=available_copies,
        total_loans=total_loans,
        active_loans=active_loans,
        returned_loans=returned_loans,
        overdue_loans=overdue_loans,
    ), 200


@app.errorhandler(404)
def not_found(_):
    return jsonify(error="not_found", message="route does not exist"), 404


if __name__ == "__main__":
    port_env = os.getenv("PORT")
    if port_env:
        port = int(port_env)
    else:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", 8080))
                port = 8080
        except OSError:
            port = 5000
            print(
                f"[INFO] Port 8080 is reserved or occupied on this machine. "
                f"Starting local dev server on http://localhost:{port}"
            )

    app.run(host="0.0.0.0", port=port)
