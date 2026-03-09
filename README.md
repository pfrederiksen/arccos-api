# arccos-api

Unofficial Python client for the [Arccos Golf](https://arccosgolf.com) platform.

Arccos provides no public API. This library was reverse-engineered from the Arccos Dashboard web app. It gives you full programmatic access to your own golf data — rounds, handicap, club distances, strokes gained, pace of play, and more.

> ⚠️ **Unofficial.** Not affiliated with Arccos Golf LLC. Use with your own account only. Respect their servers (no aggressive polling).

---

## Features

- ✅ Full authentication — email/password → `accessKey` → JWT, with auto-refresh
- ✅ All rounds with start/end times (79 rounds, 33 courses, etc.)
- ✅ Handicap index + revision history
- ✅ Smart club distances (AI-filtered carry distances per club)
- ✅ Strokes gained / SGA analysis
- ✅ Courses played + course metadata
- ✅ Pace of play analysis per course
- ✅ [OpenAPI 3.1 spec](docs/openapi.yaml) — all known endpoints documented
- ✅ Typed, tested, zero external dependencies beyond `requests`

---

## Installation

```bash
git clone https://github.com/pfrederiksen/arccos-api.git
cd arccos-api
pip install -e .
```

Requires Python ≥ 3.11. Dependencies: `requests`, `click`, `rich`.

---

## CLI — Just Use It

The fastest way to get your data. No coding required.

```bash
# 1. Log in (saves credentials to ~/.arccos_creds.json)
arccos login

# 2. Pull your data
arccos rounds                  # recent rounds (table)
arccos rounds -n 50            # last 50 rounds
arccos rounds --after 2025-01-01   # filter by date

arccos handicap                # current handicap index
arccos handicap --history      # revision history

arccos clubs                   # smart club distances
arccos clubs --after 2025-01-01    # distances from this year only

arccos pace                    # pace of play by course
arccos pace -n 50              # analyse last 50 rounds only

arccos stats --latest          # strokes gained for your last round
arccos stats 26685289          # strokes gained for a specific round

arccos export -f csv -o rounds.csv   # export all rounds to CSV
arccos export -f json               # dump raw JSON to stdout

# Every command supports --help
arccos rounds --help
```

**Skip the login prompt** by setting environment variables:
```bash
export ARCCOS_EMAIL="you@example.com"
export ARCCOS_PASSWORD="your_password"
arccos rounds
```

---

## Python Library

Use it in your own scripts or projects:

```python
from arccos import ArccosClient

client = ArccosClient(email="you@example.com", password="your_password")
# Credentials cached in ~/.arccos_creds.json. Auto-refreshes silently.

rounds = client.rounds.list()
print(f"{len(rounds)} rounds tracked")

hcp = client.handicap.current()
print(hcp)

for club in client.clubs.smart_distances():
    print(f"{club.get('clubType')}: {club.get('smartDistance')}y")

sg = client.stats.strokes_gained([rounds[0]["roundId"]])
print(f"Overall SG: {sg.get('overallSga'):+.2f}")

pace = client.rounds.pace_of_play()
print(f"Overall avg pace: {pace['overall_avg_display']}")
```

---

## Project Structure

```
arccos-api/
├── arccos/
│   ├── __init__.py          # Public API surface
│   ├── __main__.py          # CLI (python -m arccos)
│   ├── auth.py              # Two-step auth flow + credential caching
│   ├── client.py            # ArccosClient — main entry point
│   ├── _http.py             # Authenticated HTTP client (auto-refresh)
│   ├── exceptions.py        # Typed exception hierarchy
│   └── resources/
│       ├── rounds.py        # GET /users/{id}/rounds
│       ├── handicap.py      # GET /users/{id}/handicaps
│       ├── clubs.py         # GET /v4/clubs/user/{id}/smart-distances
│       ├── courses.py       # GET /courses/{id}
│       └── stats.py         # GET /v2/sga/shots/{roundIds}
├── docs/
│   └── openapi.yaml         # OpenAPI 3.1 spec (all known endpoints)
├── examples/
│   ├── basic_usage.py       # Getting started
│   └── pace_of_play.py      # Pace of play analysis
├── tests/
│   ├── test_auth.py         # Auth unit tests (mocked)
│   └── test_rounds.py       # Rounds resource tests
└── pyproject.toml
```

---

## API Reference

Full OpenAPI 3.1 spec: [`docs/openapi.yaml`](docs/openapi.yaml)

### Authentication (two-step)

All auth calls go to `https://authentication.arccosgolf.com`.

```
POST /accessKeys
  Body: {"email": "...", "password": "...", "signedInByFacebook": "F"}
  → {"userId": "...", "accessKey": "...", "secret": "..."}

POST /tokens
  Body: {"userId": "...", "accessKey": "..."}
  → {"userId": "...", "token": "<jwt>"}
```

The JWT expires in ~3 hours. The `accessKey` is valid for ~180 days.
Call `POST /tokens` again with the same `accessKey` to refresh the JWT silently.

### API Endpoints

All calls go to `https://api.arccosgolf.com` with `Authorization: Bearer <token>`.

| Resource | Method | Path |
|----------|--------|------|
| Rounds   | GET | `/users/{userId}/rounds?offSet=0&limit=200&roundType=flagship` |
| Round    | GET | `/users/{userId}/rounds/{roundId}` |
| Holes    | GET | `/users/{userId}/rounds/{roundId}/holes` |
| Handicap | GET | `/users/{userId}/handicaps/latest` |
| Hcp Hist | GET | `/users/{userId}/handicaps?rounds=20` |
| Clubs    | GET | `/v4/clubs/user/{userId}/smart-distances` |
| Club Shots | GET | `/users/{userId}/bags/{bagId}/clubs/{clubId}/shots` |
| Courses Played | GET | `/users/{userId}/coursesPlayed` |
| Course   | GET | `/courses/{courseId}?courseVersion=1` |
| SGA      | GET | `/v2/sga/shots/{roundId}?roundId={roundId}` |
| Personal Bests | GET | `/users/{userId}/personalBests?tags=allTimeBest` |

### Round Object

```json
{
  "roundId": 26685289,
  "courseId": 10769,
  "courseVersion": 11,
  "startTime": "2026-03-08T19:17:28.000000Z",
  "endTime":   "2026-03-09T00:46:31.000000Z",
  "noOfShots": 85,
  "noOfHoles": 18,
  "isEnded":   "T",
  "teeId": 1
}
```

**Pace of play** = `endTime - startTime`. Both are UTC timestamps.

---

## How It Was Reverse-Engineered

1. Loaded `dashboard.arccosgolf.com` and fetched the webpack bundle
2. Searched for `authentication.arccosgolf.com` and `api.arccosgolf.com` URL patterns
3. Found the Redux async thunk for login — it calls `AT({key:"accessKeys"})` then `AT({key:"token"})`
4. Identified the two-step auth flow: `POST /accessKeys` → `POST /tokens`
5. Extracted the full API config object from the bundle (all endpoint URL templates)
6. Confirmed all documented endpoints against the live API

The JWT uses HS256. The `accessKey` is a hex string (SHA-1 length). The `secret` field returned by `/accessKeys` appears unused by the web client.

---

## Development

```bash
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check arccos/

# Type check
mypy arccos/
```

---

## Known Gaps

- [ ] Full hole/shot schema (structure partially documented)
- [ ] Social/feed endpoints (`/users/{id}/feed`, follows, etc.)
- [ ] Driving range session data (`roundType=range`)
- [ ] Full strokes gained response schema
- [ ] Async client (`httpx`)

PRs welcome.

---

## Disclaimer

Not affiliated with, endorsed by, or connected to Arccos Golf LLC.
Use your own account credentials only. This project is for personal data access and research.

MIT License.
