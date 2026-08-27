import re
from collections.abc import Callable

Attack = Callable[[str], str]


def clean(text: str) -> str:
    return text


def uppercase(text: str) -> str:
    return text.upper()


def zero_width(text: str) -> str:
    """Insert invisible separators inside alphabetic words."""
    return re.sub(r"(?<=[A-Za-z])(?=[A-Za-z])", "\u200b", text)


def leetspeak(text: str) -> str:
    return text.translate(str.maketrans({"a": "4", "e": "3", "i": "1", "o": "0", "s": "5"}))


def punctuation_injection(text: str) -> str:
    """Insert punctuation inside words while preserving readability."""
    return re.sub(r"(?<=[A-Za-z])(?=[A-Za-z])", ".", text)


def character_flooding(text: str) -> str:
    """Repeat the first internal vowel in each eligible word."""

    def flood(match: re.Match[str]) -> str:
        word = match.group(0)
        for index, character in enumerate(word[1:-1], 1):
            if character.casefold() in "aeiou":
                return f"{word[:index]}{character * 3}{word[index + 1:]}"
        return word

    return re.sub(r"[A-Za-z]{4,}", flood, text)


ATTACKS: dict[str, Attack] = {
    "clean": clean,
    "uppercase": uppercase,
    "zero_width": zero_width,
    "leetspeak": leetspeak,
    "punctuation": punctuation_injection,
    "character_flooding": character_flooding,
}
