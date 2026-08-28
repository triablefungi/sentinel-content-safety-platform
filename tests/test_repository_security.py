from pathlib import Path

from sentinel.security.repository_check import validate_repository_security


def test_repository_security_gate() -> None:
    root = Path(__file__).resolve().parents[1]

    assert validate_repository_security(root) == []
