"""
ArccosClient — the main entry point for the Arccos API wrapper.

Usage::

    from arccos import ArccosClient

    client = ArccosClient(email="you@example.com", password="your_password")

    # Access resources through namespaced properties:
    rounds   = client.rounds.list()
    handicap = client.handicap.current()
    clubs    = client.clubs.smart_distances()
    pace     = client.rounds.pace_of_play()
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._http import HttpClient
from .auth import DEFAULT_CREDS_PATH, ArccosAuth, Credentials
from .resources.clubs import ClubsResource
from .resources.courses import CoursesResource
from .resources.handicap import HandicapResource
from .resources.rounds import RoundsResource
from .resources.stats import StatsResource

logger = logging.getLogger(__name__)


class ArccosClient:
    """
    Authenticated client for the Arccos Golf API.

    Credentials are cached in ``~/.arccos_creds.json`` after the first login.
    Subsequent instantiations silently refresh the JWT using the stored
    accessKey — no password required until the accessKey itself expires
    (~180 days).

    Args:
        email: Arccos account email address.
        password: Arccos account password.
        creds_path: Override the default credential cache location.
        creds: Pass a :class:`~arccos.auth.Credentials` object directly
               (e.g. for testing or multi-account use).

    Raises:
        ArccosAuthError: If the email or password is incorrect.
        ValueError: If neither credentials nor email+password are provided.

    Example — basic login::

        from arccos import ArccosClient

        client = ArccosClient(email="you@example.com", password="secret")
        print(client.handicap.current())

    Example — use pre-loaded credentials::

        from arccos.auth import Credentials
        from arccos import ArccosClient

        creds = Credentials.load()
        client = ArccosClient(creds=creds)

    Resources:

    - :attr:`rounds` — :class:`~arccos.resources.rounds.RoundsResource`
    - :attr:`handicap` — :class:`~arccos.resources.handicap.HandicapResource`
    - :attr:`clubs` — :class:`~arccos.resources.clubs.ClubsResource`
    - :attr:`courses` — :class:`~arccos.resources.courses.CoursesResource`
    - :attr:`stats` — :class:`~arccos.resources.stats.StatsResource`
    """

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        creds_path: Path = DEFAULT_CREDS_PATH,
        creds: Credentials | None = None,
    ):
        self._auth = ArccosAuth(creds_path=creds_path)

        if creds is not None:
            self._creds = self._auth.ensure_fresh(creds)
        elif email and password:
            self._creds = self._auth.load_or_login(email, password)
        else:
            # Try loading cached credentials
            saved = Credentials.load(creds_path)
            if saved:
                self._creds = self._auth.ensure_fresh(saved)
            else:
                raise ValueError(
                    "Provide email and password, or ensure cached credentials exist "
                    f"at {creds_path}."
                )

        self._http = HttpClient(auth=self._auth, creds=self._creds)
        self._init_resources()

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    def _init_resources(self) -> None:
        uid = self._creds.user_id
        self._rounds   = RoundsResource(self._http, uid)
        self._handicap = HandicapResource(self._http, uid)
        self._clubs    = ClubsResource(self._http, uid)
        self._courses  = CoursesResource(self._http, uid)
        self._stats    = StatsResource(self._http, uid)

    @property
    def rounds(self) -> RoundsResource:
        """Access round data. See :class:`~arccos.resources.rounds.RoundsResource`."""
        return self._rounds

    @property
    def handicap(self) -> HandicapResource:
        """Access handicap index and history."""
        return self._handicap

    @property
    def clubs(self) -> ClubsResource:
        """Access club distance data. See :class:`~arccos.resources.clubs.ClubsResource`."""
        return self._clubs

    @property
    def courses(self) -> CoursesResource:
        """Access course metadata. See :class:`~arccos.resources.courses.CoursesResource`."""
        return self._courses

    @property
    def stats(self) -> StatsResource:
        """Access strokes gained and performance stats."""
        return self._stats

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    @property
    def user_id(self) -> str:
        """The authenticated user's Arccos user ID."""
        return self._creds.user_id

    @property
    def email(self) -> str:
        """The authenticated user's email address."""
        return self._creds.email

    def __repr__(self) -> str:
        return f"ArccosClient(email={self.email!r}, user_id={self.user_id!r})"
