from dataclasses import dataclass

from sentinel.core.trie import PhraseTrie
from sentinel.schemas.moderation import SafetyCategory


@dataclass(frozen=True, slots=True)
class SafetyRule:
    phrase: str
    category: SafetyCategory
    severity: float
    reason_code: str


DEFAULT_RULES = (
    SafetyRule("kill you", SafetyCategory.THREAT, 0.95, "explicit_threat"),
    SafetyRule("attack them", SafetyCategory.THREAT, 0.90, "violent_intent"),
    SafetyRule("you are worthless", SafetyCategory.HARASSMENT, 0.65, "targeted_abuse"),
    SafetyRule(
        "people like you do not belong",
        SafetyCategory.IDENTITY_ATTACK,
        0.85,
        "exclusionary_attack",
    ),
)


class RuleEngine:
    def __init__(self, rules: tuple[SafetyRule, ...]) -> None:
        self._rules = {rule.phrase: rule for rule in rules}
        self._matcher = PhraseTrie(list(self._rules))

    def evaluate(self, normalized_text: str) -> list[SafetyRule]:
        return [self._rules[phrase] for phrase in sorted(self._matcher.find(normalized_text))]

