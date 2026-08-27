import argparse
import hashlib
import json
import shutil
from pathlib import Path

REPOSITORY = "OwenElliott/image-safety-classifier-m"
REVISION = "a5ce9ee"
WEIGHTS_FILE = "model.safetensors"
WEIGHTS_SHA256 = "d42733d1d8a0f3ef7fd61847b2be9ae4d79375720b816d0ab47e606b33019e89"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the reviewed Sentinel image model")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/models/image_safety"),
    )
    args = parser.parse_args()

    from huggingface_hub import hf_hub_download

    downloaded = Path(
        hf_hub_download(
            repo_id=REPOSITORY,
            filename=WEIGHTS_FILE,
            revision=REVISION,
        )
    )
    actual_sha256 = _sha256(downloaded)
    if actual_sha256 != WEIGHTS_SHA256:
        raise RuntimeError(
            f"downloaded image-model checksum mismatch: expected {WEIGHTS_SHA256}, "
            f"received {actual_sha256}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / WEIGHTS_FILE
    shutil.copy2(downloaded, destination)
    metadata = {
        "model_version": "swiftformer-image-safety-m-v1",
        "base_checkpoint": REPOSITORY,
        "revision": REVISION,
        "backend": "timm-safetensors",
        "architecture": "swiftformer_l1",
        "weights_file": WEIGHTS_FILE,
        "weights_sha256": WEIGHTS_SHA256,
        "label_names": ["NSFL", "NSFW", "SFW"],
        "label_categories": {
            "NSFL": "graphic_violence",
            "NSFW": "sexual_content",
        },
        "input_size": 224,
        "interpolation": "bicubic",
        "crop_pct": 0.95,
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
        "license": "MIT",
    }
    metadata_path = args.output_dir / "sentinel_image_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Verified model saved to {args.output_dir}")
    print(f"SHA-256: {actual_sha256}")


if __name__ == "__main__":
    main()
