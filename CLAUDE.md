# CLAUDE.md — Project guide for Claude Code

## Project overview

Unofficial Python client and CLI for the Arccos Golf API. Reverse-engineered from the Arccos Dashboard web app. Provides programmatic access to golf data: rounds, handicap, club distances, strokes gained, and pace of play.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest                      # runs all tests with coverage (configured in pyproject.toml)
pytest tests/test_cli.py    # run a single test file
pytest -k "test_login"      # run tests matching a pattern
```

Coverage config is in `pyproject.toml` under `[tool.coverage.*]`. Minimum threshold: 80%.

## Linting and type checking

```bash
ruff check arccos/
mypy arccos/
```

## Architecture

- **Auth flow**: Two-step — `POST /accessKeys` (email/password) then `POST /tokens` (accessKey → JWT). JWT expires ~3h, accessKey ~180 days. Credentials cached at `~/.arccos_creds.json`.
- **`ArccosClient`**: Main entry point. Initializes auth + HTTP client + resource objects.
- **`HttpClient` (`_http.py`)**: Wraps `requests.Session`. Auto-refreshes JWT, maps errors to typed exceptions.
- **Resources** (`resources/`): One class per API domain (rounds, handicap, clubs, courses, stats). Each takes an `HttpClient` and `user_id`.
- **CLI** (`cli.py`): Click commands with Rich formatting. Uses `_get_client()` helper to build authenticated client from env vars or cached creds.
- **Exceptions** (`exceptions.py`): Hierarchy — `ArccosError` → `ArccosAuthError`, `ArccosNotFoundError`, `ArccosRateLimitError`, `ArccosForbiddenError`.

## Key conventions

- All tests mock the HTTP layer (no real API calls)
- Resources return raw dicts/lists from the API — no custom data classes
- CLI commands all support `--json` for raw JSON output
- Mutable default args use `X | None = None` (not bare `None`)
- Build backend: `setuptools.build_meta`
- Python target: 3.11+
- Ruff rules: E, F, I, UP, B, SIM

## API base URLs

- Auth: `https://authentication.arccosgolf.com`
- API: `https://api.arccosgolf.com`
