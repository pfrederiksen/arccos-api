"""
Internal HTTP client for the Arccos API.

All API calls share a single requests.Session with automatic token refresh.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from .auth import ArccosAuth, Credentials
from .exceptions import raise_for_status

logger = logging.getLogger(__name__)

API_BASE = "https://api.arccosgolf.com"


class HttpClient:
    """
    Thin wrapper around requests.Session that:

    - Prepends the API base URL
    - Injects the ``Authorization: Bearer`` header on every request
    - Auto-refreshes the JWT when expired
    - Raises typed :mod:`arccos.exceptions` for non-2xx responses
    """

    def __init__(self, auth: ArccosAuth, creds: Credentials):
        self._auth = auth
        self._creds = creds
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept":       "application/json",
        })

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict | None = None) -> Any:
        """
        Perform an authenticated GET request.

        Args:
            path: API path, e.g. ``"/users/{userId}/rounds"``.
            params: Optional query parameters.

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            arccos.exceptions.ArccosError: On API errors.
        """
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict | None = None) -> Any:
        """
        Perform an authenticated POST request.

        Args:
            path: API path.
            body: Request body (JSON-serialisable dict).

        Returns:
            Parsed JSON response.
        """
        return self._request("POST", path, json=body)

    def put(self, path: str, body: dict | None = None) -> Any:
        """Perform an authenticated PUT request."""
        return self._request("PUT", path, json=body)

    def delete(self, path: str) -> Any:
        """Perform an authenticated DELETE request."""
        return self._request("DELETE", path)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> Any:
        self._creds = self._auth.ensure_fresh(self._creds)
        headers = {"Authorization": self._auth.auth_header(self._creds)}

        url = f"{API_BASE}{path}"
        logger.debug("%s %s", method, url)

        resp = self._session.request(
            method, url, headers=headers, timeout=15, verify=True, **kwargs
        )
        raise_for_status(resp)

        if resp.content:
            return resp.json()
        return {}
