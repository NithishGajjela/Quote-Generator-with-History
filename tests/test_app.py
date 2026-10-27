import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from sqlalchemy.exc import SQLAlchemyError

from app import Quote, create_app, db


def quote_response(text="A real thought.", author="A Writer"):
    response = Mock()
    response.json.return_value = [{"q": text, "a": author}]
    response.raise_for_status.return_value = None
    return response


class QuoteAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "quotes.db"
        self.database_uri = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": self.database_uri,
            }
        )
        self.extra_apps = []
        self.client = self.app.test_client()

    def tearDown(self):
        for app in [self.app, *self.extra_apps]:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        self.temp_dir.cleanup()

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Quote of the", response.data)
        self.assertIn(b"New Quote", response.data)

    @patch("app.requests.get")
    def test_quote_is_saved_and_returned(self, mock_get):
        mock_get.return_value = quote_response()

        response = self.client.post("/api/quotes/random")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["text"], "A real thought.")
        self.assertEqual(response.json["author"], "A Writer")
        self.assertEqual(response.json["source"], "ZenQuotes")
        mock_get.assert_called_once_with(
            "https://zenquotes.io/api/random", timeout=(3, 15)
        )
        with self.app.app_context():
            self.assertEqual(db.session.query(Quote).count(), 1)

    @patch("app.requests.get")
    def test_multiple_requests_save_each_quote_once(self, mock_get):
        mock_get.side_effect = [
            quote_response("First thought.", "First"),
            quote_response("Second thought.", "Second"),
        ]

        first = self.client.post("/api/quotes/random")
        second = self.client.post("/api/quotes/random")
        history = self.client.get("/api/quotes/history")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(len(history.json), 2)
        self.assertEqual(
            {quote["text"] for quote in history.json},
            {"First thought.", "Second thought."},
        )
        self.assertTrue(all(quote["created_at"] for quote in history.json))

    @patch("app.requests.get")
    def test_history_survives_a_new_app_instance(self, mock_get):
        mock_get.return_value = quote_response()
        self.assertEqual(self.client.post("/api/quotes/random").status_code, 201)

        restarted_app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": self.database_uri,
            }
        )
        self.extra_apps.append(restarted_app)
        response = restarted_app.test_client().get("/api/quotes/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]["text"], "A real thought.")

    @patch("app.requests.get")
    def test_api_timeout_returns_clear_error_without_saving(self, mock_get):
        mock_get.side_effect = requests.Timeout("timed out")

        response = self.client.post("/api/quotes/random")

        self.assertEqual(response.status_code, 502)
        self.assertIn("taking too long", response.json["error"])
        with self.app.app_context():
            self.assertEqual(db.session.query(Quote).count(), 0)

    @patch("app.requests.get")
    def test_api_failure_returns_clear_error_without_saving(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("unavailable")

        response = self.client.post("/api/quotes/random")

        self.assertEqual(response.status_code, 502)
        self.assertIn("unavailable", response.json["error"])
        with self.app.app_context():
            self.assertEqual(db.session.query(Quote).count(), 0)

    @patch("app.requests.get")
    def test_invalid_api_response_is_not_saved(self, mock_get):
        mock_get.return_value = quote_response(text="  ", author="A Writer")

        response = self.client.post("/api/quotes/random")

        self.assertEqual(response.status_code, 502)
        self.assertIn("invalid quote", response.json["error"])
        with self.app.app_context():
            self.assertEqual(db.session.query(Quote).count(), 0)

    @patch("app.requests.get")
    def test_database_failure_does_not_report_success(self, mock_get):
        mock_get.return_value = quote_response()
        with patch.object(db.session, "commit", side_effect=SQLAlchemyError("disk error")):
            response = self.client.post("/api/quotes/random")

        self.assertEqual(response.status_code, 500)
        self.assertIn("could not be saved", response.json["error"])

    @patch("app.requests.get")
    def test_get_history_starts_empty(self, mock_get):
        response = self.client.get("/api/quotes/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])
        mock_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
