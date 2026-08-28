from pathlib import Path

from sentinel.security.repository_check import validate_repository_security


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository_security(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Security configuration gate passed.")


if __name__ == "__main__":
    main()
