"""
Tests for arccos._http — the internal HTTP client.
"""

from unittest.mock import MagicMock, patch

import pytest

from arccos._http import HttpClient, API_BASE
from arccos.exceptions import ArccosNotFoundError

from conftest import make_creds


class TestHttpClient:
    def _make_client(self, creds=None) -> tuple[HttpClient, MagicMock]:
        auth = MagicMock()
        auth.ensure_fresh.side_effect = lambda c: c
        auth.auth_header.return_value = "Bearer fake-token"
        creds = creds or make_creds()
        client = HttpClient(auth=auth, creds=creds)
        return client, auth

    def test_get_sends_request(self):
        client, auth = self._make_client()
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"data": "value"}'
        resp.json.return_value = {"data": "value"}
        client._session = MagicMock()
        client._session.request.return_value = resp

        result = client.get("/test/path", params={"key": "val"})

        client._session.request.assert_called_once()
        call_args = client._session.request.call_args
        assert call_args[0] == ("GET", f"{API_BASE}/test/path")
        assert call_args[1]["params"] == {"key": "val"}
        assert result == {"data": "value"}

    def test_post_sends_json_body(self):
        client, auth = self._make_client()
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"created": true}'
        resp.json.return_value = {"created": True}
        client._session = MagicMock()
        client._session.request.return_value = resp

        result = client.post("/test/path", body={"field": "value"})

        call_args = client._session.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[1]["json"] == {"field": "value"}
        assert result == {"created": True}

    def test_put_sends_json_body(self):
        client, auth = self._make_client()
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"updated": true}'
        resp.json.return_value = {"updated": True}
        client._session = MagicMock()
        client._session.request.return_value = resp

        client.put("/test/path", body={"field": "new_value"})
        call_args = client._session.request.call_args
        assert call_args[0][0] == "PUT"

    def test_delete_sends_request(self):
        client, auth = self._make_client()
        resp = MagicMock()
        resp.ok = True
        resp.content = b""
        client._session = MagicMock()
        client._session.request.return_value = resp

        result = client.delete("/test/path")
        call_args = client._session.request.call_args
        assert call_args[0][0] == "DELETE"
        assert result == {}

    def test_empty_response_returns_empty_dict(self):
        client, auth = self._make_client()
        resp = MagicMock()
        resp.ok = True
        resp.content = b""
        client._session = MagicMock()
        client._session.request.return_value = resp

        result = client.get("/test/path")
        assert result == {}

    def test_ensure_fresh_called_on_every_request(self):
        client, auth = self._make_client()
        resp = MagicMock()
        resp.ok = True
        resp.content = b"{}"
        resp.json.return_value = {}
        client._session = MagicMock()
        client._session.request.return_value = resp

        client.get("/a")
        client.get("/b")
        assert auth.ensure_fresh.call_count == 2

    def test_auth_header_set_on_request(self):
        client, auth = self._make_client()
        auth.auth_header.return_value = "Bearer my-special-token"
        resp = MagicMock()
        resp.ok = True
        resp.content = b"{}"
        resp.json.return_value = {}
        client._session = MagicMock()
        client._session.request.return_value = resp

        client.get("/test")
        call_args = client._session.request.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer my-special-token"

    def test_raises_on_error_response(self):
        client, auth = self._make_client()
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 404
        resp.text = "Not found"
        resp.json.return_value = {"error": {"code": 404, "description": "Not found"}}
        client._session = MagicMock()
        client._session.request.return_value = resp

        with pytest.raises(ArccosNotFoundError):
            client.get("/nonexistent")
