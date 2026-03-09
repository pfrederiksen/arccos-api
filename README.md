# arccos-api

Unofficial Python client for the [Arccos Golf](https://arccosgolf.com) API.

Arccos provides no public API documentation. This client was reverse-engineered from the Arccos Golf Dashboard web app (`dashboard.arccosgolf.com`). It gives you full programmatic access to your golf data.

> **Note:** This is an unofficial client. Use it with your own account data. Be respectful of Arccos's servers (don't hammer endpoints). This project is not affiliated with Arccos Golf.

---

## Features

- ✅ Full authentication (email/password → accessKey → JWT, auto-refresh)
- ✅ All rounds with start/end times
- ✅ Handicap index + history
- ✅ Smart club distances
- ✅ Courses played
- ✅ Strokes gained / SGA data
- ✅ Personal bests
- ✅ Pace of play analysis (per course + overall)

---

## Installation

```bash
pip install requests
```

No other dependencies.

---

## Quick Start

```python
from arccos import ArccosClient

client = ArccosClient(email="you@example.com", password="your_password")

# Get all rounds
rounds = client.get_rounds()
print(f"{len(rounds)} rounds tracked")

# Handicap
handicap = client.get_handicap()
print(f"Handicap Index: {handicap}")

# Club distances
clubs = client.get_club_distances()
for club in clubs:
    print(club)

# Pace of play by course
pace = client.pace_of_play()
print(f"Overall avg: {pace['overall_avg_display']}")
for course in pace['course_averages'][:5]:
    print(f"  {course['avg_display']} — {course['course']} ({course['rounds']}x)")
```

Credentials are cached in `~/.arccos_creds.json` and the JWT auto-refreshes when expired.

---

## CLI

```bash
export ARCCOS_EMAIL="you@example.com"
export ARCCOS_PASSWORD="your_password"

python arccos.py pace      # pace of play per course
python arccos.py rounds    # recent rounds (raw JSON)
python arccos.py handicap  # current handicap
python arccos.py clubs     # smart club distances
```

---

## API Reference

### Auth

```
POST https://authentication.arccosgolf.com/accessKeys
  body: {email, password, signedInByFacebook: "F"}
  → {userId, accessKey, secret}

POST https://authentication.arccosgolf.com/tokens
  body: {userId, accessKey}
  → {userId, token}  (JWT ~3h, accessKey valid ~180 days)
```

### Endpoints (all require `Authorization: Bearer <token>`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users/{userId}/rounds?offSet=0&limit=100&roundType=flagship` | All rounds |
| GET | `/users/{userId}/rounds/{roundId}` | Single round |
| GET | `/users/{userId}/handicaps/latest` | Current handicap |
| GET | `/users/{userId}/handicaps?rounds=20` | Handicap history |
| GET | `/users/{userId}/coursesPlayed` | Courses played |
| GET | `/users/{userId}/personalBests?tags=allTimeBest` | Personal bests |
| GET | `/v4/clubs/user/{userId}/smart-distances` | Club distances |
| GET | `/v2/sga/shots/{roundId}` | Strokes gained for a round |

### Round object

Each round includes:

```json
{
  "roundId": 26685289,
  "courseId": 10769,
  "startTime": "2026-03-08T19:17:28.000000Z",
  "endTime":   "2026-03-09T00:46:31.000000Z",
  "noOfShots": 85,
  "noOfHoles": 18,
  "isEnded": "T",
  "teeId": 1
}
```

Pace of play = `endTime - startTime`.

---

## How It Was Reverse-Engineered

1. Loaded `dashboard.arccosgolf.com` and extracted the webpack bundle
2. Searched for `authentication.arccosgolf.com` and `api.arccosgolf.com` URL patterns
3. Found the Redux thunk: `login` dispatches `AT({key:"accessKeys"})` → `AT({key:"token"})`
4. Traced the two-step auth flow: `/accessKeys` → `/tokens`
5. Confirmed all endpoints by testing against the live API

---

## Contributing

PRs welcome. Known gaps:
- [ ] Round hole-by-hole shot data (endpoint exists, schema TBD)
- [ ] Social/feed endpoints
- [ ] Full SGA/strokes gained schema documentation
- [ ] Async client (httpx)

---

## Disclaimer

This project is not affiliated with, endorsed by, or connected to Arccos Golf LLC. Use your own account credentials only.
