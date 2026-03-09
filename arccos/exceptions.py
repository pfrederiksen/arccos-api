"""
Custom exceptions for the Arccos API client.
"""


class ArccosError(Exception):
    """Base exception for all Arccos API errors."""

    def __init__(self, message: str, status_code: int = None, error_code: int = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={str(self)!r}, "
            f"status_code={self.status_code}, "
            f"error_code={self.error_code})"
        )


class ArccosAuthError(ArccosError):
    """Raised when authentication fails (bad credentials, expired token, etc.)."""


class ArccosNotFoundError(ArccosError):
    """Raised when a requested resource does not exist (HTTP 404)."""


class ArccosRateLimitError(ArccosError):
    """Raised when the API returns HTTP 429 Too Many Requests."""


class ArccosForbiddenError(ArccosError):
    """Raised when access to a resource is denied (HTTP 403)."""


def raise_for_status(response) -> None:
    """
    Raise an appropriate ArccosError for non-2xx responses.

    Args:
        response: A requests.Response object.

    Raises:
        ArccosAuthError: HTTP 401 or Arccos error code 401xx.
        ArccosForbiddenError: HTTP 403.
        ArccosNotFoundError: HTTP 404.
        ArccosRateLimitError: HTTP 429.
        ArccosError: Any other non-2xx status.
    """
    if response.ok:
        return

    status = response.status_code
    try:
        body = response.json()
        error = body.get("error", {})
        code = error.get("code", status)
        message = error.get("description", response.text[:200])
    except Exception:
        code = status
        message = response.text[:200]

    if status == 401 or (isinstance(code, int) and 40100 <= code <= 40199):
        raise ArccosAuthError(message, status_code=status, error_code=code)
    elif status == 403:
        raise ArccosForbiddenError(message, status_code=status, error_code=code)
    elif status == 404:
        raise ArccosNotFoundError(message, status_code=status, error_code=code)
    elif status == 429:
        raise ArccosRateLimitError(message, status_code=status, error_code=code)
    else:
        raise ArccosError(message, status_code=status, error_code=code)
