from sentinel.core.normalization import normalize_text


def test_normalizes_unicode_spacing_and_leetspeak() -> None:
    assert normalize_text("  K1LL\u200b   Y0U  ") == "kill you"


def test_reduces_character_flooding() -> None:
    assert normalize_text("heyyyyy") == "hey"


def test_removes_punctuation_inserted_inside_words() -> None:
    assert normalize_text("k.i_l-l y.o.u") == "kill you"


def test_preserves_punctuation_at_word_boundaries() -> None:
    assert normalize_text("hello, world!") == "hello, world!"
