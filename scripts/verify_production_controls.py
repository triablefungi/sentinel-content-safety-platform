import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify local API production controls")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--max-request-bytes", type=int, default=8 * 1024 * 1024)
    args = parser.parse_args()

    with urlopen(f"{args.base_url}/health", timeout=10) as response:  # noqa: S310
        headers = response.headers
        required = {
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
        for name, expected in required.items():
            if headers.get(name) != expected:
                raise RuntimeError(f"missing or invalid {name} header")

    payload = json.dumps(
        {
            "request_id": f"security-smoke-{uuid4()}",
            "text": "Thank you for sharing.",
        }
    ).encode()
    request = Request(
        f"{args.base_url}/v1/moderate/text",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310
        if response.headers.get("RateLimit-Limit") is None:
            raise RuntimeError("rate-limit headers were not exported")

    oversized = Request(
        f"{args.base_url}/v1/moderate/text",
        data=b"x" * (args.max_request_bytes + 1),
        headers={"Content-Type": "application/octet-stream"},
        method="POST",
    )
    try:
        urlopen(oversized, timeout=10)  # noqa: S310
    except HTTPError as error:
        if error.code != 413:
            raise RuntimeError(f"oversized request returned HTTP {error.code}") from error
    else:
        raise RuntimeError("oversized request was accepted")

    print("Security headers: verified")
    print("Rate-limit metadata: verified")
    print("Request-size rejection: verified")
    print("Production controls: verified")


if __name__ == "__main__":
    main()
