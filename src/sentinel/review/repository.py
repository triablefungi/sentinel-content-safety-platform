import json
import threading
from pathlib import Path
from typing import Protocol

from sentinel.review.models import (
    ReviewAuditEvent,
    ReviewCase,
    ReviewState,
    audit_event_digest,
)


class ReviewRepository(Protocol):
    def get(self, case_id: str) -> ReviewCase | None: ...

    def find_by_request_id(self, request_id: str) -> ReviewCase | None: ...

    def list_cases(self, state: ReviewState | None = None) -> list[ReviewCase]: ...

    def audit(self, case_id: str) -> list[ReviewAuditEvent]: ...

    def commit(self, case: ReviewCase, event: ReviewAuditEvent) -> None: ...


class InMemoryReviewRepository:
    def __init__(self) -> None:
        self._cases: dict[str, ReviewCase] = {}
        self._request_index: dict[str, str] = {}
        self._events: dict[str, list[ReviewAuditEvent]] = {}
        self._lock = threading.RLock()

    def get(self, case_id: str) -> ReviewCase | None:
        with self._lock:
            case = self._cases.get(case_id)
            return case.model_copy(deep=True) if case else None

    def find_by_request_id(self, request_id: str) -> ReviewCase | None:
        with self._lock:
            case_id = self._request_index.get(request_id)
            return self.get(case_id) if case_id else None

    def list_cases(self, state: ReviewState | None = None) -> list[ReviewCase]:
        with self._lock:
            cases = [case for case in self._cases.values() if state is None or case.state == state]
            ordered = sorted(cases, key=lambda item: item.created_at)
            return [case.model_copy(deep=True) for case in ordered]

    def audit(self, case_id: str) -> list[ReviewAuditEvent]:
        with self._lock:
            return [event.model_copy(deep=True) for event in self._events.get(case_id, [])]

    def commit(self, case: ReviewCase, event: ReviewAuditEvent) -> None:
        with self._lock:
            self._cases[case.case_id] = case.model_copy(deep=True)
            self._request_index[case.request_id] = case.case_id
            self._events.setdefault(case.case_id, []).append(event.model_copy(deep=True))


class JsonlReviewRepository(InMemoryReviewRepository):
    """Single-process append-only ledger with an in-memory query projection."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self._replay()

    def _replay(self) -> None:
        for line_number, line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                case = ReviewCase.model_validate(record["case"])
                event = ReviewAuditEvent.model_validate(record["event"])
            except (KeyError, ValueError, TypeError) as error:
                raise ValueError(f"invalid review ledger record at line {line_number}") from error
            previous_events = self._events.get(case.case_id, [])
            expected_previous = previous_events[-1].event_hash if previous_events else "0" * 64
            payload = {
                "event_id": event.event_id,
                "case_id": event.case_id,
                "sequence": event.sequence,
                "action": event.action.value,
                "actor_id": event.actor_id,
                "actor_role": event.actor_role.value if event.actor_role else None,
                "from_state": event.from_state.value if event.from_state else None,
                "to_state": event.to_state.value,
                "reason_code": event.reason_code,
                "occurred_at": event.occurred_at.isoformat(),
                "previous_hash": event.previous_hash,
            }
            hash_is_valid = event.event_hash == audit_event_digest(payload)
            if event.previous_hash != expected_previous or not hash_is_valid:
                raise ValueError(f"review ledger integrity failure at line {line_number}")
            if event.sequence != len(previous_events) + 1:
                raise ValueError(f"review ledger sequence failure at line {line_number}")
            super().commit(case, event)

    def commit(self, case: ReviewCase, event: ReviewAuditEvent) -> None:
        record = {"case": case.model_dump(mode="json"), "event": event.model_dump(mode="json")}
        serialized = json.dumps(record, separators=(",", ":"), sort_keys=True)
        with self._lock:
            with self._path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized + "\n")
                stream.flush()
            super().commit(case, event)
