import re
import unicodedata

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
_WHITESPACE = re.compile(r"\s+")
_REPEATED_CHARACTERS = re.compile(r"(.)\1{2,}")
_INTRA_WORD_PUNCTUATION = re.compile(
    r"(?<=[^\W\d_])(?:[^\w\s]|_)+(?=[^\W\d_])",
    flags=re.UNICODE,
)
_LEETSPEAK = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
    }
)

NORMALIZATION_VERSION = "sentinel-normalization-v2"


def normalize_text(text: str) -> str:
    """Return a deterministic representation used by the heuristic layer."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = _ZERO_WIDTH.sub("", normalized)
    normalized = normalized.translate(_LEETSPEAK)
    normalized = _INTRA_WORD_PUNCTUATION.sub("", normalized)
    normalized = _REPEATED_CHARACTERS.sub(r"\1", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()
