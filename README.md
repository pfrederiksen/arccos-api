# arccos-api

Unofficial Python client and CLI for the [Arccos Golf](https://arccosgolf.com) platform.

Arccos provides no public API. This library was reverse-engineered from the Arccos Dashboard web app. It gives you full programmatic access to your own golf data — rounds, handicap, club distances, pace of play, and more.

> **Unofficial.** Not affiliated with Arccos Golf LLC. Use with your own account only. Respect their servers (no aggressive polling).

## Installation

```bash
pip install arccos-api
```

Or install from source:

```bash
git clone https://github.com/pfrederiksen/arccos-api.git
cd arccos-api
pip install -e .
```

Requires Python >= 3.11. Dependencies: `requests`, `click`, `rich`.

## CLI

### Quick start

```bash
arccos login       # authenticate and save credentials
arccos rounds      # your recent rounds
arccos handicap    # handicap breakdown
arccos clubs       # smart club distances
```

### Commands

| Command | Description |
|---------|-------------|
| `arccos login` | Authenticate and cache credentials to `~/.arccos_creds.json` |
| `arccos rounds` | List recent rounds with date, score, holes, course |
| `arccos round <id>` | Hole-by-hole detail (score, putts, FIR, GIR) with totals |
| `arccos handicap` | Handicap breakdown by category (overall, driving, approach, etc.) |
| `arccos clubs` | Smart club distances with make/model, range, and shot count |
| `arccos courses` | List all courses you've played |
| `arccos pace` | Pace of play analysis by course (color-coded) |
| `arccos stats <id>` | Strokes gained analysis for a round |
| `arccos export` | Export rounds to JSON, CSV, or NDJSON |
| `arccos logout` | Clear cached credentials |

Every command supports `--json` for raw JSON output and `--help` for usage info.

### Usage examples

```bash
# Rounds
arccos rounds                         # last 20 rounds
arccos rounds -n 50                   # last 50
arccos rounds --after 2025-01-01      # filter by date
arccos rounds --json                  # raw JSON

# Round detail
arccos round 26685289                 # hole-by-hole breakdown

# Handicap
arccos handicap                       # category breakdown
arccos handicap --history             # revision history

# Club distances
arccos clubs                          # active clubs with make/model
arccos clubs --after 2025-01-01       # distances from this year only

# Courses
arccos courses                        # all courses played

# Pace of play
arccos pace                           # all rounds, slowest courses first
arccos pace -n 20                     # last 20 rounds only

# Export
arccos export -f csv -o rounds.csv    # export to CSV file
arccos export -f json                 # dump JSON to stdout
arccos export -f ndjson               # newline-delimited JSON
```

### Example output

```
$ arccos clubs
            Smart Club Distances
╭──────┬────────────────┬───────┬─────────┬──────────┬───────╮
│ Club │ Model          │ Smart │ Longest │    Range │ Shots │
├──────┼────────────────┼───────┼─────────┼──────────┼───────┤
│ Dr   │ PING G425 SFT  │  244y │    285y │ 241–259y │   517 │
│ 3w   │ PING G440 SFT  │  203y │    223y │ 194–210y │    71 │
│ 5w   │ PING G425      │  170y │    206y │ 164–177y │   285 │
│ 4i   │ Callaway Elyte │  141y │    171y │ 137–151y │    35 │
│ 9i   │ Callaway Elyte │  125y │    149y │ 117–128y │    43 │
│ Pw   │ Callaway Elyte │   98y │    113y │  95–101y │    25 │
│ Aw   │ Callaway Elyte │   87y │    104y │   87–91y │    49 │
│ 56   │ Callaway Opus  │   69y │    186y │   67–71y │   644 │
╰──────┴────────────────┴───────┴─────────┴──────────┴───────╯

$ arccos round 26685289
╭─── Round 26685289 ───╮
│ Date:   2026-03-08   │
│ Course: Las Vegas GC │
│ Score:  85 (+13)     │
│ Holes:  18           │
╰──────────────────────╯
            Hole-by-Hole
╭──────┬───────┬───────┬─────┬─────╮
│ Hole │ Score │ Putts │ FIR │ GIR │
├──────┼───────┼───────┼─────┼─────┤
│    1 │     5 │     2 │  T  │  F  │
│    2 │     5 │     2 │  F  │  T  │
│  ... │   ... │   ... │ ... │ ... │
├──────┼───────┼───────┼─────┼─────┤
│  Tot │    85 │    34 │     │     │
╰──────┴───────┴───────┴─────┴─────╯

$ arccos handicap
  Handicap Breakdown
╭────────────┬───────╮
│ Category   │   HCP │
├────────────┼───────┤
│ Overall    │ -17.3 │
│ Driving    │ -20.4 │
│ Approach   │ -25.6 │
│ Short Game │ -21.2 │
│ Putting    │  -8.5 │
╰────────────┴───────╯

$ arccos pace -n 10
Pace of Play — 10 rounds across 9 courses   Overall avg: 4h 39m

                  By Course (slowest first)
╭────┬──────────┬───────────────────────┬────────╮
│    │ Avg Time │ Course                │ Rounds │
├────┼──────────┼───────────────────────┼────────┤
│ 🔴 │   5h 05m │ Las Vegas GC          │      2 │
│ 🟡 │   5h 00m │ Siena GC              │      1 │
│ 🟢 │   3h 27m │ Furnace Creek Ranch   │      1 │
╰────┴──────────┴───────────────────────┴────────╯
```

### Environment variables

Skip the login prompt by setting:

```bash
export ARCCOS_EMAIL="you@example.com"
export ARCCOS_PASSWORD="your_password"
arccos rounds
```

## Python Library

```python
from arccos import ArccosClient

client = ArccosClient(email="you@example.com", password="your_password")
# Credentials cached in ~/.arccos_creds.json. Auto-refreshes silently.

# Rounds
rounds = client.rounds.list(limit=10)
for r in rounds:
    print(f"{r['startTime'][:10]}  score={r['noOfShots']}  {r.get('courseName', '')}")

# Round detail (includes embedded hole-by-hole data)
rd = client.rounds.get(rounds[0]["roundId"])
for hole in rd["holes"]:
    print(f"  Hole {hole['holeId']}: {hole['noOfShots']} shots, {hole['putts']} putts")

# Handicap breakdown
hcp = client.handicap.current()
print(f"Overall: {hcp['userHcp']:.1f}")
print(f"Driving: {hcp['driveHcp']:.1f}")

# Club distances (returns clubId as bag slot — see bag API for name mapping)
for club in client.clubs.smart_distances():
    dist = club["smartDistance"]["distance"]
    print(f"  Club {club['clubId']}: {dist:.0f}y")

# Bag configuration (maps clubId → clubType + make/model)
profile = client._http.get(f"/users/{client.user_id}")
bag = client.clubs.bag(str(profile["bagId"]))
for club in bag["clubs"]:
    if club.get("isDeleted") != "T":
        print(f"  {club['clubMakeOther']} {club['clubModelOther']}")

# Courses played
for course in client.courses.played():
    print(f"  {course.get('courseName', course['courseId'])}")

# Pace of play analysis
pace = client.rounds.pace_of_play()
print(f"Overall avg: {pace['overall_avg_display']}")
for c in pace["course_averages"][:5]:
    print(f"  {c['avg_display']}  {c['course']}")

# Personal bests
bests = client.stats.personal_bests()
```

## API Reference

Full OpenAPI 3.1 spec: [`docs/openapi.yaml`](docs/openapi.yaml)

### Authentication

All auth calls go to `https://authentication.arccosgolf.com`.

| Step | Endpoint | Body | Returns |
|------|----------|------|---------|
| 1. Get access key | `POST /accessKeys` | `{"email", "password", "signedInByFacebook": "F"}` | `{"userId", "accessKey", "secret"}` |
| 2. Get JWT | `POST /tokens` | `{"userId", "accessKey"}` | `{"userId", "token"}` |

The JWT expires in ~3 hours. The `accessKey` is valid for ~180 days. Refresh by calling `POST /tokens` again.

### Endpoints

All data calls go to `https://api.arccosgolf.com` with `Authorization: Bearer <token>`.

| Resource | Method | Path |
|----------|--------|------|
| User profile | GET | `/users/{userId}` (includes `bagId`, `bags[]`) |
| Bag / clubs | GET | `/users/{userId}/bags/{bagId}` (club config with make/model) |
| Rounds | GET | `/users/{userId}/rounds?offSet=0&limit=200&roundType=flagship` |
| Round detail | GET | `/users/{userId}/rounds/{roundId}` (includes `holes[]` with `shots[]`) |
| Handicap | GET | `/users/{userId}/handicaps/latest` |
| Handicap history | GET | `/users/{userId}/handicaps?rounds=20` |
| Smart distances | GET | `/v4/clubs/user/{userId}/smart-distances` |
| Courses played | GET | `/users/{userId}/coursesPlayed` |
| Course metadata | GET | `/courses/{courseId}?courseVersion=1` |
| Course search | GET | `/v2/courses?search={query}` |
| Personal bests | GET | `/users/{userId}/personalBests?tags=allTimeBest` |

### Key data structures

**Round** (from `GET /users/{id}/rounds/{roundId}`):
```json
{
  "roundId": 26685289,
  "courseId": 10769,
  "courseName": "Las Vegas GC",
  "startTime": "2026-03-08T19:17:28.000000Z",
  "endTime": "2026-03-09T00:46:31.000000Z",
  "noOfShots": 85,
  "noOfHoles": 18,
  "overUnder": 13,
  "holes": [
    {
      "holeId": 1, "noOfShots": 5, "putts": 2,
      "isGir": "F", "isFairWay": "T",
      "shots": [{"clubId": 1, "clubType": 1, "distance": 237.0}]
    }
  ]
}
```

**Smart distance** (from `GET /v4/clubs/user/{id}/smart-distances`):
```json
{
  "clubId": 1,
  "smartDistance": {"distance": 243.9, "unit": "yd"},
  "longest": {"distance": 285.4, "unit": "yd"},
  "range": {"low": 241.1, "high": 259.1, "unit": "yd"},
  "usage": {"count": 517}
}
```

**Bag club** (from `GET /users/{id}/bags/{bagId}`):
```json
{
  "clubId": 1, "clubType": 1,
  "clubMakeOther": "PING", "clubModelOther": "G425 SFT",
  "isDeleted": "F"
}
```

> `clubId` is a user-specific bag slot. Resolve to a display name via: bag's `clubType` → standard name (1=Dr, 2=3w, 3=5w, 5=4i, ..., 11=Pw, 12=Putter, 43=Aw, 53=56°).

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest                  # tests with coverage (90%+, 96 tests)
ruff check arccos/      # lint
mypy arccos/            # type check
```

Coverage report: `htmlcov/index.html`. Minimum threshold: 80% (configured in `pyproject.toml`).

## Known Gaps

- [ ] SGA endpoint auth (`/v2/sga/shots/` returns 40102 — may need HMAC via `secret`)
- [ ] Social/feed endpoints (`/users/{id}/feed`, follows, etc.)
- [ ] Driving range session data (`roundType=range`)
- [ ] Async client (`httpx`)

PRs welcome.

## Disclaimer

Not affiliated with, endorsed by, or connected to Arccos Golf LLC.
Use your own account credentials only. This project is for personal data access and research.

MIT License.
