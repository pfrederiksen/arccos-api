"""
Shared test fixtures for the arccos test suite.
"""

import base64
import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from arccos.auth import ArccosAuth, Credentials


def make_jwt(exp_offset: int = 3600, user_id: str = "test-user") -> str:
    """Return a minimal JWT with the given expiry offset from now."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"userId": user_id, "exp": int(time.time()) + exp_offset}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


def make_creds(exp_offset: int = 3600, **overrides) -> Credentials:
    """Create test credentials with a JWT expiring in *exp_offset* seconds."""
    defaults = dict(
        email="test@example.com",
        user_id="test-user-id",
        access_key="TESTACCESSKEY",
        token=make_jwt(exp_offset),
        secret="testsecret",
    )
    defaults.update(overrides)
    return Credentials(**defaults)


@pytest.fixture
def creds():
    """Valid (non-expired) test credentials."""
    return make_creds(exp_offset=3600)


@pytest.fixture
def expired_creds():
    """Expired test credentials."""
    return make_creds(exp_offset=-10)


@pytest.fixture
def mock_http():
    """A MagicMock standing in for HttpClient."""
    return MagicMock()


@pytest.fixture
def tmp_creds_path(tmp_path):
    """A temporary path for credential storage."""
    return tmp_path / "creds.json"
