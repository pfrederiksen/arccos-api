"""
Basic usage examples for the arccos Python client.

Set environment variables before running:
    export ARCCOS_EMAIL="you@example.com"
    export ARCCOS_PASSWORD="your_password"
    python examples/basic_usage.py
"""

import os
from arccos import ArccosClient

email    = os.environ["ARCCOS_EMAIL"]
password = os.environ["ARCCOS_PASSWORD"]

client = ArccosClient(email=email, password=password)
print(f"Logged in as {client.email} (userId: {client.user_id})\n")

# --- Handicap ---
print("=== Handicap ===")
try:
    hcp = client.handicap.current()
    print(f"Current: {hcp}")
except Exception as e:
    print(f"  Error: {e}")

# --- Recent rounds ---
print("\n=== Recent Rounds (last 5) ===")
rounds = client.rounds.list(limit=5)
for r in rounds:
    date = r.get("startTime", "")[:10]
    score = r.get("noOfShots", "?")
    cid   = r.get("courseId", "?")
    print(f"  {date}  score={score}  courseId={cid}  roundId={r['roundId']}")

# --- Club distances ---
print("\n=== Smart Club Distances ===")
try:
    clubs = client.clubs.smart_distances()
    for club in clubs[:5]:
        name = club.get("clubType") or club.get("name", "?")
        dist = club.get("smartDistance") or club.get("averageDistance", "?")
        print(f"  {name}: {dist}y")
except Exception as e:
    print(f"  Error: {e}")

# --- Courses played ---
print("\n=== Courses Played ===")
try:
    played = client.courses.played()
    print(f"  {len(played)} courses")
    for c in played[:3]:
        print(f"  - {c.get('courseName', c.get('courseId'))}")
except Exception as e:
    print(f"  Error: {e}")

# --- Strokes gained (latest round) ---
print("\n=== Strokes Gained (latest round) ===")
try:
    latest_id = rounds[0]["roundId"]
    sg = client.stats.strokes_gained([latest_id])
    for k, v in sg.items():
        if "Sga" in k or "sga" in k:
            print(f"  {k}: {v:+.2f}" if isinstance(v, (int, float)) else f"  {k}: {v}")
except Exception as e:
    print(f"  Error: {e}")
