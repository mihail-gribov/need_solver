"""
User profile for dog breed recommendation.

Represents user as a vector in needs space using 4-valued fuzzy logic.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from fuzzy4 import FuzzyBool

SCRIPT_DIR = Path(__file__).parent


@dataclass
class Answer:
    """Record of a single user answer."""
    need_id: str
    question_id: str  # unique ID of the question variant
    question_text: str
    answer_type: str  # true, false, unknown, independent
    fuzzy_value: FuzzyBool | None  # None for independent
    weight: float = 1.0  # confidence weight of this question


class UserProfile:
    """
    User profile as a vector in needs space.

    Each need can be:
    - Set with a FuzzyBool value (from user answer)
    - Independent (user doesn't care - excluded from matching)
    - Unset (not yet asked)

    Multiple answers to the same need are combined using fuzzy consensus.
    """

    def __init__(self, domain_dir: Path | str | None = None):
        if domain_dir is None:
            domain_dir = SCRIPT_DIR
        self.domain_dir = Path(domain_dir)

        # Load config
        with open(self.domain_dir / "config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.answer_options = self.config["questions"]["answer_options"]

        # Current state
        self._needs: dict[str, FuzzyBool] = {}  # need_id -> combined fuzzy value
        self._independent: set[str] = set()     # needs marked as "don't care"
        self._answers: list[Answer] = []        # history of all answers
        self._answer_counts: dict[str, int] = {}  # how many times each need was answered
        self._asked_questions: set[str] = set()  # question_ids that have been asked
        self._need_weights: dict[str, float] = {}  # accumulated weight per need

    def add_answer(
        self,
        need_id: str,
        answer_type: str,
        question_text: str = "",
        question_id: str = "",
        weight: float = 1.0
    ) -> None:
        """
        Add user's answer to a question.

        Args:
            need_id: The need this question was about
            answer_type: One of 'true', 'false', 'unknown', 'independent'
            question_text: The question that was asked (for history)
            question_id: Unique ID of the question variant
            weight: Confidence weight of this question (0.0-1.0)
        """
        if answer_type not in self.answer_options:
            raise ValueError(f"Invalid answer_type: {answer_type}. Must be one of {list(self.answer_options.keys())}")

        # Mark question as asked
        if question_id:
            self._asked_questions.add(question_id)

        option = self.answer_options[answer_type]
        mapping = option.get("fuzzy_mapping")

        if mapping is None:
            # Independent - user doesn't care about this need
            fuzzy_value = None
            self._independent.add(need_id)
            # Remove from active needs if was set
            self._needs.pop(need_id, None)
            self._need_weights.pop(need_id, None)
        else:
            # Apply weight to T and F values
            # Weight acts as confidence: lower weight = less certain answer
            base_t = mapping["t"]
            base_f = mapping["f"]
            weighted_t = base_t * weight
            weighted_f = base_f * weight
            fuzzy_value = FuzzyBool(weighted_t, weighted_f)
            # Remove from independent if was marked
            self._independent.discard(need_id)
            # Combine with existing value if any
            self._update_need(need_id, fuzzy_value, weight)

        # Record answer
        self._answers.append(Answer(
            need_id=need_id,
            question_id=question_id,
            question_text=question_text,
            answer_type=answer_type,
            fuzzy_value=fuzzy_value,
            weight=weight
        ))

    def _update_need(self, need_id: str, new_value: FuzzyBool, weight: float = 1.0) -> None:
        """
        Update need value, combining with existing if present.

        Uses fuzzy accumulation (+) with weight scaling.
        Multiple answers accumulate evidence: more confirmations → higher T,
        more refutations → higher F. Conflicting answers create CONFLICT state.
        """
        if need_id not in self._needs:
            # First answer for this need
            self._needs[need_id] = new_value
            self._need_weights[need_id] = weight
        else:
            # Combine with existing using fuzzy accumulation (+)
            # Accumulates evidence: multiple "yes" → stronger confirmation
            # Conflicting answers: "yes" + "no" → approaches CONFLICT (1,1)
            old = self._needs[need_id]
            self._needs[need_id] = old + new_value
            self._need_weights[need_id] += weight

        self._answer_counts[need_id] = self._answer_counts.get(need_id, 0) + 1

    def get_needs(self) -> dict[str, FuzzyBool]:
        """
        Get current needs vector for matching.

        Returns only needs that are set (not independent, not unset).
        """
        return dict(self._needs)

    def get_need(self, need_id: str) -> FuzzyBool | None:
        """Get value for a specific need, or None if not set/independent."""
        return self._needs.get(need_id)

    def is_independent(self, need_id: str) -> bool:
        """Check if user marked this need as independent (don't care)."""
        return need_id in self._independent

    def is_set(self, need_id: str) -> bool:
        """Check if need has a value (either set or independent)."""
        return need_id in self._needs or need_id in self._independent

    def get_unset_needs(self, all_need_ids: list[str]) -> list[str]:
        """Get list of needs that haven't been asked yet."""
        return [nid for nid in all_need_ids if not self.is_set(nid)]

    def get_answer_history(self) -> list[Answer]:
        """Get full history of answers."""
        return list(self._answers)

    def clear(self) -> None:
        """Reset profile to initial state."""
        self._needs.clear()
        self._independent.clear()
        self._answers.clear()
        self._answer_counts.clear()
        self._asked_questions.clear()
        self._need_weights.clear()

    def recompute_vector(self) -> None:
        """
        Recompute needs vector from raw answers.

        Useful after modifying answer history or changing aggregation logic.
        """
        self._needs.clear()
        self._independent.clear()
        self._answer_counts.clear()
        self._asked_questions.clear()
        self._need_weights.clear()

        for ans in self._answers:
            if ans.question_id:
                self._asked_questions.add(ans.question_id)

            if ans.fuzzy_value is None:
                # Independent
                self._independent.add(ans.need_id)
                self._needs.pop(ans.need_id, None)
                self._need_weights.pop(ans.need_id, None)
            else:
                self._independent.discard(ans.need_id)
                self._update_need(ans.need_id, ans.fuzzy_value, ans.weight)

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to dict."""
        return {
            "needs": {k: {"t": v.t, "f": v.f} for k, v in self._needs.items()},
            "need_weights": dict(self._need_weights),
            "independent": list(self._independent),
            "asked_questions": list(self._asked_questions),
            "answers": [
                {
                    "need_id": a.need_id,
                    "question_id": a.question_id,
                    "question_text": a.question_text,
                    "answer_type": a.answer_type,
                    "weight": a.weight,
                    "fuzzy_value": {"t": a.fuzzy_value.t, "f": a.fuzzy_value.f} if a.fuzzy_value else None
                }
                for a in self._answers
            ]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], domain_dir: Path | str | None = None) -> "UserProfile":
        """Deserialize profile from dict."""
        profile = cls(domain_dir)

        for need_id, val in data.get("needs", {}).items():
            profile._needs[need_id] = FuzzyBool(val["t"], val["f"])

        profile._need_weights = dict(data.get("need_weights", {}))
        profile._independent = set(data.get("independent", []))
        profile._asked_questions = set(data.get("asked_questions", []))

        for ans in data.get("answers", []):
            fv = ans.get("fuzzy_value")
            profile._answers.append(Answer(
                need_id=ans["need_id"],
                question_id=ans.get("question_id", ""),
                question_text=ans.get("question_text", ""),
                answer_type=ans["answer_type"],
                weight=ans.get("weight", 1.0),
                fuzzy_value=FuzzyBool(fv["t"], fv["f"]) if fv else None
            ))

        # Rebuild answer counts
        for ans in profile._answers:
            if ans.fuzzy_value is not None:
                profile._answer_counts[ans.need_id] = profile._answer_counts.get(ans.need_id, 0) + 1

        return profile

    def get_answered_need_ids(self) -> set[str]:
        """Get set of all need IDs that have been answered (including independent)."""
        return set(self._needs.keys()) | self._independent

    def is_question_asked(self, question_id: str) -> bool:
        """Check if a specific question variant has been asked."""
        return question_id in self._asked_questions

    def get_asked_questions(self) -> set[str]:
        """Get set of all asked question IDs."""
        return set(self._asked_questions)

    def get_need_confidence(self, need_id: str) -> float:
        """
        Get confidence for a need based on FuzzyBool value.

        Confidence = 1 - unknown component = 1 - (1-t)(1-f)
        - High confidence: we know something (either true or false)
        - Low confidence: uncertain (neither confirmed nor refuted)

        Returns 0.0 if need not set.
        """
        val = self._needs.get(need_id)
        if val is None:
            return 0.0
        # confidence = 1 - unknown = 1 - (1-t)(1-f)
        return 1.0 - (1.0 - val.t) * (1.0 - val.f)

    def get_need_total_weight(self, need_id: str) -> float:
        """Get total weight of all questions answered for this need."""
        return self._need_weights.get(need_id, 0.0)

    def get_unanswered_questions(self, need_id: str, all_questions: list[dict]) -> list[dict]:
        """
        Get questions for a need that haven't been asked yet.

        Args:
            need_id: The need to get questions for
            all_questions: List of question dicts with 'id' field

        Returns:
            List of question dicts that haven't been asked
        """
        return [q for q in all_questions if q.get("id") not in self._asked_questions]

    def __repr__(self) -> str:
        return f"UserProfile(needs={len(self._needs)}, independent={len(self._independent)}, answers={len(self._answers)})"


# CLI for testing
if __name__ == "__main__":
    profile = UserProfile()

    # Simulate answering questions with weights
    print("Simulating user answers with weights...\n")

    # High-weight direct question
    profile.add_answer("hypoallergenic", "true", "Кто-то в семье страдает астмой?",
                       question_id="hypo_q1_asthma", weight=0.95)

    # Low-weight indirect questions for same need
    profile.add_answer("hypoallergenic", "true", "Вы часто носите тёмную одежду?",
                       question_id="hypo_q2_dark_clothes", weight=0.4)

    profile.add_answer("apartment_compatible", "true", "Вы живёте в многоквартирном доме?",
                       question_id="apt_q1_building", weight=0.9)

    profile.add_answer("child_friendly", "true", "В семье есть дети до 7 лет?",
                       question_id="child_q1_age", weight=0.85)

    profile.add_answer("guard_role", "independent", "Ваш дом на отшибе?",
                       question_id="guard_q1_remote", weight=0.7)

    print(f"Profile: {profile}")
    print(f"\nNeeds vector ({len(profile.get_needs())} active):")
    for need_id, val in profile.get_needs().items():
        confidence = profile.get_need_confidence(need_id)
        print(f"  {need_id}: t={val.t:.2f}, f={val.f:.2f} (conf={confidence:.2f})")

    print(f"\nIndependent: {profile._independent}")
    print(f"Asked questions: {profile.get_asked_questions()}")

    print(f"\nAnswer history:")
    for ans in profile.get_answer_history():
        print(f"  [{ans.answer_type}] {ans.need_id} (w={ans.weight}): {ans.question_text[:40]}...")

    # Test with matcher
    print("\n--- Testing with Matcher ---")
    from matcher import BreedMatcher

    matcher = BreedMatcher()
    results = matcher.match_fast(profile.get_needs(), top_k=5)

    print(f"\nTop 5 matches:")
    for breed_id, score in results:
        print(f"  {breed_id}: {score}")
