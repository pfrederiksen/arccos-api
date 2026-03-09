"""
Courses resource — access Arccos course data.

Endpoint prefix: /courses, /users/{userId}/coursesPlayed
"""

from __future__ import annotations

from .._http import HttpClient


class CoursesResource:
    """
    Access course metadata and the user's played-courses list.

    Available via ``client.courses``.

    Example::

        played = client.courses.played()
        print(f"Played {len(played)} courses")

        course = client.courses.get(10769)
        print(course["courseName"])
    """

    def __init__(self, http: HttpClient, user_id: str = None):
        self._http = http
        self._user_id = user_id

    def get(self, course_id: int, version: int = 1) -> dict:
        """
        Fetch metadata for a specific course.

        Args:
            course_id: Arccos internal course ID (integer).
            version: Course version (default 1). Use the ``courseVersion`` value
                     from a round object to get the exact tee layout used.

        Returns:
            Course dict including:

            - ``courseName`` — full course name
            - ``city``, ``state``, ``country`` — location
            - ``tees`` — list of tee set configurations
            - ``holes`` — hole-level par and yardage data
        """
        return self._http.get(
            f"/courses/{course_id}",
            params={"courseVersion": version},
        )

    def played(self) -> list[dict]:
        """
        Fetch all courses the user has played.

        Returns:
            List of course summary dicts (courseId, courseName, roundsPlayed, etc.).
        """
        data = self._http.get(f"/users/{self._user_id}/coursesPlayed")
        return data if isinstance(data, list) else data.get("courses", data)

    def search(self, query: str) -> list[dict]:
        """
        Search for courses by name.

        Args:
            query: Search string (course name or partial name).

        Returns:
            List of matching course dicts.
        """
        data = self._http.get("/v2/courses", params={"search": query})
        return data if isinstance(data, list) else data.get("courses", data)
