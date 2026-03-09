"""
arccos — Unofficial Python client for the Arccos Golf API.

Quick start:
    from arccos import ArccosClient

    client = ArccosClient(email="you@example.com", password="secret")
    rounds = client.rounds.list()
    print(client.handicap.current())
"""

from .auth import ArccosAuth
from .client import ArccosClient
from .exceptions import (
    ArccosAuthError,
    ArccosError,
    ArccosForbiddenError,
    ArccosNotFoundError,
    ArccosRateLimitError,
)

__version__ = "0.1.0"
__all__ = [
    "ArccosClient",
    "ArccosAuth",
    "ArccosError",
    "ArccosAuthError",
    "ArccosForbiddenError",
    "ArccosNotFoundError",
    "ArccosRateLimitError",
]
