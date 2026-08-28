import json
import tomllib
from pathlib import Path
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5


def build_cyclonedx_sbom(lock_path: Path) -> dict[str, object]:
    with lock_path.open("rb") as handle:
        lock = tomllib.load(handle)
    packages = lock.get("package")
    if not isinstance(packages, list):
        raise ValueError("uv.lock does not contain a package list")

    components: dict[tuple[str, str], dict[str, str]] = {}
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError("uv.lock package entries must be tables")
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise ValueError("uv.lock package entries require name and version")
        normalized_name = name.lower().replace("_", "-")
        purl = f"pkg:pypi/{quote(normalized_name)}@{quote(version)}"
        components[(normalized_name, version)] = {
            "type": "library",
            "bom-ref": purl,
            "name": normalized_name,
            "version": version,
            "purl": purl,
        }

    ordered = [components[key] for key in sorted(components)]
    identity = "\n".join(f"{item['name']}=={item['version']}" for item in ordered)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid5(NAMESPACE_URL, identity)}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": "sentinel-content-safety-platform",
                "name": "sentinel-content-safety-platform",
                "version": "0.1.0",
            },
            "properties": [
                {
                    "name": "sentinel:source",
                    "value": "uv.lock",
                },
                {
                    "name": "sentinel:reproducible",
                    "value": "true",
                },
            ],
        },
        "components": ordered,
    }


def write_cyclonedx_sbom(lock_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_cyclonedx_sbom(lock_path), indent=2) + "\n",
        encoding="utf-8",
    )
