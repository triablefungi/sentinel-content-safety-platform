from sentinel.evaluation.attacks import (
    character_flooding,
    leetspeak,
    punctuation_injection,
    uppercase,
    zero_width,
)


def test_attacks_are_deterministic_and_distinct() -> None:
    text = "You are awful"

    assert uppercase(text) == "YOU ARE AWFUL"
    assert zero_width(text) == "Y\u200bo\u200bu a\u200br\u200be a\u200bw\u200bf\u200bu\u200bl"
    assert leetspeak(text) == "Y0u 4r3 4wful"
    assert punctuation_injection(text) == "Y.o.u a.r.e a.w.f.u.l"
    assert character_flooding(text) == "You are awfuuul"


def test_attacks_do_not_remove_content() -> None:
    text = "No"

    assert zero_width(text).replace("\u200b", "") == text
    assert punctuation_injection(text).replace(".", "") == text
