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
# From source (recommended while pre-release)
git clone https://github.com/pfrederiksen/arccos-api.git
cd arccos-api
pip install -e ".[dev]"
```

Requires Python ≥ 3.11.

---

## Quick Start

```python
from arccos import ArccosClient

client = ArccosClient(email="you@example.com", password="your_password")
# Credentials are cached in ~/.arccos_creds.json after first login.
# The accessKey (~180 day TTL) silently refreshes the JWT (~3h TTL).

# Rounds
rounds = client.rounds.list()
print(f"{len(rounds)} rounds tracked")

latest = rounds[0]
print(f"Latest: {latest['startTime'][:10]}  score={latest['noOfShots']}")

# Handicap
hcp = client.handicap.current()
print(hcp)

# Club distances
for club in client.clubs.smart_distances():
    print(f"{club.get('clubType')}: {club.get('smartDistance')}y")

# Strokes gained
sg = client.stats.strokes_gained([latest["roundId"]])
print(f"Overall SG: {sg.get('overallSga'):+.2f}")

# Pace of play (fetches all rounds + course names)
pace = client.rounds.pace_of_play()
print(f"Overall avg: {pace['overall_avg_display']}")
for c in pace["course_averages"][:5]:
    print(f"  {c['avg_display']}  {c['course']}  ({c['rounds']}x)")
```

---

## CLI

```bash
export ARCCOS_EMAIL="you@example.com"
export ARCCOS_PASSWORD="your_password"

python -m arccos login        # authenticate + cache credentials
python -m arccos pace         # pace of play by course
python -m arccos rounds       # recent rounds
python -m arccos rounds 20    # last 20 rounds
python -m arccos handicap     # current handicap (raw JSON)
python -m arccos clubs        # smart club distances
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
