"""
Pace of play analysis — slowest and fastest courses.

Usage:
    export ARCCOS_EMAIL="you@example.com"
    export ARCCOS_PASSWORD="your_password"
    python examples/pace_of_play.py
"""

import os
from arccos import ArccosClient

client = ArccosClient(email=os.environ["ARCCOS_EMAIL"], password=os.environ["ARCCOS_PASSWORD"])

print("Fetching all rounds (this may take a moment)...")
data = client.rounds.pace_of_play()

print(f"\n📊 Pace of Play — {len(data['rounds'])} rounds across {len(data['course_averages'])} courses")
print(f"   Overall average: {data['overall_avg_display']}\n")

print("🐌 Slowest courses:")
for c in data["course_averages"][:5]:
    bar = "█" * (c["avg_minutes"] // 20)
    print(f"   {c['avg_display']}  {bar}  {c['course']} ({c['rounds']}x)")

print("\n⚡ Fastest courses:")
for c in reversed(data["course_averages"][-5:]):
    bar = "░" * (c["avg_minutes"] // 20)
    print(f"   {c['avg_display']}  {bar}  {c['course']} ({c['rounds']}x)")

print("\n📅 Most recent rounds:")
for r in data["rounds"][:5]:
    flag = "🔴" if r["duration_minutes"] > 300 else "🟡" if r["duration_minutes"] > 270 else "🟢"
    print(f"   {flag} {r['date']}  {r['duration_display']}  {r['course']}  score={r['score']}")
