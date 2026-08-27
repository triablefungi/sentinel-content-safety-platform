import base64
import binascii
import struct
from dataclasses import dataclass

from sentinel.multimodal.errors import (
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedImageError,
)
from sentinel.schemas.moderation import ImageMediaType

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGE_DIMENSION = 8_192
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_START_OF_FRAME = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    data: bytes
    format: str
    width: int
    height: int
    bytes_received: int


def _png_metadata(payload: bytes) -> tuple[int, int, bool] | None:
    if not payload.startswith(_PNG_SIGNATURE):
        return None
    if len(payload) < 33 or payload[12:16] != b"IHDR":
        raise InvalidImageError("PNG is missing a valid IHDR chunk")
    width, height = struct.unpack(">II", payload[16:24])
    return width, height, b"acTL" in payload


def _jpeg_metadata(payload: bytes) -> tuple[int, int, bool] | None:
    if not payload.startswith(b"\xff\xd8"):
        return None
    position = 2
    while position + 4 <= len(payload):
        if payload[position] != 0xFF:
            position += 1
            continue
        while position < len(payload) and payload[position] == 0xFF:
            position += 1
        if position >= len(payload):
            break
        marker = payload[position]
        position += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if position + 2 > len(payload):
            break
        segment_length = int.from_bytes(payload[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > len(payload):
            raise InvalidImageError("JPEG contains an invalid segment")
        if marker in _JPEG_START_OF_FRAME:
            if segment_length < 7:
                raise InvalidImageError("JPEG frame header is incomplete")
            height = int.from_bytes(payload[position + 3 : position + 5], "big")
            width = int.from_bytes(payload[position + 5 : position + 7], "big")
            return width, height, False
        position += segment_length
    raise InvalidImageError("JPEG dimensions could not be determined")


def _webp_metadata(payload: bytes) -> tuple[int, int, bool] | None:
    if len(payload) < 30 or payload[:4] != b"RIFF" or payload[8:12] != b"WEBP":
        return None
    chunk = payload[12:16]
    if chunk == b"VP8X":
        flags = payload[20]
        width = 1 + int.from_bytes(payload[24:27], "little")
        height = 1 + int.from_bytes(payload[27:30], "little")
        return width, height, bool(flags & 0x02)
    if chunk == b"VP8L":
        if payload[20] != 0x2F:
            raise InvalidImageError("WebP lossless header is invalid")
        bits = int.from_bytes(payload[21:25], "little")
        width = 1 + (bits & 0x3FFF)
        height = 1 + ((bits >> 14) & 0x3FFF)
        return width, height, False
    if chunk == b"VP8 ":
        if payload[23:26] != b"\x9d\x01\x2a":
            raise InvalidImageError("WebP frame header is invalid")
        width = int.from_bytes(payload[26:28], "little") & 0x3FFF
        height = int.from_bytes(payload[28:30], "little") & 0x3FFF
        return width, height, False
    raise InvalidImageError("WebP uses an unsupported encoding")


def _inspect(payload: bytes) -> tuple[str, int, int, bool]:
    inspectors = (
        ("PNG", _png_metadata),
        ("JPEG", _jpeg_metadata),
        ("WEBP", _webp_metadata),
    )
    for format_name, inspector in inspectors:
        metadata = inspector(payload)
        if metadata is not None:
            width, height, animated = metadata
            return format_name, width, height, animated
    raise UnsupportedImageError("payload is not a supported JPEG, PNG, or WebP image")


def decode_image(image_base64: str, declared_media_type: ImageMediaType) -> ValidatedImage:
    """Decode Base64 and validate signature, type, dimensions, and animation flags."""
    try:
        payload = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise InvalidImageError("image_base64 is not valid Base64") from error
    if not payload:
        raise InvalidImageError("decoded image is empty")
    if len(payload) > MAX_IMAGE_BYTES:
        raise ImageTooLargeError(f"image exceeds {MAX_IMAGE_BYTES} bytes")

    actual_format, width, height, animated = _inspect(payload)
    expected_format = {
        ImageMediaType.JPEG: "JPEG",
        ImageMediaType.PNG: "PNG",
        ImageMediaType.WEBP: "WEBP",
    }[declared_media_type]
    if actual_format != expected_format:
        raise UnsupportedImageError("declared media type does not match the image signature")
    if animated:
        raise UnsupportedImageError("animated images are not supported")
    if width <= 0 or height <= 0:
        raise InvalidImageError("image dimensions must be positive")
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ImageTooLargeError("image dimensions exceed the safe limit")
    if width * height > MAX_IMAGE_PIXELS:
        raise ImageTooLargeError("image exceeds the safe decoded-pixel limit")

    return ValidatedImage(
        data=payload,
        format=actual_format,
        width=width,
        height=height,
        bytes_received=len(payload),
    )
