from sentinel.core.normalization import normalize_text


def test_normalizes_unicode_spacing_and_leetspeak() -> None:
    assert normalize_text("  K1LL\u200b   Y0U  ") == "kill you"


def test_reduces_character_flooding() -> None:
    assert normalize_text("heyyyyy") == "heyy"

