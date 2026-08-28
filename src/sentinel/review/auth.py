import hashlib
import hmac
import json
from pathlib import Path

from sentinel.review.errors import ReviewAuthorizationError
from sentinel.review.models import ReviewerRole, ReviewPrincipal


class ReviewAuthorizer:
    def __init__(self, token_hashes: dict[str, ReviewPrincipal]) -> None:
        self._token_hashes = token_hashes

    @classmethod
    def from_file(cls, path: Path) -> "ReviewAuthorizer":
        if not path.is_file():
            raise ValueError(f"review authorization file is missing: {path}")
        document = json.loads(path.read_text(encoding="utf-8"))
        principals = document.get("principals")
        if not isinstance(principals, list) or not principals:
            raise ValueError("review authorization file requires principals")
        token_hashes: dict[str, ReviewPrincipal] = {}
        for entry in principals:
            token_hash = str(entry["token_sha256"]).lower()
            if len(token_hash) != 64 or any(char not in "0123456789abcdef" for char in token_hash):
                raise ValueError("review token_sha256 must be a lowercase SHA-256 digest")
            token_hashes[token_hash] = ReviewPrincipal(
                reviewer_id=entry["reviewer_id"],
                role=ReviewerRole(entry["role"]),
            )
        return cls(token_hashes)

    def authenticate(self, token: str) -> ReviewPrincipal:
        candidate = hashlib.sha256(token.encode("utf-8")).hexdigest()
        for token_hash, principal in self._token_hashes.items():
            if hmac.compare_digest(candidate, token_hash):
                return principal.model_copy()
        raise ReviewAuthorizationError("invalid reviewer credentials")
