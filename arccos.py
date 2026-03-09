#!/usr/bin/env python3
"""
arccos.py — Unofficial Python client for the Arccos Golf API.

Arccos has no public API. This client was reverse-engineered from the
dashboard web app (dashboard.arccosgolf.com). Use responsibly.

Auth flow (two-step):
  1. POST https://authentication.arccosgolf.com/accessKeys
       body: {email, password, signedInByFacebook: "F"}
       → {userId, accessKey, secret}

  2. POST https://authentication.arccosgolf.com/tokens
       body: {userId, accessKey}
       → {userId, token}  (JWT, expires ~3h)

  Refresh: repeat step 2 with the same accessKey (valid ~180 days).

All API calls: GET/POST https://api.arccosgolf.com/...
  Header: Authorization: Bearer <token>
"""

import json
import base64
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from collections import defaultdict


AUTH_BASE = "https://authentication.arccosgolf.com"
API_BASE  = "https://api.arccosgolf.com"

_CREDS_FILE = Path.home() / ".arccos_creds.json"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def login(email: str, password: str) -> dict:
    """Full login with email + password. Returns creds dict."""
    # Step 1 — get accessKey
    r = requests.post(
        f"{AUTH_BASE}/accessKeys",
        json={"email": email, "password": password, "signedInByFacebook": "F"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    access_key = data["accessKey"]
    user_id    = data["userId"]

    # Step 2 — exchange for JWT
    token = _fetch_token(user_id, access_key)

    creds = {
        "email":      email,
        "user_id":    user_id,
        "access_key": access_key,
        "token":      token,
    }
    _save_creds(creds)
    return creds


def _fetch_token(user_id: str, access_key: str) -> str:
    """Exchange userId + accessKey for a fresh JWT."""
    r = requests.post(
        f"{AUTH_BASE}/tokens",
        json={"userId": user_id, "accessKey": access_key},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["token"]


def _token_expired(token: str) -> bool:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.b64decode(payload))["exp"]
        return datetime.now(timezone.utc).timestamp() > exp - 60
    except Exception:
        return True


def _load_creds() -> Optional[dict]:
    if _CREDS_FILE.exists():
        return json.loads(_CREDS_FILE.read_text())
    return None


def _save_creds(creds: dict) -> None:
    _CREDS_FILE.write_text(json.dumps(creds, indent=2))


class ArccosClient:
    """Authenticated Arccos API client."""

    def __init__(self, email: str = None, password: str = None, creds: dict = None):
        """
        Initialize with email+password, or pass a creds dict directly.
        Creds are cached in ~/.arccos_creds.json and auto-refreshed.
        """
        if creds:
            self._creds = creds
        elif email and password:
            saved = _load_creds()
            if saved and saved.get("email") == email:
                self._creds = saved
            else:
                self._creds = login(email, password)
        elif _load_creds():
            self._creds = _load_creds()
        else:
            raise ValueError("Provide email+password or a creds dict.")

    def _ensure_token(self):
        if _token_expired(self._creds["token"]):
            self._creds["token"] = _fetch_token(
                self._creds["user_id"], self._creds["access_key"]
            )
            _save_creds(self._creds)

    def _headers(self) -> dict:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._creds['token']}"}

    @property
    def user_id(self) -> str:
        return self._creds["user_id"]

    # -----------------------------------------------------------------------
    # Rounds
    # -----------------------------------------------------------------------

    def get_rounds(self, limit: int = 200, offset: int = 0,
                   round_type: str = "flagship") -> list[dict]:
        """Fetch all rounds (paginated)."""
        r = requests.get(
            f"{API_BASE}/users/{self.user_id}/rounds",
            headers=self._headers(),
            params={"offSet": offset, "limit": limit, "roundType": round_type},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("rounds", data) if isinstance(data, dict) else data

    def get_round(self, round_id: int | str) -> dict:
        """Fetch a single round by ID."""
        r = requests.get(
            f"{API_BASE}/users/{self.user_id}/rounds/{round_id}",
            headers=self._headers(), timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def get_round_holes(self, round_id: int | str) -> list[dict]:
        """Fetch hole-by-hole data for a round."""
        r = requests.get(
            f"{API_BASE}/users/{self.user_id}/rounds/{round_id}/holes",
            headers=self._headers(), timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # -----------------------------------------------------------------------
    # Handicap
    # -----------------------------------------------------------------------

    def get_handicap(self) -> dict:
        """Latest handicap index."""
        r = requests.get(
            f"{API_BASE}/users/{self.user_id}/handicaps/latest",
            headers=self._headers(), timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def get_handicap_history(self, rounds: int = 20) -> list[dict]:
        """Handicap history over last N rounds."""
        r = requests.get(
            f"{API_BASE}/users/{self.user_id}/handicaps",
            headers=self._headers(),
            params={"rounds": rounds},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # -----------------------------------------------------------------------
    # Clubs & Distances
    # -----------------------------------------------------------------------

    def get_club_distances(self, num_shots: int = None,
                           start_date: str = None, end_date: str = None) -> list[dict]:
        """Smart club distances. Dates as 'YYYY-MM-DD'."""
        params = {}
        if num_shots:   params["numberOfShots"] = num_shots
        if start_date:  params["startDate"] = start_date
        if end_date:    params["endDate"] = end_date
        r = requests.get(
            f"{API_BASE}/v4/clubs/user/{self.user_id}/smart-distances",
            headers=self._headers(), params=params, timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # -----------------------------------------------------------------------
    # Courses
    # -----------------------------------------------------------------------

    def get_courses_played(self) -> list[dict]:
        """All courses the user has played."""
        r = requests.get(
            f"{API_BASE}/users/{self.user_id}/coursesPlayed",
            headers=self._headers(), timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def get_course(self, course_id: int, version: int = 1) -> dict:
        """Course metadata by ID."""
        r = requests.get(
            f"{API_BASE}/courses/{course_id}",
            headers=self._headers(),
            params={"courseVersion": version},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # -----------------------------------------------------------------------
    # Strokes Gained / Stats
    # -----------------------------------------------------------------------

    def get_strokes_gained(self, round_ids: list[int | str]) -> dict:
        """Strokes gained analysis for one or more rounds."""
        ids = ",".join(str(r) for r in round_ids)
        r = requests.get(
            f"{API_BASE}/v2/sga/shots/{ids}",
            headers=self._headers(),
            params={"roundId": ids},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def get_personal_bests(self) -> dict:
        """All-time personal bests."""
        r = requests.get(
            f"{API_BASE}/users/{self.user_id}/personalBests",
            headers=self._headers(),
            params={"tags": "allTimeBest"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # -----------------------------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------------------------

    def pace_of_play(self) -> dict:
        """
        Compute pace of play (round duration) per course from all rounds.
        Returns:
          {rounds: [...], course_averages: [...], overall_avg_minutes: int}
        """
        rounds = self.get_rounds()

        # Build course name map
        course_ids = set(rd["courseId"] for rd in rounds)
        course_map = {}
        for cid in course_ids:
            try:
                cd = self.get_course(cid)
                course_map[cid] = cd.get("courseName") or cd.get("name") or f"Course {cid}"
            except Exception:
                course_map[cid] = f"Course {cid}"

        processed = []
        for rd in rounds:
            try:
                start = datetime.fromisoformat(rd["startTime"].replace("Z", "+00:00"))
                end   = datetime.fromisoformat(rd["endTime"].replace("Z", "+00:00"))
                mins  = int((end - start).total_seconds() / 60)
                if not (60 <= mins <= 480):
                    continue
                h, m = divmod(mins, 60)
                processed.append({
                    "date":             start.strftime("%Y-%m-%d"),
                    "course":           course_map.get(rd["courseId"], f"Course {rd['courseId']}"),
                    "score":            rd.get("noOfShots"),
                    "duration_minutes": mins,
                    "duration_display": f"{h}h {m:02d}m",
                    "round_id":         rd["roundId"],
                })
            except Exception:
                continue

        totals = defaultdict(lambda: {"total": 0, "count": 0})
        for rnd in processed:
            totals[rnd["course"]]["total"] += rnd["duration_minutes"]
            totals[rnd["course"]]["count"] += 1

        averages = sorted(
            [
                {
                    "course":       course,
                    "avg_minutes":  (avg_min := v["total"] // v["count"]),
                    "avg_display":  f"{avg_min // 60}h {avg_min % 60:02d}m",
                    "rounds":       v["count"],
                }
                for course, v in totals.items()
            ],
            key=lambda x: x["avg_minutes"],
            reverse=True,
        )

        total_mins = sum(r["duration_minutes"] for r in processed)
        overall    = total_mins // len(processed) if processed else 0

        return {
            "rounds":            sorted(processed, key=lambda x: x["date"], reverse=True),
            "course_averages":   averages,
            "overall_avg_minutes": overall,
            "overall_avg_display": f"{overall // 60}h {overall % 60:02d}m",
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, os

    email    = os.environ.get("ARCCOS_EMAIL")
    password = os.environ.get("ARCCOS_PASSWORD")

    if not email or not password:
        print("Set ARCCOS_EMAIL and ARCCOS_PASSWORD environment variables.")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "pace"
    client = ArccosClient(email=email, password=password)

    if cmd == "pace":
        data = client.pace_of_play()
        print(f"Pace of play across {len(data['rounds'])} rounds ({len(data['course_averages'])} courses)")
        print(f"Overall avg: {data['overall_avg_display']}\n")
        print("Slowest courses:")
        for c in data["course_averages"][:10]:
            print(f"  {c['avg_display']}  {c['course']}  ({c['rounds']}x)")
    elif cmd == "rounds":
        for r in client.get_rounds()[:5]:
            print(r)
    elif cmd == "handicap":
        print(client.get_handicap())
    elif cmd == "clubs":
        for c in client.get_club_distances():
            print(c)
    else:
        print(f"Unknown command: {cmd}. Try: pace, rounds, handicap, clubs")
