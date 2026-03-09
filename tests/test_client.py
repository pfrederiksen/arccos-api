"""
Tests for arccos.client — ArccosClient initialization paths.
"""

from unittest.mock import patch

import pytest
from conftest import make_creds

from arccos.client import ArccosClient


class TestArccosClientInit:
    @patch("arccos.client.HttpClient")
    @patch("arccos.client.ArccosAuth")
    def test_init_with_email_and_password(self, MockAuth, MockHttp):
        auth_instance = MockAuth.return_value
        creds = make_creds()
        auth_instance.load_or_login.return_value = creds

        client = ArccosClient(email="test@example.com", password="password")

        auth_instance.load_or_login.assert_called_once_with("test@example.com", "password")
        assert client.email == "test@example.com"
        assert client.user_id == "test-user-id"

    @patch("arccos.client.HttpClient")
    @patch("arccos.client.ArccosAuth")
    def test_init_with_creds_object(self, MockAuth, MockHttp):
        auth_instance = MockAuth.return_value
        creds = make_creds()
        auth_instance.ensure_fresh.return_value = creds

        client = ArccosClient(creds=creds)

        auth_instance.ensure_fresh.assert_called_once_with(creds)
        assert client.user_id == creds.user_id

    @patch("arccos.client.Credentials")
    @patch("arccos.client.HttpClient")
    @patch("arccos.client.ArccosAuth")
    def test_init_from_cached_credentials(self, MockAuth, MockHttp, MockCreds):
        auth_instance = MockAuth.return_value
        creds = make_creds()
        MockCreds.load.return_value = creds
        auth_instance.ensure_fresh.return_value = creds

        ArccosClient()

        MockCreds.load.assert_called_once()
        auth_instance.ensure_fresh.assert_called_once_with(creds)

    @patch("arccos.client.Credentials")
    @patch("arccos.client.HttpClient")
    @patch("arccos.client.ArccosAuth")
    def test_init_no_creds_raises_value_error(self, MockAuth, MockHttp, MockCreds):
        MockCreds.load.return_value = None

        with pytest.raises(ValueError, match="Provide email and password"):
            ArccosClient()

    @patch("arccos.client.HttpClient")
    @patch("arccos.client.ArccosAuth")
    def test_resources_initialized(self, MockAuth, MockHttp):
        auth_instance = MockAuth.return_value
        creds = make_creds()
        auth_instance.ensure_fresh.return_value = creds

        client = ArccosClient(creds=creds)

        assert client.rounds is not None
        assert client.handicap is not None
        assert client.clubs is not None
        assert client.courses is not None
        assert client.stats is not None

    @patch("arccos.client.HttpClient")
    @patch("arccos.client.ArccosAuth")
    def test_repr(self, MockAuth, MockHttp):
        auth_instance = MockAuth.return_value
        creds = make_creds()
        auth_instance.ensure_fresh.return_value = creds

        client = ArccosClient(creds=creds)
        r = repr(client)
        assert "test@example.com" in r
        assert "test-user-id" in r
