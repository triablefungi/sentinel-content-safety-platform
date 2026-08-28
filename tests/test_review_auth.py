import hashlib
import json

import pytest

from sentinel.review.auth import ReviewAuthorizer
from sentinel.review.errors import ReviewAuthorizationError


def test_authorizer_loads_hashed_token_without_storing_plaintext(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    token = "reviewer-secret"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    path = tmp_path / "reviewer-auth.json"
    path.write_text(
        json.dumps(
            {
                "principals": [
                    {
                        "reviewer_id": "reviewer-1",
                        "role": "reviewer",
                        "token_sha256": token_hash,
                    }
                ]
            }
        )
    )

    authorizer = ReviewAuthorizer.from_file(path)

    assert authorizer.authenticate(token).reviewer_id == "reviewer-1"
    with pytest.raises(ReviewAuthorizationError, match="invalid reviewer credentials"):
        authorizer.authenticate("wrong-secret")


def test_authorizer_rejects_invalid_token_digest(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "reviewer-auth.json"
    path.write_text(
        json.dumps(
            {
                "principals": [
                    {
                        "reviewer_id": "reviewer-1",
                        "role": "reviewer",
                        "token_sha256": "not-a-digest",
                    }
                ]
            }
        )
    )

    with pytest.raises(ValueError, match="SHA-256"):
        ReviewAuthorizer.from_file(path)
