from dataclasses import dataclass, field


@dataclass(slots=True)
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)


class PhraseTrie:
    """Small multi-pattern matcher used as the first moderation layer.

    This milestone uses a trie to make the algorithm explicit. A future milestone
    upgrades it to Aho-Corasick failure links for linear-time multi-pattern scans.
    """

    def __init__(self, phrases: list[str]) -> None:
        self._root = TrieNode()
        for phrase in phrases:
            self._insert(phrase)

    def _insert(self, phrase: str) -> None:
        node = self._root
        for character in phrase:
            node = node.children.setdefault(character, TrieNode())
        node.outputs.append(phrase)

    def find(self, text: str) -> set[str]:
        matches: set[str] = set()
        for start in range(len(text)):
            node = self._root
            for character in text[start:]:
                node = node.children.get(character)
                if node is None:
                    break
                matches.update(node.outputs)
        return matches

