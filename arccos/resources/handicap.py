"""
Handicap resource — access Arccos handicap index data.

Endpoint prefix: /users/{userId}/handicaps
"""

from __future__ import annotations

from .._http import HttpClient


class HandicapResource:
    """
    Access handicap index and history.

    Available via ``client.handicap``.

    Example::

        current = client.handicap.current()
        print(f"Handicap Index: {current}")

        history = client.handicap.history(rounds=20)
    """

    def __init__(self, http: HttpClient, user_id: str):
        self._http = http
        self._user_id = user_id

    def current(self) -> dict:
        """
        Fetch the current (latest) handicap index.

        Returns:
            Dict with handicap data. Typically includes the current index value
            and related metadata.

        Example response::

            {
                "handicapIndex": 18.2,
                "lowHandicapIndex": 17.3,
                ...
            }
        """
        return self._http.get(f"/users/{self._user_id}/handicaps/latest")

    def history(self, rounds: int = 20) -> list[dict]:
        """
        Fetch handicap history over the last N rounds.

        Args:
            rounds: Number of rounds to include in the history (default 20).

        Returns:
            List of handicap history entries, each with a date and index value.
        """
        data = self._http.get(
            f"/users/{self._user_id}/handicaps",
            params={"rounds": rounds},
        )
        return data if isinstance(data, list) else data.get("handicaps", data)
