import json
from pathlib import Path

REQUIRED_HEADERS = {
    "Cache-Control",
    "Content-Security-Policy",
    "Permissions-Policy",
    "Referrer-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
}


def validate_repository_security(root: Path) -> list[str]:
    errors: list[str] = []
    policy_path = root / "config" / "security-policy.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"security policy could not be read: {error}"]

    configured_headers = set(policy.get("api", {}).get("required_headers", []))
    if configured_headers != REQUIRED_HEADERS:
        errors.append("security policy required_headers does not match the runtime contract")

    production = policy.get("production", {})
    if production.get("docs_enabled") is not False:
        errors.append("production documentation must be disabled")
    if production.get("hsts_enabled") is not True:
        errors.append("production HSTS must be enabled")
    if production.get("rate_limit_enabled") is not True:
        errors.append("production rate limiting must be enabled")

    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    if "USER sentinel" not in dockerfile:
        errors.append("Docker image must run as the sentinel user")
    if "--no-server-header" not in dockerfile:
        errors.append("Uvicorn server header must be disabled")

    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    required_compose_fragments = {
        'SENTINEL_RATE_LIMIT_ENABLED: "true"': "Compose rate limiting is not enabled",
        'SENTINEL_MAX_REQUEST_BYTES: "8388608"': "Compose request-size limit is absent",
        '"127.0.0.1:8000:8000"': "API port is not restricted to localhost",
        "no-new-privileges:true": "API/worker privilege escalation is not disabled",
    }
    for fragment, message in required_compose_fragments.items():
        if fragment not in compose:
            errors.append(message)

    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for secret_path in (".env", "config/reviewer-auth.json"):
        if secret_path not in gitignore:
            errors.append(f"{secret_path} must be ignored")

    sbom_path = root / "artifacts" / "security" / "sbom.cdx.json"
    if not sbom_path.exists():
        errors.append("versioned CycloneDX SBOM is absent")
    if not (root / ".github" / "workflows" / "container-security.yml").exists():
        errors.append("scheduled container vulnerability scan is absent")
    return errors
