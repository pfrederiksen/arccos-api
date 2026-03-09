"""
Stats resource — strokes gained (SGA) and performance analytics.

Endpoint prefix: /v2/sga, /users/{userId}/personalBests
"""

from __future__ import annotations

from typing import Optional

from .._http import HttpClient


class StatsResource:
    """
    Access strokes gained analysis and performance stats.

    Available via ``client.stats``.

    Strokes Gained Analysis (SGA) measures each shot against the expected number
    of strokes an average tour player would need from the same position. Positive
    values mean better than average; negative values mean worse.

    Categories:

    - **Overall** — total strokes gained vs. scratch
    - **Driving** — tee shots (accuracy + distance)
    - **Approach** — approach shots to the green
    - **Short Game** — chipping and pitching
    - **Putting** — on-green performance

    Example::

        latest_round = client.rounds.list(limit=1)[0]
        sg = client.stats.strokes_gained([latest_round["roundId"]])
        print(f"Overall SG: {sg.get('overallSga')}")

        bests = client.stats.personal_bests()
    """

    def __init__(self, http: HttpClient, user_id: str):
        self._http = http
        self._user_id = user_id

    def strokes_gained(self, round_ids: list[int | str]) -> dict:
        """
        Fetch strokes gained (SGA) analysis for one or more rounds.

        When multiple round IDs are passed, the response contains aggregate
        strokes gained across all specified rounds.

        Args:
            round_ids: List of Arccos round IDs to analyse.

        Returns:
            Dict with strokes gained values, e.g.::

                {
                    "overallSga": -2.1,
                    "drivingSga": 0.4,
                    "approachSga": -1.8,
                    "shortSga": -0.3,
                    "puttingSga": -0.4,
                    ...
                }
        """
        ids_str = ",".join(str(r) for r in round_ids)
        return self._http.get(
            f"/v2/sga/shots/{ids_str}",
            params={"roundId": ids_str},
        )

    def strokes_to_get_down(self) -> dict:
        """
        Fetch the user's "strokes to get down" stats (up-and-down proficiency).

        Returns:
            Dict with proximity-to-hole and short game conversion data.
        """
        return self._http.get("/v2/sga/strokes-to-get-down")

    def personal_bests(self) -> dict:
        """
        Fetch all-time personal bests.

        Returns:
            Dict with personal best records (low round, longest drive, etc.).
        """
        return self._http.get(
            f"/users/{self._user_id}/personalBests",
            params={"tags": "allTimeBest"},
        )

    def overall_stats(self) -> dict:
        """
        Fetch aggregated overall performance stats.

        Returns:
            Dict with GIR percentage, fairway percentage, putts per round,
            scoring average, and other aggregate stats.
        """
        return self._http.get(f"/users/{self._user_id}/stats/overall")

    def sga_filter_settings(self) -> dict:
        """
        Fetch the user's SGA filter settings (date range, course type, etc.).

        Returns:
            Current filter configuration dict.
        """
        return self._http.get(
            f"/sga/filterSettings",
            params={"userId": self._user_id},
        )
