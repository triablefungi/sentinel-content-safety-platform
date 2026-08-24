class IdempotencyConflictError(Exception):
    """A request ID was reused with different content."""


class QueueUnavailableError(Exception):
    """The event could not be acknowledged by the broker."""
