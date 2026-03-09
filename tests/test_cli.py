"""
Tests for arccos.cli — CLI commands via Click's CliRunner.

These tests mock the ArccosClient so no real API calls are made.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from arccos.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def _mock_client():
    """Create a fully mocked ArccosClient with all resource attributes."""
    client = MagicMock()
    client.email = "test@example.com"
    client.user_id = "user-123"
    return client


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLoginCommand:
    @patch("arccos.ArccosClient")
    def test_login_success(self, MockClient, runner):
        client = _mock_client()
        MockClient.return_value = client

        result = runner.invoke(cli, ["login", "--email", "a@b.com", "--password", "pass"])
        assert result.exit_code == 0
        assert "Logged in" in result.output

    @patch("arccos.ArccosClient")
    def test_login_failure(self, MockClient, runner):
        from arccos.exceptions import ArccosAuthError
        MockClient.side_effect = ArccosAuthError("Bad creds", status_code=401)

        result = runner.invoke(cli, ["login", "--email", "a@b.com", "--password", "wrong"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# rounds
# ---------------------------------------------------------------------------

class TestRoundsCommand:
    @patch("arccos.cli._get_client")
    def test_rounds_table_output(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = [
            {
                "roundId": 1,
                "courseId": 100,
                "startTime": "2025-06-01T08:00:00.000Z",
                "noOfShots": 85,
                "noOfHoles": 18,
            }
        ]
        mock_get.return_value = client

        result = runner.invoke(cli, ["rounds"])
        assert result.exit_code == 0
        assert "2025-06-01" in result.output
        assert "85" in result.output

    @patch("arccos.cli._get_client")
    def test_rounds_json_output(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = [{"roundId": 1}]
        mock_get.return_value = client

        result = runner.invoke(cli, ["rounds", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["roundId"] == 1

    @patch("arccos.cli._get_client")
    def test_rounds_empty(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = []
        mock_get.return_value = client

        result = runner.invoke(cli, ["rounds"])
        assert result.exit_code == 0
        assert "No rounds found" in result.output

    @patch("arccos.cli._get_client")
    def test_rounds_passes_options(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = []
        mock_get.return_value = client

        runner.invoke(cli, ["rounds", "-n", "5", "-o", "10", "-a", "2025-01-01", "-b", "2025-06-01"])
        client.rounds.list.assert_called_once_with(
            limit=5, offset=10, after_date="2025-01-01", before_date="2025-06-01"
        )


# ---------------------------------------------------------------------------
# handicap
# ---------------------------------------------------------------------------

class TestHandicapCommand:
    @patch("arccos.cli._get_client")
    def test_handicap_current(self, mock_get, runner):
        client = _mock_client()
        client.handicap.current.return_value = {"handicapIndex": 18.2}
        mock_get.return_value = client

        result = runner.invoke(cli, ["handicap"])
        assert result.exit_code == 0
        assert "18.2" in result.output

    @patch("arccos.cli._get_client")
    def test_handicap_history(self, mock_get, runner):
        client = _mock_client()
        client.handicap.history.return_value = [
            {"date": "2025-01-01", "index": 18.2},
            {"date": "2025-02-01", "index": 17.5},
        ]
        mock_get.return_value = client

        result = runner.invoke(cli, ["handicap", "--history"])
        assert result.exit_code == 0
        assert "18.2" in result.output

    @patch("arccos.cli._get_client")
    def test_handicap_json(self, mock_get, runner):
        client = _mock_client()
        client.handicap.current.return_value = {"handicapIndex": 18.2}
        mock_get.return_value = client

        result = runner.invoke(cli, ["handicap", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["handicapIndex"] == 18.2


# ---------------------------------------------------------------------------
# clubs
# ---------------------------------------------------------------------------

class TestClubsCommand:
    @patch("arccos.cli._get_client")
    def test_clubs_table_output(self, mock_get, runner):
        client = _mock_client()
        client.clubs.smart_distances.return_value = [
            {
                "clubId": 1,
                "smartDistance": {"distance": 240.5, "unit": "yd"},
                "longest": {"distance": 285.0, "unit": "yd"},
                "range": {"low": 230.0, "high": 250.0, "unit": "yd"},
                "usage": {"count": 50},
            },
            {
                "clubId": 9,
                "smartDistance": {"distance": 155.0, "unit": "yd"},
                "longest": {"distance": 170.0, "unit": "yd"},
                "range": {"low": 145.0, "high": 165.0, "unit": "yd"},
                "usage": {"count": 80},
            },
        ]
        mock_get.return_value = client

        result = runner.invoke(cli, ["clubs"])
        assert result.exit_code == 0
        assert "Dr" in result.output
        assert "240y" in result.output

    @patch("arccos.cli._get_client")
    def test_clubs_empty(self, mock_get, runner):
        client = _mock_client()
        client.clubs.smart_distances.return_value = []
        mock_get.return_value = client

        result = runner.invoke(cli, ["clubs"])
        assert "No club data" in result.output

    @patch("arccos.cli._get_client")
    def test_clubs_json(self, mock_get, runner):
        client = _mock_client()
        client.clubs.smart_distances.return_value = [{"clubType": "PW"}]
        mock_get.return_value = client

        result = runner.invoke(cli, ["clubs", "--json"])
        data = json.loads(result.output)
        assert data[0]["clubType"] == "PW"


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

class TestStatsCommand:
    @patch("arccos.cli._get_client")
    def test_stats_with_round_id(self, mock_get, runner):
        client = _mock_client()
        client.stats.strokes_gained.return_value = {
            "overallSga": -2.1,
            "drivingSga": 0.4,
            "approachSga": -1.8,
            "shortSga": -0.3,
            "puttingSga": -0.4,
        }
        mock_get.return_value = client

        result = runner.invoke(cli, ["stats", "12345"])
        assert result.exit_code == 0
        assert "Overall" in result.output

    @patch("arccos.cli._get_client")
    def test_stats_latest(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = [
            {"roundId": 999, "startTime": "2025-06-01T08:00:00Z"}
        ]
        client.stats.strokes_gained.return_value = {"overallSga": 1.5}
        mock_get.return_value = client

        result = runner.invoke(cli, ["stats", "--latest"])
        assert result.exit_code == 0
        client.stats.strokes_gained.assert_called_once_with([999])

    @patch("arccos.cli._get_client")
    def test_stats_no_args_shows_help(self, mock_get, runner):
        client = _mock_client()
        mock_get.return_value = client

        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 1

    @patch("arccos.cli._get_client")
    def test_stats_json(self, mock_get, runner):
        client = _mock_client()
        client.stats.strokes_gained.return_value = {"overallSga": -2.1}
        mock_get.return_value = client

        result = runner.invoke(cli, ["stats", "--json", "12345"])
        data = json.loads(result.output)
        assert data["overallSga"] == -2.1


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

class TestExportCommand:
    @patch("arccos.cli._get_client")
    def test_export_json_stdout(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = [{"roundId": 1, "noOfShots": 85}]
        mock_get.return_value = client

        result = runner.invoke(cli, ["export"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["roundId"] == 1

    @patch("arccos.cli._get_client")
    def test_export_csv_stdout(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = [{"roundId": 1, "noOfShots": 85}]
        mock_get.return_value = client

        result = runner.invoke(cli, ["export", "-f", "csv"])
        assert result.exit_code == 0
        assert "roundId" in result.output
        assert "85" in result.output

    @patch("arccos.cli._get_client")
    def test_export_ndjson_stdout(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = [
            {"roundId": 1},
            {"roundId": 2},
        ]
        mock_get.return_value = client

        result = runner.invoke(cli, ["export", "-f", "ndjson"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2

    @patch("arccos.cli._get_client")
    def test_export_to_file(self, mock_get, runner, tmp_path):
        client = _mock_client()
        client.rounds.list.return_value = [{"roundId": 1}]
        mock_get.return_value = client

        outfile = str(tmp_path / "out.json")
        result = runner.invoke(cli, ["export", "-o", outfile])
        assert result.exit_code == 0
        data = json.loads((tmp_path / "out.json").read_text())
        assert data[0]["roundId"] == 1

    @patch("arccos.cli._get_client")
    def test_export_empty_rounds(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = []
        mock_get.return_value = client

        result = runner.invoke(cli, ["export"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# pace
# ---------------------------------------------------------------------------

class TestPaceCommand:
    @patch("arccos.cli._get_client")
    def test_pace_output(self, mock_get, runner):
        client = _mock_client()
        client.rounds.list.return_value = []
        client.rounds.pace_of_play.return_value = {
            "rounds": [
                {
                    "date": "2025-06-01",
                    "course": "Test GC",
                    "score": 85,
                    "duration_minutes": 270,
                    "duration_display": "4h 30m",
                    "round_id": 1,
                }
            ],
            "course_averages": [
                {"course": "Test GC", "avg_minutes": 270, "avg_display": "4h 30m", "rounds": 1}
            ],
            "overall_avg_minutes": 270,
            "overall_avg_display": "4h 30m",
        }
        mock_get.return_value = client

        result = runner.invoke(cli, ["pace"])
        assert result.exit_code == 0
        assert "4h 30m" in result.output
        assert "Test GC" in result.output


# ---------------------------------------------------------------------------
# courses
# ---------------------------------------------------------------------------

class TestCoursesCommand:
    @patch("arccos.cli._get_client")
    def test_courses_table_output(self, mock_get, runner):
        client = _mock_client()
        client.courses.played.return_value = [
            {"courseName": "Augusta National", "city": "Augusta", "state": "GA",
             "roundsPlayed": 3, "courseId": 100},
            {"courseName": "Pebble Beach", "city": "Pebble Beach", "state": "CA",
             "roundsPlayed": 1, "courseId": 200},
        ]
        mock_get.return_value = client

        result = runner.invoke(cli, ["courses"])
        assert result.exit_code == 0
        assert "Augusta National" in result.output
        assert "Pebble Beach" in result.output

    @patch("arccos.cli._get_client")
    def test_courses_empty(self, mock_get, runner):
        client = _mock_client()
        client.courses.played.return_value = []
        mock_get.return_value = client

        result = runner.invoke(cli, ["courses"])
        assert result.exit_code == 0
        assert "No courses found" in result.output

    @patch("arccos.cli._get_client")
    def test_courses_json(self, mock_get, runner):
        client = _mock_client()
        client.courses.played.return_value = [{"courseName": "Test GC"}]
        mock_get.return_value = client

        result = runner.invoke(cli, ["courses", "--json"])
        data = json.loads(result.output)
        assert data[0]["courseName"] == "Test GC"


# ---------------------------------------------------------------------------
# round (detail)
# ---------------------------------------------------------------------------

class TestRoundDetailCommand:
    @patch("arccos.cli._get_client")
    def test_round_detail_output(self, mock_get, runner):
        client = _mock_client()
        client.rounds.get.return_value = {
            "roundId": 12345,
            "courseId": 100,
            "courseName": "Test GC",
            "startTime": "2025-06-01T08:00:00.000Z",
            "noOfShots": 85,
            "noOfHoles": 18,
            "overUnder": 13,
            "holes": [
                {"holeId": 1, "noOfShots": 5, "putts": 2, "isFairWay": "T", "isGir": "F"},
                {"holeId": 2, "noOfShots": 3, "putts": 1, "isFairWay": None, "isGir": "T"},
                {"holeId": 3, "noOfShots": 4, "putts": 2, "isFairWay": "T", "isGir": "T"},
            ],
        }
        mock_get.return_value = client

        result = runner.invoke(cli, ["round", "12345"])
        assert result.exit_code == 0
        assert "2025-06-01" in result.output
        assert "85" in result.output
        assert "Test GC" in result.output

    @patch("arccos.cli._get_client")
    def test_round_detail_no_holes(self, mock_get, runner):
        client = _mock_client()
        client.rounds.get.return_value = {
            "roundId": 12345,
            "startTime": "2025-06-01T08:00:00.000Z",
            "noOfShots": 85,
            "noOfHoles": 18,
            "holes": [],
        }
        mock_get.return_value = client

        result = runner.invoke(cli, ["round", "12345"])
        assert result.exit_code == 0
        assert "No hole data" in result.output

    @patch("arccos.cli._get_client")
    def test_round_detail_json(self, mock_get, runner):
        client = _mock_client()
        client.rounds.get.return_value = {
            "roundId": 12345,
            "holes": [{"holeId": 1}],
        }
        mock_get.return_value = client

        result = runner.invoke(cli, ["round", "--json", "12345"])
        data = json.loads(result.output)
        assert data["roundId"] == 12345


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

class TestLogoutCommand:
    def test_logout_with_existing_creds(self, runner, tmp_path):
        creds_file = tmp_path / ".arccos_creds.json"
        creds_file.write_text('{"test": true}')

        with patch("arccos.auth.DEFAULT_CREDS_PATH", creds_file):
            result = runner.invoke(cli, ["logout"])

        assert result.exit_code == 0
        assert "removed" in result.output
        assert not creds_file.exists()

    def test_logout_no_creds(self, runner, tmp_path):
        creds_file = tmp_path / ".arccos_creds.json"

        with patch("arccos.auth.DEFAULT_CREDS_PATH", creds_file):
            result = runner.invoke(cli, ["logout"])

        assert result.exit_code == 0
        assert "No cached" in result.output


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

class TestVersionCommand:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


# ---------------------------------------------------------------------------
# help
# ---------------------------------------------------------------------------

class TestHelpCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "arccos" in result.output
