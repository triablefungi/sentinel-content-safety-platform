import argparse
from pathlib import Path

from sentinel.security.sbom import write_cyclonedx_sbom


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a reproducible CycloneDX SBOM")
    parser.add_argument("--lock", type=Path, default=Path("uv.lock"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/security/sbom.cdx.json"),
    )
    args = parser.parse_args()
    write_cyclonedx_sbom(args.lock, args.output)
    print(f"CycloneDX SBOM written to {args.output}")


if __name__ == "__main__":
    main()
