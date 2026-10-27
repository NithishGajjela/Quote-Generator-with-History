# Quote of the Moment

A single-page Flask application that retrieves real random quotes from the public
[ZenQuotes API](https://zenquotes.io/), saves each successful
fetch in SQLite, and displays the saved quotes as history. The backend makes
the API request; no API key or frontend framework is required.

## Requirements

- Python 3.10 or later
- Internet access when fetching a new quote

## Windows setup and run (PowerShell)

Open PowerShell in this project folder, then run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

If PowerShell prevents virtual-environment activation, allow it for the current
terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Open <http://127.0.0.1:5057> in your browser. The SQLite database is created
automatically at `instance\quotes.db` and is retained when Flask is restarted.

## Run tests

With the virtual environment activated:

```powershell
python -m unittest discover -s tests -v
```

The tests cover the application page, quote validation, API timeouts and
failures, database write failures, multiple saves, and history persistence
across separate Flask app instances.

## API and error handling

- `POST /api/quotes/random` fetches and validates the API response, stores one
  quote, and returns the saved record as JSON with HTTP 201.
- `GET /api/quotes/history` returns saved records, newest first.
- The external endpoint is `https://zenquotes.io/api/random`; requests use a
  connect/read timeout. The response must contain non-empty `q` (quote) and
  `a` (author) strings.
- Upstream errors return HTTP 502. A database write error is rolled back,
  logged, and returned as HTTP 500; it is never reported as a successful save.
- The page uses the browser Fetch API to update the quote and history without
  reloading.
