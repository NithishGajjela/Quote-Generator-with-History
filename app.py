import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()

QUOTE_API_URL = "https://zenquotes.io/api/random"
QUOTE_API_NAME = "ZenQuotes"
QUOTE_API_TIMEOUT = (3, 15)


class QuoteAPIError(Exception):
    """Raised when the external quote service cannot provide a valid quote."""


class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        created_at = self.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author,
            "source": self.source,
            "created_at": created_at.isoformat(),
        }


def fetch_random_quote():
    try:
        response = requests.get(QUOTE_API_URL, timeout=QUOTE_API_TIMEOUT)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise QuoteAPIError("The quote service is taking too long to respond. Please try again.") from exc
    except requests.RequestException as exc:
        raise QuoteAPIError("The quote service is unavailable right now. Please try again.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise QuoteAPIError("The quote service returned an invalid response. Please try again.") from exc

    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise QuoteAPIError("The quote service returned an invalid response. Please try again.")

    text = data[0].get("q")
    author = data[0].get("a")
    if not isinstance(text, str) or not text.strip():
        raise QuoteAPIError("The quote service returned an invalid quote. Please try again.")
    if not isinstance(author, str) or not author.strip():
        raise QuoteAPIError("The quote service returned an invalid author. Please try again.")

    return text.strip(), author.strip()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///quotes.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/quotes/random")
    def random_quote():
        try:
            text, author = fetch_random_quote()
        except QuoteAPIError as exc:
            app.logger.warning("Quote API request failed: %s", exc)
            return jsonify({"error": str(exc)}), 502

        quote = Quote(text=text, author=author, source=QUOTE_API_NAME)
        try:
            db.session.add(quote)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not save fetched quote")
            return jsonify({"error": "The quote was fetched but could not be saved. Please try again."}), 500

        return jsonify(quote.to_dict()), 201

    @app.get("/api/quotes/history")
    def quote_history():
        quotes = db.session.execute(
            db.select(Quote).order_by(Quote.created_at.desc(), Quote.id.desc())
        ).scalars()
        return jsonify([quote.to_dict() for quote in quotes])

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=False, port=5057)
