"""
Tests for arccos.auth — authentication flow.

Run: pytest tests/
"""

import json
import base64
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arccos.auth import ArccosAuth, Credentials
from arccos.exceptions import ArccosAuthError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(exp_offset: int = 3600) -> str:
    """Return a minimal JWT with the given expiry offset from now."""
    header  = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"userId": "test-user", "exp": int(time.time()) + exp_offset}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


def _make_creds(exp_offset: int = 3600) -> Credentials:
    return Credentials(
        email="test@example.com",
        user_id="test-user-id",
        access_key="TESTACCESSKEY",
        token=_make_jwt(exp_offset),
        secret="testsecret",
    )


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

class TestCredentials:
    def test_token_not_expired(self):
        creds = _make_creds(exp_offset=3600)
        assert not creds.token_expired()

    def test_token_expired(self):
        creds = _make_creds(exp_offset=-10)
        assert creds.token_expired()

    def test_token_expiring_soon(self):
        creds = _make_creds(exp_offset=30)  # expires in 30s, grace=60
        assert creds.token_expired(grace_seconds=60)

    def test_save_and_load(self, tmp_path):
        creds = _make_creds()
        path  = tmp_path / "creds.json"
        creds.save(path)
        loaded = Credentials.load(path)
        assert loaded.email      == creds.email
        assert loaded.user_id    == creds.user_id
        assert loaded.access_key == creds.access_key
        assert loaded.token      == creds.token

    def test_load_missing_file(self, tmp_path):
        assert Credentials.load(tmp_path / "nonexistent.json") is None

    def test_to_dict_roundtrip(self):
        creds = _make_creds()
        assert Credentials.from_dict(creds.to_dict()).token == creds.token


# ---------------------------------------------------------------------------
# ArccosAuth.login
# ---------------------------------------------------------------------------

class TestArccosAuthLogin:
    def _auth(self, tmp_path) -> ArccosAuth:
        return ArccosAuth(creds_path=tmp_path / "creds.json")

    @patch("arccos.auth.requests.Session")
    def test_login_success(self, mock_session_cls, tmp_path):
        session = MagicMock()
        mock_session_cls.return_value = session
        jwt = _make_jwt(3600)

        # Step 1: /accessKeys
        r1 = MagicMock()
        r1.status_code = 200
        r1.ok = True
        r1.json.return_value = {
            "userId": "uid-123", "accessKey": "ACCESSKEY", "secret": "SECRET"
        }

        # Step 2: /tokens
        r2 = MagicMock()
        r2.status_code = 200
        r2.ok = True
        r2.json.return_value = {"userId": "uid-123", "token": jwt}

        session.post.side_effect = [r1, r2]

        auth  = self._auth(tmp_path)
        creds = auth.login("test@example.com", "password")

        assert creds.user_id    == "uid-123"
        assert creds.access_key == "ACCESSKEY"
        assert creds.token      == jwt
        assert session.post.call_count == 2

    @patch("arccos.auth.requests.Session")
    def test_login_bad_password(self, mock_session_cls, tmp_path):
        session = MagicMock()
        mock_session_cls.return_value = session

        r1 = MagicMock()
        r1.status_code = 401
        r1.ok = False
        session.post.return_value = r1

        auth = self._auth(tmp_path)
        with pytest.raises(ArccosAuthError):
            auth.login("bad@example.com", "wrongpass")

    @patch("arccos.auth.requests.Session")
    def test_refresh_success(self, mock_session_cls, tmp_path):
        session = MagicMock()
        mock_session_cls.return_value = session
        new_jwt = _make_jwt(3600)

        r = MagicMock()
        r.status_code = 200
        r.ok = True
        r.json.return_value = {"userId": "uid-123", "token": new_jwt}
        session.post.return_value = r

        auth  = self._auth(tmp_path)
        creds = _make_creds(exp_offset=-10)  # expired
        refreshed = auth.refresh(creds)

        assert refreshed.token == new_jwt

    @patch("arccos.auth.requests.Session")
    def test_ensure_fresh_noop_when_valid(self, mock_session_cls, tmp_path):
        session = MagicMock()
        mock_session_cls.return_value = session

        auth  = self._auth(tmp_path)
        creds = _make_creds(exp_offset=3600)  # valid
        result = auth.ensure_fresh(creds)

        # Should NOT call the API
        session.post.assert_not_called()
        assert result.token == creds.token
