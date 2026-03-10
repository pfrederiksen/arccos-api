"""
Clubs resource — access Arccos smart club distance data.

Endpoint prefix: /v4/clubs/user/{userId}

Club ID note:
    The ``clubId`` returned by the smart-distances endpoint is a bag-specific
    sequential ID, NOT a club-type code. To map clubId → club name/make/model,
    cross-reference with :meth:`ClubsResource.bag`. The bag endpoint returns
    ``clubType`` (an Arccos club-type code) which maps to a club name, plus
    ``clubMakeOther`` and ``clubModelOther`` for equipment details.

Actual smart-distances response shape (per club):
    {
        "clubId": 1,
        "smartDistance": {"distance": 243.9, "unit": "yd"},
        "normalizedSmartDistance": {"distance": 243.9, "unit": "yd"},
        "terrain": {
            "tee":     {"distance": 257.8, "unit": "yd", "diff": 0.0},
            "fairway": {"distance": 189.7, "unit": "yd", "diff": 0.0} | null,
            "rough":   {"distance": 188.7, "unit": "yd", "diff": 0.0} | null,
            "sand":    {"distance": ...,   "unit": "yd", "diff": 0.0} | null,
        },
        "usage":   {"count": 517},
        "gir":     null,
        "longest": {"distance": 285.4, "unit": "yd"},
        "range":   {"low": 241.1, "high": 259.1, "unit": "yd"},
    }

GPS distance (raw avg) vs smart distance:
    - ``smartDistance.distance`` — Arccos-filtered carry distance (outliers removed)
    - ``terrain.tee.distance``   — avg GPS distance when hit from tee (driver/woods)
    - ``terrain.fairway.distance`` — avg GPS distance from fairway (irons/wedges)
    - ``terrain.rough.distance``   — avg GPS distance from rough
    To get a GPS average for each club: use tee distance for driver/woods,
    and the mean of fairway + rough for irons/wedges.
"""

from __future__ import annotations

from .._http import HttpClient

# Standard Arccos clubType codes → short display names.
# These appear in bag configuration (clubs[].clubType), not smart-distances.
CLUB_TYPE_NAMES: dict[int, str] = {
    1:  "Driver",
    2:  "3 Wood",
    3:  "5 Wood",
    4:  "7 Wood",
    5:  "4 Iron",
    6:  "5 Iron",
    7:  "6 Iron",
    8:  "7 Iron",
    9:  "8 Iron",
    10: "9 Iron",
    11: "PW",
    12: "Putter",
    13: "SW",
    14: "LW",
    15: "Putter",
    17: "3 Hybrid",
    18: "4 Hybrid",
    19: "5 Hybrid",
    20: "6 Hybrid",
    21: "7 Hybrid",
    43: "AW",
    44: "2 Iron",
    45: "2 Hybrid",
    46: "Di",
    47: "GW",
    48: "52°",
    49: "54°",
    50: "56°",
    51: "58°",
    52: "60°",
    53: "56°",
    54: "3 Iron",
}


class ClubsResource:
    """
    Access smart club distance recommendations.

    Available via ``client.clubs``.

    Example::

        distances = client.clubs.smart_distances()
        for club in distances:
            sd = club["smartDistance"]["distance"]
            shots = club["usage"]["count"]
            print(f"clubId {club['clubId']}: {sd}y ({shots} shots)")

        # Map clubId → name by cross-referencing the bag:
        bag = client.clubs.bag(client.user_id)  # get bagId from client.profile()
        club_names = {
            c["clubId"]: c["clubType"]
            for c in bag["clubs"]
            if c.get("isDeleted") != "T"
        }
    """

    def __init__(self, http: HttpClient, user_id: str):
        self._http = http
        self._user_id = user_id

    def smart_distances(
        self,
        num_shots: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """
        Fetch smart club distance data for all clubs in the current bag.

        Smart distances are computed from actual shot data, filtered to shots
        that represent the golfer's "real" carry distance (outliers removed).

        Each item in the returned list contains:

        - ``clubId`` — bag-specific club ID (cross-ref with :meth:`bag` to get name)
        - ``smartDistance`` — ``{"distance": float, "unit": "yd"}`` (Arccos filtered avg)
        - ``normalizedSmartDistance`` — same, normalized
        - ``terrain`` — per-terrain breakdowns: ``tee``, ``fairway``, ``rough``, ``sand``
          (each ``{"distance": float, "unit": "yd", "diff": float}`` or ``null``)
        - ``usage`` — ``{"count": int}`` total shots used
        - ``longest`` — ``{"distance": float, "unit": "yd"}``
        - ``range`` — ``{"low": float, "high": float, "unit": "yd"}``
        - ``gir`` — green in regulation data (may be null)

        To get GPS (raw) distance:
            - Driver/woods: use ``terrain["tee"]["distance"]``
            - Irons/wedges: average of ``terrain["fairway"]["distance"]``
              and ``terrain["rough"]["distance"]``

        Args:
            num_shots: Minimum number of shots required for inclusion.
            start_date: Filter to shots after this date (``"YYYY-MM-DD"``).
            end_date: Filter to shots before this date (``"YYYY-MM-DD"``).

        Returns:
            List of club distance dicts as described above.
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

    def bag(self, bag_id: str | int) -> dict:
        """
        Fetch the user's bag configuration.

        Returns a dict with a ``clubs`` list. Each club includes:

        - ``clubId`` — bag-specific ID (matches ``smart_distances()`` clubId)
        - ``clubType`` — Arccos club-type code (see :data:`CLUB_TYPE_NAMES`)
        - ``clubMakeOther`` — club make (e.g. ``"PING"``)
        - ``clubModelOther`` — club model (e.g. ``"G425 SFT"``)
        - ``isDeleted`` — ``"T"`` if removed from bag, ``"F"`` if active
        - ``startDate`` / ``endDate`` — when added/removed from bag

        Args:
            bag_id: The Arccos bag ID (get from ``client.profile()["bagId"]``).

        Returns:
            Bag configuration dict.
        """
        return self._http.get(f"/users/{self._user_id}/bags/{bag_id}")

    def club_shots(
        self,
        bag_id: str | int,
        club_id: str | int,
        limit: int = 100,
        offset: int = 0,
        round_id: str | None = None,
    ) -> list[dict]:
        """
        Fetch individual shot records for a specific club.

        Args:
            bag_id: The Arccos bag ID.
            club_id: The bag-specific club ID (from :meth:`smart_distances`).
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
