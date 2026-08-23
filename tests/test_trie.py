from sentinel.core.trie import PhraseTrie


def test_trie_returns_all_matching_phrases() -> None:
    matcher = PhraseTrie(["harm", "harmful", "safe"])

    assert matcher.find("harmful but safe") == {"harm", "harmful", "safe"}

