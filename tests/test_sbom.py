import json
from pathlib import Path

from sentinel.security.sbom import build_cyclonedx_sbom, write_cyclonedx_sbom


def test_sbom_is_deterministic_and_sorted(tmp_path: Path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text(
        """
version = 1

[[package]]
name = "z-package"
version = "2.0.0"

[[package]]
name = "a_package"
version = "1.0.0"
""".strip(),
        encoding="utf-8",
    )

    first = build_cyclonedx_sbom(lock)
    second = build_cyclonedx_sbom(lock)

    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert [component["name"] for component in first["components"]] == [
        "a-package",
        "z-package",
    ]


def test_sbom_writer_creates_parent_directory(tmp_path: Path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text(
        'version = 1\n[[package]]\nname = "example"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )
    output = tmp_path / "nested" / "sbom.json"

    write_cyclonedx_sbom(lock, output)

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["components"][0]["purl"] == "pkg:pypi/example@1.2.3"
