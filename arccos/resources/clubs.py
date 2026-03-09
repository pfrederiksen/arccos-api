"""
Clubs resource — access Arccos smart club distance data.

Endpoint prefix: /v4/clubs/user/{userId}
"""

from __future__ import annotations

from typing import Optional

from .._http import HttpClient


class ClubsResource:
    """
    Access smart club distance recommendations.

    Available via ``client.clubs``.

    Example::

        distances = client.clubs.smart_distances()
        for club in distances:
            print(f"{club['clubType']}: {club['averageDistance']}y")
    """

    def __init__(self, http: HttpClient, user_id: str):
        self._http = http
        self._user_id = user_id

    def smart_distances(
        self,
        num_shots: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch smart club distance recommendations.

        Smart distances are computed from actual shot data, filtered to shots
        that represent the golfer's "real" carry distance (outliers removed).

        Args:
            num_shots: Minimum number of shots required for a distance to be
                       included. Defaults to Arccos's own threshold.
            start_date: Filter to shots after this date (``"YYYY-MM-DD"``).
            end_date: Filter to shots before this date (``"YYYY-MM-DD"``).

        Returns:
            List of club dicts. Each typically includes:

            - ``clubType`` — club name (e.g. ``"Driver"``, ``"7 Iron"``)
            - ``averageDistance`` — average carry distance in yards
            - ``smartDistance`` — recommended club distance in yards
            - ``totalShots`` — number of shots used in the calculation
        """
        params: dict = {}
        if num_shots:
            params["numberOfShots"] = num_shots
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        data = self._http.get(
            f"/v4/clubs/user/{self._user_id}/smart-distances",
            params=params,
        )
        return data if isinstance(data, list) else data.get("clubs", data)

    def bag(self, bag_id: str) -> dict:
        """
        Fetch the user's bag configuration.

        Args:
            bag_id: The Arccos bag ID.

        Returns:
            Bag configuration dict including all clubs and their IDs.
        """
        return self._http.get(f"/users/{self._user_id}/bags/{bag_id}")

    def club_shots(
        self,
        bag_id: str,
        club_id: str,
        limit: int = 100,
        offset: int = 0,
        round_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch individual shot records for a specific club.

        Args:
            bag_id: The Arccos bag ID.
            club_id: The Arccos club ID.
            limit: Maximum number of shots to return (default 100).
            offset: Pagination offset (default 0).
            round_id: Optional — filter to shots from a specific round.

        Returns:
            List of shot dicts with distance, location, and outcome data.
        """
        params: dict = {"limit": limit, "offSet": offset}
        if round_id:
            params["roundId"] = round_id

        return self._http.get(
            f"/users/{self._user_id}/bags/{bag_id}/clubs/{club_id}/shots",
            params=params,
        )
