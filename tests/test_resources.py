"""
Tests for resource modules: clubs, courses, handicap, stats.

Rounds are tested separately in test_rounds.py.
"""

from unittest.mock import MagicMock

from arccos.resources.clubs import ClubsResource
from arccos.resources.courses import CoursesResource
from arccos.resources.handicap import HandicapResource
from arccos.resources.stats import StatsResource


# ---------------------------------------------------------------------------
# ClubsResource
# ---------------------------------------------------------------------------

class TestClubsResource:
    def _resource(self) -> tuple[ClubsResource, MagicMock]:
        http = MagicMock()
        return ClubsResource(http, "user-123"), http

    def test_smart_distances_returns_list(self):
        res, http = self._resource()
        http.get.return_value = [
            {"clubType": "Driver", "smartDistance": 240, "averageDistance": 245, "totalShots": 50},
        ]
        result = res.smart_distances()
        assert len(result) == 1
        assert result[0]["clubType"] == "Driver"

    def test_smart_distances_extracts_from_dict(self):
        res, http = self._resource()
        http.get.return_value = {"clubs": [{"clubType": "7 Iron"}]}
        result = res.smart_distances()
        assert result == [{"clubType": "7 Iron"}]

    def test_smart_distances_with_filters(self):
        res, http = self._resource()
        http.get.return_value = []
        res.smart_distances(num_shots=10, start_date="2025-01-01", end_date="2025-12-31")
        params = http.get.call_args[1]["params"]
        assert params["numberOfShots"] == 10
        assert params["startDate"] == "2025-01-01"
        assert params["endDate"] == "2025-12-31"

    def test_smart_distances_no_filters_empty_params(self):
        res, http = self._resource()
        http.get.return_value = []
        res.smart_distances()
        params = http.get.call_args[1]["params"]
        assert params == {}

    def test_bag(self):
        res, http = self._resource()
        http.get.return_value = {"bagId": "bag-1", "clubs": []}
        result = res.bag("bag-1")
        assert result["bagId"] == "bag-1"
        http.get.assert_called_with("/users/user-123/bags/bag-1")

    def test_club_shots(self):
        res, http = self._resource()
        http.get.return_value = [{"shotId": 1}]
        result = res.club_shots("bag-1", "club-1", limit=50, offset=10)
        params = http.get.call_args[1]["params"]
        assert params["limit"] == 50
        assert params["offSet"] == 10

    def test_club_shots_with_round_filter(self):
        res, http = self._resource()
        http.get.return_value = []
        res.club_shots("bag-1", "club-1", round_id="round-1")
        params = http.get.call_args[1]["params"]
        assert params["roundId"] == "round-1"


# ---------------------------------------------------------------------------
# CoursesResource
# ---------------------------------------------------------------------------

class TestCoursesResource:
    def _resource(self) -> tuple[CoursesResource, MagicMock]:
        http = MagicMock()
        return CoursesResource(http, "user-123"), http

    def test_get_course(self):
        res, http = self._resource()
        http.get.return_value = {"courseName": "Augusta National", "courseId": 1}
        result = res.get(1)
        assert result["courseName"] == "Augusta National"
        params = http.get.call_args[1]["params"]
        assert params["courseVersion"] == 1

    def test_get_course_with_version(self):
        res, http = self._resource()
        http.get.return_value = {"courseName": "Test"}
        res.get(1, version=3)
        params = http.get.call_args[1]["params"]
        assert params["courseVersion"] == 3

    def test_played_returns_list(self):
        res, http = self._resource()
        http.get.return_value = [{"courseId": 1}, {"courseId": 2}]
        result = res.played()
        assert len(result) == 2

    def test_played_extracts_from_dict(self):
        res, http = self._resource()
        http.get.return_value = {"courses": [{"courseId": 1}]}
        result = res.played()
        assert result == [{"courseId": 1}]

    def test_search(self):
        res, http = self._resource()
        http.get.return_value = [{"courseName": "Pine Valley"}]
        result = res.search("Pine")
        assert len(result) == 1
        http.get.assert_called_with("/v2/courses", params={"search": "Pine"})

    def test_search_extracts_from_dict(self):
        res, http = self._resource()
        http.get.return_value = {"courses": [{"courseName": "Test"}]}
        result = res.search("Test")
        assert result == [{"courseName": "Test"}]

    def test_init_without_user_id(self):
        http = MagicMock()
        res = CoursesResource(http)
        assert res._user_id is None


# ---------------------------------------------------------------------------
# HandicapResource
# ---------------------------------------------------------------------------

class TestHandicapResource:
    def _resource(self) -> tuple[HandicapResource, MagicMock]:
        http = MagicMock()
        return HandicapResource(http, "user-123"), http

    def test_current(self):
        res, http = self._resource()
        http.get.return_value = {"handicapIndex": 15.2, "lowHandicapIndex": 14.1}
        result = res.current()
        assert result["handicapIndex"] == 15.2
        http.get.assert_called_with("/users/user-123/handicaps/latest")

    def test_history_returns_list(self):
        res, http = self._resource()
        http.get.return_value = [{"date": "2025-01-01", "index": 15.2}]
        result = res.history(rounds=10)
        assert len(result) == 1
        params = http.get.call_args[1]["params"]
        assert params["rounds"] == 10

    def test_history_extracts_from_dict(self):
        res, http = self._resource()
        http.get.return_value = {"handicaps": [{"date": "2025-01-01"}]}
        result = res.history()
        assert result == [{"date": "2025-01-01"}]


# ---------------------------------------------------------------------------
# StatsResource
# ---------------------------------------------------------------------------

class TestStatsResource:
    def _resource(self) -> tuple[StatsResource, MagicMock]:
        http = MagicMock()
        return StatsResource(http, "user-123"), http

    def test_strokes_gained_single_round(self):
        res, http = self._resource()
        http.get.return_value = {"overallSga": -2.1, "drivingSga": 0.4}
        result = res.strokes_gained([12345])
        assert result["overallSga"] == -2.1
        call_args = http.get.call_args
        assert "12345" in call_args[0][0]

    def test_strokes_gained_multiple_rounds(self):
        res, http = self._resource()
        http.get.return_value = {}
        res.strokes_gained([111, 222, 333])
        call_args = http.get.call_args
        assert "111,222,333" in call_args[0][0]
        assert call_args[1]["params"]["roundId"] == "111,222,333"

    def test_strokes_to_get_down(self):
        res, http = self._resource()
        http.get.return_value = {"data": "value"}
        result = res.strokes_to_get_down()
        http.get.assert_called_with("/v2/sga/strokes-to-get-down")

    def test_personal_bests(self):
        res, http = self._resource()
        http.get.return_value = {"longestDrive": 285}
        result = res.personal_bests()
        assert result["longestDrive"] == 285
        params = http.get.call_args[1]["params"]
        assert params["tags"] == "allTimeBest"

    def test_overall_stats(self):
        res, http = self._resource()
        http.get.return_value = {"girPct": 44.2}
        result = res.overall_stats()
        http.get.assert_called_with("/users/user-123/stats/overall")

    def test_sga_filter_settings(self):
        res, http = self._resource()
        http.get.return_value = {"dateRange": "last90"}
        result = res.sga_filter_settings()
        params = http.get.call_args[1]["params"]
        assert params["userId"] == "user-123"
