import base64
import struct

import pytest

from sentinel.multimodal.errors import (
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedImageError,
)
from sentinel.multimodal.image import decode_image
from sentinel.schemas.moderation import ImageMediaType

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def encoded_image() -> str:
    return base64.b64encode(PNG_BYTES).decode("ascii")


def test_decode_image_verifies_and_sanitizes_pixels() -> None:
    result = decode_image(encoded_image(), ImageMediaType.PNG)

    assert result.format == "PNG"
    assert (result.width, result.height) == (1, 1)
    assert result.data == PNG_BYTES
    assert result.bytes_received > 0


def test_decode_image_rejects_invalid_base64() -> None:
    with pytest.raises(InvalidImageError, match="Base64"):
        decode_image("not-valid-%%%", ImageMediaType.PNG)


def test_decode_image_rejects_declared_type_mismatch() -> None:
    with pytest.raises(UnsupportedImageError, match="does not match"):
        decode_image(encoded_image(), ImageMediaType.JPEG)


def test_decode_image_rejects_non_image_bytes() -> None:
    payload = base64.b64encode(b"this is not an image").decode("ascii")

    with pytest.raises(UnsupportedImageError, match="supported JPEG"):
        decode_image(payload, ImageMediaType.PNG)


def test_decode_image_reads_jpeg_frame_dimensions() -> None:
    jpeg = bytes.fromhex("ffd8ffc0000b080002000301011100")
    encoded = base64.b64encode(jpeg).decode("ascii")

    result = decode_image(encoded, ImageMediaType.JPEG)

    assert result.format == "JPEG"
    assert (result.width, result.height) == (3, 2)


def test_decode_image_reads_webp_extended_dimensions() -> None:
    webp = (
        b"RIFF"
        + (22).to_bytes(4, "little")
        + b"WEBPVP8X"
        + (10).to_bytes(4, "little")
        + b"\x00\x00\x00\x00"
        + (3).to_bytes(3, "little")
        + (1).to_bytes(3, "little")
    )
    encoded = base64.b64encode(webp).decode("ascii")

    result = decode_image(encoded, ImageMediaType.WEBP)

    assert (result.width, result.height) == (4, 2)


def test_decode_image_rejects_animated_webp() -> None:
    webp = (
        b"RIFF"
        + (22).to_bytes(4, "little")
        + b"WEBPVP8X"
        + (10).to_bytes(4, "little")
        + b"\x02\x00\x00\x00"
        + (1).to_bytes(3, "little")
        + (1).to_bytes(3, "little")
    )

    with pytest.raises(UnsupportedImageError, match="animated"):
        decode_image(base64.b64encode(webp).decode("ascii"), ImageMediaType.WEBP)


def test_decode_image_rejects_oversized_dimensions() -> None:
    png_header = (
        PNG_BYTES[:16]
        + struct.pack(">II", 9_000, 1)
        + PNG_BYTES[24:]
    )

    with pytest.raises(ImageTooLargeError, match="dimensions"):
        decode_image(base64.b64encode(png_header).decode("ascii"), ImageMediaType.PNG)
