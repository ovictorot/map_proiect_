"""Starter skeleton for the MAP project.

Implements only the common contract: /health, /version, / and /reset.
Add the routes required by your assigned theme in this file or in separate modules.
"""

import os
import time

from flask import Flask, jsonify, request

APP_NAME = "map-project"
APP_VERSION = "0.1.0"
LOAN_PERIOD_DAYS = 14

STARTED_AT = time.monotonic()

app = Flask(__name__)


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


@app.errorhandler(404)
def not_found(_):
    return jsonify(error="not_found", message="route does not exist"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
