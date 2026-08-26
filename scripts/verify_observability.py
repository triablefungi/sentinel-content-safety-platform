import argparse
import json
from urllib.request import urlopen

REQUIRED_METRICS = {
    "sentinel_build_info",
    "sentinel_http_requests_total",
    "sentinel_http_request_duration_seconds",
    "sentinel_moderation_decisions_total",
}


def fetch(url: str) -> str:
    with urlopen(url, timeout=10) as response:  # noqa: S310 - local verification utility
        return response.read().decode()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Sentinel readiness and API metrics")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    ready = json.loads(fetch(f"{args.base_url}/health/ready"))
    if ready.get("status") != "ready":
        raise SystemExit(f"readiness check failed: {ready}")

    exposition = fetch(f"{args.base_url}/metrics")
    missing = sorted(metric for metric in REQUIRED_METRICS if metric not in exposition)
    if missing:
        raise SystemExit(f"missing metrics: {', '.join(missing)}")

    print("Readiness: ready")
    print(f"Required metrics exported: {len(REQUIRED_METRICS)}/{len(REQUIRED_METRICS)}")


if __name__ == "__main__":
    main()
