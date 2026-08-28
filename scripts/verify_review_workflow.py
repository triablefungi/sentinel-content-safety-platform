import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, str] | None = None,
) -> object:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - explicit local verifier
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the local human-review workflow")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--reviewer-token", default="sentinel-reviewer-demo")
    parser.add_argument("--senior-token", default="sentinel-senior-demo")
    parser.add_argument("--auditor-token", default="sentinel-auditor-demo")
    args = parser.parse_args()
    request_id = f"review-smoke-{uuid4()}"

    moderated = request_json(
        "POST",
        f"{args.base_url}/v1/moderate/text",
        payload={"request_id": request_id, "text": "You are worthless."},
    )
    pending_result = request_json(
        "GET",
        f"{args.base_url}/v1/reviews?state=pending",
        token=args.reviewer_token,
    )
    if not isinstance(pending_result, list):
        raise RuntimeError("review queue response was not a list")
    matching = [case for case in pending_result if case["request_id"] == request_id]
    if len(matching) != 1:
        raise RuntimeError("new moderation result was not represented once in the review queue")
    case_id = matching[0]["case_id"]
    request_json(
        "POST",
        f"{args.base_url}/v1/reviews/{case_id}/claim",
        token=args.reviewer_token,
    )
    request_json(
        "POST",
        f"{args.base_url}/v1/reviews/{case_id}/decisions",
        token=args.reviewer_token,
        payload={"decision": "block", "reason_code": "confirmed_abuse"},
    )
    request_json(
        "POST",
        f"{args.base_url}/v1/reviews/{case_id}/appeals",
        token=args.reviewer_token,
        payload={"reason_code": "context_missing"},
    )
    request_json(
        "POST",
        f"{args.base_url}/v1/reviews/{case_id}/claim",
        token=args.senior_token,
    )
    resolved = request_json(
        "POST",
        f"{args.base_url}/v1/reviews/{case_id}/decisions",
        token=args.senior_token,
        payload={"decision": "allow", "reason_code": "appeal_upheld"},
    )
    audit = request_json(
        "GET",
        f"{args.base_url}/v1/reviews/{case_id}/audit",
        token=args.auditor_token,
    )
    export = request_json(
        "GET",
        f"{args.base_url}/v1/review-feedback/export",
        token=args.auditor_token,
    )

    if not all(isinstance(item, dict) for item in (moderated, resolved, export)):
        raise RuntimeError("workflow response shape was invalid")
    if not isinstance(audit, list):
        raise RuntimeError("audit response was not a list")
    print(f"Moderation decision: {moderated['decision']}")
    print(f"Final human decision: {resolved['final_decision']}")
    print(f"Audit events: {len(audit)}")
    print(f"Feedback records: {len(export['records'])}")
    print("Human-review workflow: verified")


if __name__ == "__main__":
    main()
