"""
Tests for arccos.resources.rounds.
"""

from unittest.mock import MagicMock

from arccos.resources.rounds import RoundsResource


def _make_round(round_id: int, course_id: int, start: str, end: str, shots: int) -> dict:
    return {
        "roundId":   round_id,
        "courseId":  course_id,
        "startTime": f"{start}.000000Z",
        "endTime":   f"{end}.000000Z",
        "noOfShots": shots,
        "noOfHoles": 18,
        "isEnded":   "T",
    }


class TestRoundsResource:
    def _resource(self, rounds_response):
        http = MagicMock()
        http.get.return_value = {"rounds": rounds_response, "totalCount": len(rounds_response)}
        res = RoundsResource(http, "test-user")
        return res, http

    def test_list_returns_rounds(self):
        rounds = [_make_round(1, 100, "2026-01-01T08:00:00", "2026-01-01T12:30:00", 85)]
        res, http = self._resource(rounds)
        result = res.list()
        assert len(result) == 1
        assert result[0]["roundId"] == 1
        http.get.assert_called_once()

    def test_list_passes_params(self):
        res, http = self._resource([])
        res.list(limit=10, offset=5, round_type="flagship", before_date="2026-01-01")
        call_params = http.get.call_args[1]["params"]
        assert call_params["limit"]      == 10
        assert call_params["offSet"]     == 5
        assert call_params["roundType"]  == "flagship"
        assert call_params["beforeDate"] == "2026-01-01"

    def test_pace_of_play_computes_duration(self):
        rounds = [
            _make_round(1, 100, "2026-01-01T08:00:00", "2026-01-01T12:30:00", 85),  # 4h30m
            _make_round(2, 101, "2026-01-05T09:00:00", "2026-01-05T14:00:00", 90),  # 5h00m
        ]
        http = MagicMock()
        http.get.side_effect = [
            {"rounds": rounds, "totalCount": 2},  # list()
            {"courseName": "Alpha GC"},            # get_course(100)
            {"courseName": "Beta GC"},             # get_course(101)
        ]
        res = RoundsResource(http, "test-user")
        result = res.pace_of_play()

        assert result["overall_avg_minutes"] == (270 + 300) // 2
        courses = {c["course"]: c["avg_minutes"] for c in result["course_averages"]}
        assert courses["Alpha GC"] == 270
        assert courses["Beta GC"]  == 300

    def test_pace_of_play_skips_bogus_durations(self):
        rounds = [
            _make_round(1, 100, "2026-01-01T08:00:00", "2026-01-01T08:05:00", 0),   # 5 min — skip
            _make_round(2, 100, "2026-01-01T08:00:00", "2026-01-01T22:00:00", 999), # 14h — skip
            _make_round(3, 101, "2026-01-05T09:00:00", "2026-01-05T13:30:00", 88),  # 4h30m — keep
        ]
        http = MagicMock()
        http.get.side_effect = [
            {"rounds": rounds},
            {"courseName": "Alpha GC"},  # courseId 100 (appears in rounds even if skipped)
            {"courseName": "Beta GC"},   # courseId 101
        ]
        res = RoundsResource(http, "test-user")
        result = res.pace_of_play()
        assert len(result["rounds"]) == 1
        assert result["rounds"][0]["course"] == "Beta GC"
