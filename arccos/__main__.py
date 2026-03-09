"""
CLI entry point.

Usage:
    python -m arccos [command]
    arccos [command]          # if installed via pip

Commands:
    login       Authenticate and cache credentials
    pace        Pace of play by course
    rounds      List recent rounds
    handicap    Current handicap index
    clubs       Smart club distances

Environment variables:
    ARCCOS_EMAIL      Account email
    ARCCOS_PASSWORD   Account password
"""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "help":
        print(__doc__)
        return

    email    = os.environ.get("ARCCOS_EMAIL")
    password = os.environ.get("ARCCOS_PASSWORD")

    if not email or not password:
        print("Error: set ARCCOS_EMAIL and ARCCOS_PASSWORD environment variables.")
        sys.exit(1)

    from arccos import ArccosClient
    client = ArccosClient(email=email, password=password)

    if cmd == "login":
        print(f"✅ Logged in as {client.email} (userId: {client.user_id})")

    elif cmd == "pace":
        print("Fetching rounds…")
        data = client.rounds.pace_of_play()
        total  = len(data["rounds"])
        ncours = len(data["course_averages"])
        print(f"\n📊 {total} rounds across {ncours} courses")
        print(f"   Overall avg: {data['overall_avg_display']}\n")
        print("Slowest courses:")
        for c in data["course_averages"][:10]:
            flag = "🔴" if c["avg_minutes"] > 300 else "🟡" if c["avg_minutes"] > 270 else "🟢"
            print(f"  {flag} {c['avg_display']}  {c['course']}  ({c['rounds']}x)")

    elif cmd == "rounds":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        rounds = client.rounds.list(limit=n)
        print(f"Last {len(rounds)} rounds:\n")
        for r in rounds:
            date  = r.get("startTime", "")[:10]
            score = r.get("noOfShots", "?")
            cid   = r.get("courseId", "?")
            print(f"  {date}  score={score}  courseId={cid}  id={r['roundId']}")

    elif cmd == "handicap":
        hcp = client.handicap.current()
        print(json.dumps(hcp, indent=2))

    elif cmd == "clubs":
        clubs = client.clubs.smart_distances()
        for c in clubs:
            name = c.get("clubType") or c.get("name", "?")
            dist = c.get("smartDistance") or c.get("averageDistance", "?")
            shots = c.get("totalShots", "?")
            print(f"  {name:<20} {dist}y  ({shots} shots)")

    else:
        print(f"Unknown command: {cmd!r}")
        print("Run `arccos help` for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
