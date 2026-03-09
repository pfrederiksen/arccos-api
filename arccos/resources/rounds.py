"""
Rounds resource — access Arccos round data.

Endpoint prefix: /users/{userId}/rounds
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .._http import HttpClient


class RoundsResource:
    """
    Access and analyse round data.

    Available via ``client.rounds``.

    Example::

        rounds = client.rounds.list()
        print(f"{len(rounds)} rounds tracked")

        latest = client.rounds.get(rounds[0]["roundId"])
    """

    def __init__(self, http: HttpClient, user_id: str):
        self._http = http
        self._user_id = user_id

    # ------------------------------------------------------------------
    # Core endpoints
    # ------------------------------------------------------------------

    def list(
        self,
        limit: int = 200,
        offset: int = 0,
        round_type: str = "flagship",
        before_date: Optional[str] = None,
        after_date: Optional[str] = None,
        course_id: Optional[int] = None,
    ) -> list[dict]:
        """
        Fetch all rounds for the user.

        Args:
            limit: Maximum number of rounds to return (default 200).
            offset: Pagination offset (default 0).
            round_type: ``"flagship"`` for GPS rounds (default). Also ``"range"``.
            before_date: ISO date string ``"YYYY-MM-DD"`` — return rounds before this date.
            after_date: ISO date string ``"YYYY-MM-DD"`` — return rounds after this date.
            course_id: Filter to rounds at a specific course.

        Returns:
            List of round dicts. Each round includes ``roundId``, ``courseId``,
            ``startTime``, ``endTime``, ``noOfShots``, ``noOfHoles``, etc.
        """
        params: dict = {"offSet": offset, "limit": limit, "roundType": round_type}
        if before_date:
            params["beforeDate"] = before_date
        if after_date:
            params["afterDate"] = after_date
        if course_id:
            params["courseId"] = course_id

        data = self._http.get(f"/users/{self._user_id}/rounds", params=params)
        return data.get("rounds", data) if isinstance(data, dict) else data

    def get(self, round_id: int | str) -> dict:
        """
        Fetch a single round by ID.

        Args:
            round_id: The Arccos round ID (integer or string).

        Returns:
            Round dict with full metadata.

        Raises:
            ArccosNotFoundError: If the round does not exist.
        """
        return self._http.get(f"/users/{self._user_id}/rounds/{round_id}")

    def holes(self, round_id: int | str) -> list[dict]:
        """
        Fetch hole-by-hole data for a round.

        Args:
            round_id: The Arccos round ID.

        Returns:
            List of hole dicts (score, putts, fairway, GIR, etc.).
        """
        return self._http.get(f"/users/{self._user_id}/rounds/{round_id}/holes")

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def pace_of_play(self, rounds: list[dict] = None) -> dict:
        """
        Compute pace of play (round duration) per course.

        Fetches all rounds if *rounds* is not provided.

        Args:
            rounds: Optional pre-fetched list of round dicts.

        Returns:
            Dict with keys:

            - ``rounds`` — list of processed round dicts (date, course, duration)
            - ``course_averages`` — list sorted slowest-first
            - ``overall_avg_minutes`` — int
            - ``overall_avg_display`` — e.g. ``"4h 22m"``
        """
        from collections import defaultdict

        if rounds is None:
            rounds = self.list()

        # We need course names; import here to avoid circular dependency
        from .courses import CoursesResource
        courses_res = CoursesResource(self._http)

        course_ids = {r["courseId"] for r in rounds}
        course_map: dict[int, str] = {}
        for cid in course_ids:
            try:
                cd = courses_res.get(cid)
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

        totals: dict = defaultdict(lambda: {"total": 0, "count": 0})
        for rnd in processed:
            totals[rnd["course"]]["total"] += rnd["duration_minutes"]
            totals[rnd["course"]]["count"] += 1

        averages = sorted(
            [
                {
                    "course":      course,
                    "avg_minutes": (avg := v["total"] // v["count"]),
                    "avg_display": f"{avg // 60}h {avg % 60:02d}m",
                    "rounds":      v["count"],
                }
                for course, v in totals.items()
            ],
            key=lambda x: x["avg_minutes"],
            reverse=True,
        )

        total_mins = sum(r["duration_minutes"] for r in processed)
        overall    = total_mins // len(processed) if processed else 0

        return {
            "rounds":               sorted(processed, key=lambda x: x["date"], reverse=True),
            "course_averages":      averages,
            "overall_avg_minutes":  overall,
            "overall_avg_display":  f"{overall // 60}h {overall % 60:02d}m",
        }
