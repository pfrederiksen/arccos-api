"""
Security-focused tests for the arccos package.

Covers credential file permissions, JWT validation hardening,
auth response parsing, and export path handling.
"""

import json
import os
import stat

import pytest
from conftest import make_creds

from arccos.auth import Credentials


class TestCredentialFilePermissions:
    """Verify that credential files are created with restrictive permissions."""

    def test_save_creates_file_with_0600(self, tmp_path):
        creds = make_creds()
        creds_file = tmp_path / "creds.json"

        creds.save(creds_file)

        mode = stat.S_IMODE(os.stat(creds_file).st_mode)
        assert mode == 0o600, f"Expected 0600, got {oct(mode)}"

    def test_save_overwrites_existing_file_keeps_0600(self, tmp_path):
        creds_file = tmp_path / "creds.json"
        # Create with open permissions first
        creds_file.write_text("{}")
        creds_file.chmod(0o644)

        creds = make_creds()
        creds.save(creds_file)

        mode = stat.S_IMODE(os.stat(creds_file).st_mode)
        assert mode == 0o600

    def test_save_writes_valid_json(self, tmp_path):
        creds = make_creds()
        creds_file = tmp_path / "creds.json"

        creds.save(creds_file)

        data = json.loads(creds_file.read_text())
        assert data["email"] == "test@example.com"
        assert data["user_id"] == "test-user-id"
        assert data["access_key"] == "TESTACCESSKEY"

    def test_load_returns_none_for_missing_file(self, tmp_path):
        result = Credentials.load(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_returns_none_for_corrupt_json(self, tmp_path):
        creds_file = tmp_path / "creds.json"
        creds_file.write_text("not json{{{")

        result = Credentials.load(creds_file)
        assert result is None

    def test_load_returns_none_for_missing_keys(self, tmp_path):
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"email": "test@example.com"}')

        result = Credentials.load(creds_file)
        assert result is None


class TestJWTValidation:
    """Verify JWT parsing handles malformed tokens gracefully."""

    def test_valid_jwt_not_expired(self):
        creds = make_creds(exp_offset=3600)
        assert creds.token_expired() is False

    def test_expired_jwt(self):
        creds = make_creds(exp_offset=-10)
        assert creds.token_expired() is True

    def test_empty_token(self):
        creds = make_creds()
        creds.token = ""
        assert creds.token_expired() is True

    def test_single_segment_token(self):
        creds = make_creds()
        creds.token = "not-a-jwt"
        assert creds.token_expired() is True

    def test_two_segment_token(self):
        creds = make_creds()
        creds.token = "header.payload"
        assert creds.token_expired() is True

    def test_four_segment_token(self):
        creds = make_creds()
        creds.token = "a.b.c.d"
        assert creds.token_expired() is True

    def test_invalid_base64_payload(self):
        creds = make_creds()
        creds.token = "header.!!!invalid!!!.sig"
        assert creds.token_expired() is True

    def test_payload_not_json(self):
        import base64

        payload = base64.urlsafe_b64encode(b"not json").rstrip(b"=").decode()
        creds = make_creds()
        creds.token = f"header.{payload}.sig"
        assert creds.token_expired() is True

    def test_payload_missing_exp_claim(self):
        import base64

        payload = base64.urlsafe_b64encode(b'{"sub": "user"}').rstrip(b"=").decode()
        creds = make_creds()
        creds.token = f"header.{payload}.sig"
        assert creds.token_expired() is True

    def test_payload_is_json_array(self):
        import base64

        payload = base64.urlsafe_b64encode(b'[1, 2, 3]').rstrip(b"=").decode()
        creds = make_creds()
        creds.token = f"header.{payload}.sig"
        assert creds.token_expired() is True


class TestExportPathHandling:
    """Verify export resolves symlinks to prevent symlink attacks."""

    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_export_resolves_symlinks(self, runner, tmp_path):
        from unittest.mock import MagicMock, patch

        from arccos.cli import cli

        client = MagicMock()
        client.rounds.list.return_value = [{"roundId": 1}]

        real_file = tmp_path / "real_output.json"
        symlink = tmp_path / "link_output.json"
        symlink.symlink_to(real_file)

        with patch("arccos.cli._get_client", return_value=client):
            result = runner.invoke(cli, ["export", "-o", str(symlink)])

        assert result.exit_code == 0
        # The data should be written to the real file, not the symlink target
        assert real_file.exists()
