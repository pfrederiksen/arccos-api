"""
Tests for arccos.exceptions — error mapping from HTTP responses.
"""

from unittest.mock import MagicMock

import pytest

from arccos.exceptions import (
    ArccosAuthError,
    ArccosError,
    ArccosForbiddenError,
    ArccosNotFoundError,
    ArccosRateLimitError,
    raise_for_status,
)


def _mock_response(status_code: int, body: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.text = text or f"Error {status_code}"
    if body is not None:
        resp.json.return_value = body
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


class TestRaiseForStatus:
    def test_2xx_no_raise(self):
        resp = _mock_response(200)
        raise_for_status(resp)  # should not raise

    def test_204_no_raise(self):
        resp = _mock_response(204)
        raise_for_status(resp)

    def test_401_raises_auth_error(self):
        resp = _mock_response(401, {"error": {"code": 401, "description": "Unauthorized"}})
        with pytest.raises(ArccosAuthError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.status_code == 401

    def test_401xx_error_code_raises_auth_error(self):
        resp = _mock_response(400, {"error": {"code": 40101, "description": "Token expired"}})
        resp.ok = False
        resp.status_code = 400
        # The code checks for 40100-40199 range regardless of HTTP status
        with pytest.raises(ArccosAuthError):
            raise_for_status(resp)

    def test_403_raises_forbidden_error(self):
        resp = _mock_response(403)
        with pytest.raises(ArccosForbiddenError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.status_code == 403

    def test_404_raises_not_found_error(self):
        resp = _mock_response(404, {"error": {"code": 404, "description": "Not found"}})
        with pytest.raises(ArccosNotFoundError) as exc_info:
            raise_for_status(resp)
        assert "Not found" in str(exc_info.value)

    def test_429_raises_rate_limit_error(self):
        resp = _mock_response(429)
        with pytest.raises(ArccosRateLimitError):
            raise_for_status(resp)

    def test_500_raises_generic_error(self):
        resp = _mock_response(500, {"error": {"code": 500, "description": "Server error"}})
        with pytest.raises(ArccosError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.status_code == 500

    def test_no_json_body_uses_text(self):
        resp = _mock_response(502, text="Bad Gateway")
        with pytest.raises(ArccosError, match="Bad Gateway"):
            raise_for_status(resp)

    def test_truncates_long_error_text(self):
        resp = _mock_response(500, text="x" * 500)
        with pytest.raises(ArccosError) as exc_info:
            raise_for_status(resp)
        assert len(str(exc_info.value)) <= 200


class TestArccosError:
    def test_repr(self):
        err = ArccosError("test message", status_code=418, error_code=41800)
        r = repr(err)
        assert "418" in r
        assert "41800" in r
        assert "test message" in r

    def test_str(self):
        err = ArccosError("something broke")
        assert str(err) == "something broke"

    def test_subclass_hierarchy(self):
        assert issubclass(ArccosAuthError, ArccosError)
        assert issubclass(ArccosNotFoundError, ArccosError)
        assert issubclass(ArccosRateLimitError, ArccosError)
        assert issubclass(ArccosForbiddenError, ArccosError)
