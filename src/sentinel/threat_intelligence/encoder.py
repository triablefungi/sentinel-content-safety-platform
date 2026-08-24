import hashlib
import math

from sentinel.core.normalization import normalize_text


class HashedNgramEncoder:
    """Dependency-light character n-gram vectors for adversarial near duplicates."""

    def __init__(self, dimension: int = 384, min_n: int = 3, max_n: int = 5) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._dimension = dimension
        self._min_n = min_n
        self._max_n = max_n

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def version(self) -> str:
        return "hashed-char-ngram-v1"

    def encode(self, text: str) -> list[float]:
        normalized = f" {normalize_text(text)} "
        vector = [0.0] * self._dimension
        for size in range(self._min_n, self._max_n + 1):
            for start in range(max(0, len(normalized) - size + 1)):
                token = normalized[start : start + size].encode("utf-8")
                digest = hashlib.blake2b(token, digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "big") % self._dimension
                sign = 1.0 if digest[4] & 1 else -1.0
                vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [value / norm for value in vector]
        return vector
