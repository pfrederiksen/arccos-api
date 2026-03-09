"""
Authentication for the Arccos Golf API.

Arccos uses a two-step auth flow:

  Step 1 — Exchange email + password for an accessKey:
    POST https://authentication.arccosgolf.com/accessKeys
    Body: {"email": "...", "password": "...", "signedInByFacebook": "F"}
    Response: {"userId": "...", "accessKey": "...", "secret": "..."}

  Step 2 — Exchange accessKey for a short-lived JWT:
    POST https://authentication.arccosgolf.com/tokens
    Body: {"userId": "...", "accessKey": "..."}
    Response: {"userId": "...", "token": "<jwt>"}

The JWT expires in ~3 hours. The accessKey is valid for ~180 days.
Use the accessKey to silently refresh the JWT without re-entering credentials.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from .exceptions import ArccosAuthError, raise_for_status

logger = logging.getLogger(__name__)

AUTH_BASE = "https://authentication.arccosgolf.com"

DEFAULT_CREDS_PATH = Path.home() / ".arccos_creds.json"


@dataclass
class Credentials:
    """Holds the full credential set for an Arccos account."""

    email: str
    user_id: str
    access_key: str
    token: str
    secret: str = ""

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "email":      self.email,
            "user_id":    self.user_id,
            "access_key": self.access_key,
            "token":      self.token,
            "secret":     self.secret,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Credentials:
        return cls(
            email=      data["email"],
            user_id=    data["user_id"],
            access_key= data["access_key"],
            token=      data["token"],
            secret=     data.get("secret", ""),
        )

    def save(self, path: Path = DEFAULT_CREDS_PATH) -> None:
        """Persist credentials to a JSON file (mode 0600)."""
        path.write_text(json.dumps(self.to_dict(), indent=2))
        path.chmod(0o600)
        logger.debug("Credentials saved to %s", path)

    @classmethod
    def load(cls, path: Path = DEFAULT_CREDS_PATH) -> Credentials | None:
        """Load credentials from disk, or return None if not found."""
        if not path.exists():
            return None
        try:
            return cls.from_dict(json.loads(path.read_text()))
        except (KeyError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load credentials from %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Token inspection
    # ------------------------------------------------------------------

    def token_expired(self, grace_seconds: int = 60) -> bool:
        """Return True if the JWT is expired (or will expire within *grace_seconds*)."""
        try:
            payload = self.token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            exp = json.loads(base64.b64decode(payload))["exp"]
            now = datetime.now(UTC).timestamp()
            return now > exp - grace_seconds
        except Exception:
            return True


class ArccosAuth:
    """
    Manages Arccos authentication, including initial login and token refresh.

    Usage::

        auth = ArccosAuth()
        creds = auth.login("you@example.com", "password")

        # Later — refresh silently:
        auth.ensure_fresh(creds)

        # Get an Authorization header value:
        header = auth.auth_header(creds)  # "Bearer eyJ..."
    """

    def __init__(
        self,
        creds_path: Path = DEFAULT_CREDS_PATH,
        session: requests.Session | None = None,
    ):
        self._creds_path = creds_path
        self._session = session or requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> Credentials:
        """
        Authenticate with email and password.

        Performs the two-step auth flow and caches credentials to disk.

        Args:
            email: Arccos account email address.
            password: Arccos account password.

        Returns:
            A :class:`Credentials` object with a valid JWT.

        Raises:
            ArccosAuthError: If email or password is incorrect.
        """
        logger.debug("Logging in as %s", email)

        # Step 1: email + password → accessKey
        resp = self._session.post(
            f"{AUTH_BASE}/accessKeys",
            json={"email": email, "password": password, "signedInByFacebook": "F"},
            timeout=15,
        )
        if resp.status_code == 401:
            raise ArccosAuthError(
                "Invalid email or password.",
                status_code=resp.status_code,
            )
        raise_for_status(resp)
        data = resp.json()

        access_key = data["accessKey"]
        user_id    = data["userId"]
        secret     = data.get("secret", "")

        # Step 2: accessKey → JWT
        token = self._fetch_token(user_id, access_key)

        creds = Credentials(
            email=email,
            user_id=user_id,
            access_key=access_key,
            token=token,
            secret=secret,
        )
        creds.save(self._creds_path)
        logger.info("Logged in successfully as %s (userId=%s)", email, user_id)
        return creds

    def refresh(self, creds: Credentials) -> Credentials:
        """
        Silently refresh the JWT using the stored accessKey.

        Does NOT require the user's password. The accessKey is valid for
        approximately 180 days.

        Args:
            creds: Existing :class:`Credentials` (accessKey must be valid).

        Returns:
            Updated :class:`Credentials` with a fresh JWT.

        Raises:
            ArccosAuthError: If the accessKey has expired.
        """
        logger.debug("Refreshing token for userId=%s", creds.user_id)
        creds.token = self._fetch_token(creds.user_id, creds.access_key)
        creds.save(self._creds_path)
        return creds

    def ensure_fresh(self, creds: Credentials) -> Credentials:
        """
        Refresh the JWT only if it is expired (or about to expire).

        This is a no-op if the token is still valid.

        Args:
            creds: Existing :class:`Credentials`.

        Returns:
            Possibly-updated :class:`Credentials`.
        """
        if creds.token_expired():
            return self.refresh(creds)
        return creds

    def load_or_login(self, email: str, password: str) -> Credentials:
        """
        Load cached credentials if they exist, otherwise log in.

        The cached accessKey is used to silently refresh the JWT if needed,
        so the password is only used once (the first time).

        Args:
            email: Arccos account email address.
            password: Arccos account password.

        Returns:
            Valid :class:`Credentials`.
        """
        creds = Credentials.load(self._creds_path)
        if creds and creds.email == email:
            return self.ensure_fresh(creds)
        return self.login(email, password)

    @staticmethod
    def auth_header(creds: Credentials) -> str:
        """Return the ``Authorization`` header value for API requests."""
        return f"Bearer {creds.token}"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_token(self, user_id: str, access_key: str) -> str:
        """POST /tokens and return the JWT string."""
        resp = self._session.post(
            f"{AUTH_BASE}/tokens",
            json={"userId": user_id, "accessKey": access_key},
            timeout=15,
        )
        if resp.status_code == 401:
            raise ArccosAuthError(
                "accessKey is invalid or expired. Please log in again.",
                status_code=resp.status_code,
            )
        raise_for_status(resp)
        return resp.json()["token"]
