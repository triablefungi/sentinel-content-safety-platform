class ReviewError(Exception):
    """Base error for review workflow failures."""


class ReviewNotFoundError(ReviewError):
    """The requested review case does not exist."""


class ReviewConflictError(ReviewError):
    """The requested state transition is invalid or stale."""


class ReviewAuthorizationError(ReviewError):
    """The principal is not authorized for the requested operation."""
