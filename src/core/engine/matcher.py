"""
Core matching engine for object recommendation.

Calculates match scores between user needs and object characteristics
using 4-valued fuzzy logic (fuzzy4).
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from fuzzy4 import FuzzyBool


@dataclass
class MatchResult:
    """Result of matching an object against user needs."""
    object_id: str
    score: float  # 0.0 to 1.0, higher = better match
    details: dict[str, dict]  # need_id -> {user, object, similarity}


class Matcher:
    """
    Core matching engine.

    Pre-loads all data for fast matching operations.
    Domain-agnostic: requires domain_dir with config.json.
    """

    # Default domain path (relative to this file)
    DEFAULT_DOMAIN = Path(__file__).parent.parent.parent.parent / "domains" / "dog_breeds"

    def __init__(self, domain_dir: Path | str | None = None):
        if domain_dir is None:
            domain_dir = self.DEFAULT_DOMAIN
        self.domain_dir = Path(domain_dir)

        # Load config
        with open(self.domain_dir / "config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)

        # Pre-load all data
        self._load_needs()
        self._load_breeds()
        self._precompute_matrix()

    def _load_needs(self):
        """Load and pre-compile user needs formulas."""
        needs_file = self.domain_dir / self.config["paths"]["content"] / "user_needs.json"
        with open(needs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.needs: dict[str, dict] = {}
        self.compiled_formulas: dict[str, Any] = {}  # Pre-compiled code objects

        for need in data["needs"]:
            need_id = need["id"]
            self.needs[need_id] = need
            # Pre-compile formula for fast eval
            self.compiled_formulas[need_id] = compile(need["formula"], f"<{need_id}>", "eval")

    def _load_features(self) -> list[str]:
        """Load list of all feature IDs from object_features.json."""
        features_file = self.domain_dir / self.config["paths"]["content"] / "object_features.json"
        with open(features_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        feature_ids = []
        for feat in data.get("features", []):
            feature_ids.append(feat["id"])

        # Also collect category IDs
        for group_name in ["size_group", "height_group", "lifespan_group"]:
            if group_name in data:
                for cat in data[group_name].get("values", []):
                    feature_ids.append(cat["id"])
                for derived in data[group_name].get("derived", []):
                    feature_ids.append(derived["id"])

        return feature_ids

    def _load_breeds(self):
        """Load all breed fuzzy data."""
        fuzzy_dir = self.domain_dir / self.config["paths"]["fuzzy"]

        # Get all known feature IDs for default UNKNOWN values
        all_feature_ids = self._load_features()
        UNKNOWN = FuzzyBool(0, 0)

        self.breeds: dict[str, dict] = {}
        self.breed_contexts: dict[str, dict[str, FuzzyBool]] = {}

        for fpath in fuzzy_dir.glob("*.json"):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            breed_id = data["breed_id"]
            self.breeds[breed_id] = data

            # Build evaluation context (all variables as FuzzyBool)
            # Start with UNKNOWN for all features
            context = {feat_id: UNKNOWN for feat_id in all_feature_ids}

            # Add features from data (overwrites UNKNOWN)
            for feat_id, feat_data in data.get("features", {}).items():
                context[feat_id] = FuzzyBool(feat_data["t"], feat_data["f"])

            # Add category values
            for group_id, group_data in data.get("categories", {}).items():
                for cat_id, cat_data in group_data.get("values", {}).items():
                    context[cat_id] = FuzzyBool(cat_data["t"], cat_data["f"])

            self.breed_contexts[breed_id] = context

    def _precompute_matrix(self):
        """Pre-compute all (breed × need) evaluations."""
        self.eval_matrix: dict[str, dict[str, FuzzyBool]] = {}

        for breed_id, context in self.breed_contexts.items():
            self.eval_matrix[breed_id] = {}
            for need_id, code in self.compiled_formulas.items():
                self.eval_matrix[breed_id][need_id] = eval(code, {"__builtins__": {}}, context)

    def evaluate_need(
        self,
        breed_id: str,
        need_id: str
    ) -> FuzzyBool:
        """
        Get pre-computed need evaluation for a breed. O(1) lookup.
        """
        return self.eval_matrix[breed_id][need_id]

    def compute_match(
        self,
        user_value: FuzzyBool,
        breed_value: FuzzyBool
    ) -> FuzzyBool:
        """
        Compute fuzzy match between user's need and breed's characteristic.

        Returns FuzzyBool representing how well the breed satisfies the need.
        Uses fuzzy equivalence (iff): user ↔ breed
        """
        # Fuzzy equivalence: (user → breed) & (breed → user)
        return user_value.iff(breed_value)

    def match_breed(
        self,
        breed_id: str,
        user_needs: dict[str, FuzzyBool],
        equal_weights: bool = False
    ) -> MatchResult:
        """
        Match a single breed against user needs.

        Args:
            breed_id: The breed to evaluate
            user_needs: Dict of need_id -> FuzzyBool (user's desired value)
                       Only include needs that are set (not independent)
            equal_weights: If True, all needs have weight=1 (ignore user confidence)

        Returns:
            MatchResult with overall score and per-need details
        """
        if not user_needs:
            # No needs specified - neutral match
            return MatchResult(breed_id=breed_id, score=0.0, details={})

        details = {}
        match_scores = []

        for need_id, user_value in user_needs.items():
            breed_value = self.evaluate_need(breed_id, need_id)

            user_score = user_value.t - user_value.f
            breed_score = breed_value.t - breed_value.f

            # Match via multiplication
            match = user_score * breed_score
            weight = 1.0 if equal_weights else abs(user_score)

            details[need_id] = {
                "user": {"t": user_value.t, "f": user_value.f, "score": round(user_score, 3)},
                "breed": {"t": round(breed_value.t, 3), "f": round(breed_value.f, 3), "score": round(breed_score, 3)},
                "match": round(match, 3),
                "weight": round(weight, 3)
            }

            match_scores.append((match, weight))

        # Weighted average
        total_weight = sum(w for _, w in match_scores)
        if total_weight > 0:
            score = sum(m * w for m, w in match_scores) / total_weight
        else:
            score = 0.0

        return MatchResult(
            breed_id=breed_id,
            score=round(score, 3),
            details=details
        )

    def match_all(
        self,
        user_needs: dict[str, FuzzyBool],
        top_k: int | None = None,
        equal_weights: bool = False
    ) -> list[MatchResult]:
        """
        Match all breeds against user needs.

        Args:
            user_needs: Dict of need_id -> FuzzyBool
            top_k: If set, return only top K results
            equal_weights: If True, all needs have weight=1

        Returns:
            List of MatchResult sorted by score descending
        """
        results = []

        for breed_id in self.breeds:
            result = self.match_breed(breed_id, user_needs, equal_weights=equal_weights)
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        if top_k:
            results = results[:top_k]

        return results

    def match_fast(
        self,
        user_needs: dict[str, FuzzyBool],
        breed_ids: list[str] | None = None,
        top_k: int | None = None,
        equal_weights: bool = False
    ) -> list[tuple[str, float]]:
        """
        Fast batch matching - returns only (breed_id, score) pairs.

        Uses fuzzy AND to combine matches across all needs.
        Score = T - F of the combined fuzzy match.

        Args:
            user_needs: Dict of need_id -> FuzzyBool
            breed_ids: List of breeds to evaluate (None = all)
            top_k: Return only top K results
            equal_weights: If True, all needs have weight=1 (ignore user confidence)
        """
        if breed_ids is None:
            breed_ids = list(self.breeds.keys())

        if not user_needs:
            return [(bid, 0.0) for bid in breed_ids]

        need_ids = list(user_needs.keys())
        user_values = [user_needs[nid] for nid in need_ids]

        scores = []

        for breed_id in breed_ids:
            breed_row = self.eval_matrix[breed_id]
            match_scores = []

            for i, need_id in enumerate(need_ids):
                breed_val = breed_row[need_id]
                user_val = user_values[i]

                # T-F score comparison
                user_score = user_val.t - user_val.f
                breed_score = breed_val.t - breed_val.f

                # Match via multiplication:
                # user=+1, breed=+1 → +1 (want and have = good)
                # user=+1, breed=-1 → -1 (want but don't have = bad)
                # user=-1, breed=+1 → -1 (don't want but have = bad)
                # user=-1, breed=-1 → +1 (don't want and don't have = good)
                match = user_score * breed_score

                # Weight by user's confidence (how strongly they care)
                weight = 1.0 if equal_weights else abs(user_score)
                match_scores.append((match, weight))

            # Weighted average of match scores
            total_weight = sum(w for _, w in match_scores)
            if total_weight > 0:
                score = sum(m * w for m, w in match_scores) / total_weight
            else:
                score = 0.0

            scores.append((breed_id, round(score, 3)))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        if top_k:
            scores = scores[:top_k]

        return scores

    # Alias for backwards compatibility
    match_all_fast = match_fast

    def select_next_question(
        self,
        current_needs: dict[str, FuzzyBool],
        answered_needs: set[str] | None = None,
        equal_weights: bool = False
    ) -> tuple[str, float]:
        """
        Select the next best question to ask.

        Uses expected split quality: finds the need where answering
        TRUE vs FALSE produces the most different rankings.

        Args:
            current_needs: Current user needs vector
            answered_needs: Set of already answered need IDs (to skip)
            equal_weights: If True, all needs have weight=1

        Returns:
            (best_need_id, split_score)
        """
        if answered_needs is None:
            answered_needs = set(current_needs.keys())

        # Get unanswered needs
        all_need_ids = list(self.needs.keys())
        unanswered = [nid for nid in all_need_ids if nid not in answered_needs]

        if not unanswered:
            return None, 0.0

        best_need = None
        best_split = -1.0

        breed_ids = list(self.breeds.keys())
        n_breeds = len(breed_ids)

        for need_id in unanswered:
            # Simulate answer = TRUE
            needs_true = {**current_needs, need_id: FuzzyBool(1, 0)}
            scores_true = self._compute_scores_array(needs_true, breed_ids, equal_weights)

            # Simulate answer = FALSE
            needs_false = {**current_needs, need_id: FuzzyBool(0, 1)}
            scores_false = self._compute_scores_array(needs_false, breed_ids, equal_weights)

            # Split quality = mean absolute difference
            # Higher = answer matters more = better question
            split_score = sum(abs(scores_true[i] - scores_false[i]) for i in range(n_breeds)) / n_breeds

            if split_score > best_split:
                best_split = split_score
                best_need = need_id

        return best_need, round(best_split, 4)

    def _compute_scores_array(
        self,
        user_needs: dict[str, FuzzyBool],
        breed_ids: list[str],
        equal_weights: bool = False
    ) -> list[float]:
        """
        Compute scores for breeds as a list (for batch comparison).

        Uses fuzzy AND to combine matches. Score = T - F.
        Internal method optimized for split quality calculation.
        """
        if not user_needs:
            return [0.0] * len(breed_ids)

        need_ids = list(user_needs.keys())
        user_values = [(user_needs[nid].t, user_needs[nid].f) for nid in need_ids]

        scores = []
        for breed_id in breed_ids:
            breed_row = self.eval_matrix[breed_id]
            match_scores = []

            for i, need_id in enumerate(need_ids):
                breed_val = breed_row[need_id]
                user_t, user_f = user_values[i]

                user_score = user_t - user_f
                breed_score = breed_val.t - breed_val.f

                # Match via multiplication
                match = user_score * breed_score
                weight = 1.0 if equal_weights else abs(user_score)
                match_scores.append((match, weight))

            total_weight = sum(w for _, w in match_scores)
            if total_weight > 0:
                score = sum(m * w for m, w in match_scores) / total_weight
            else:
                score = 0.0

            scores.append(score)

        return scores

    def get_question_rankings(
        self,
        current_needs: dict[str, FuzzyBool],
        answered_needs: set[str] | None = None,
        top_k: int | None = None,
        equal_weights: bool = False
    ) -> list[tuple[str, float]]:
        """
        Rank all unanswered questions by their split quality.

        Returns list of (need_id, split_score) sorted by score descending.
        """
        if answered_needs is None:
            answered_needs = set(current_needs.keys())

        all_need_ids = list(self.needs.keys())
        unanswered = [nid for nid in all_need_ids if nid not in answered_needs]

        breed_ids = list(self.breeds.keys())
        n_breeds = len(breed_ids)

        rankings = []

        for need_id in unanswered:
            needs_true = {**current_needs, need_id: FuzzyBool(1, 0)}
            scores_true = self._compute_scores_array(needs_true, breed_ids, equal_weights)

            needs_false = {**current_needs, need_id: FuzzyBool(0, 1)}
            scores_false = self._compute_scores_array(needs_false, breed_ids, equal_weights)

            split_score = sum(abs(scores_true[i] - scores_false[i]) for i in range(n_breeds)) / n_breeds
            rankings.append((need_id, round(split_score, 4)))

        rankings.sort(key=lambda x: x[1], reverse=True)

        if top_k:
            rankings = rankings[:top_k]

        return rankings

    def get_breed_ids(self) -> list[str]:
        """Get list of all available breed IDs."""
        return list(self.breeds.keys())

    def get_need_ids(self) -> list[str]:
        """Get list of all available need IDs."""
        return list(self.needs.keys())


# Backward compatibility alias
BreedMatcher = Matcher


# Convenience functions for quick usage

_default_matcher: BreedMatcher | None = None

def get_matcher() -> BreedMatcher:
    """Get or create default matcher instance (singleton)."""
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = BreedMatcher()
    return _default_matcher


def match(
    user_needs: dict[str, tuple[float, float] | FuzzyBool],
    top_k: int | None = None,
    equal_weights: bool = False
) -> list[MatchResult]:
    """
    Quick match function.

    Args:
        user_needs: Dict of need_id -> (t, f) tuple or FuzzyBool
        top_k: Return only top K results
        equal_weights: If True, all needs have weight=1

    Returns:
        List of MatchResult sorted by score
    """
    matcher = get_matcher()

    # Convert tuples to FuzzyBool
    fb_needs = {}
    for need_id, value in user_needs.items():
        if isinstance(value, FuzzyBool):
            fb_needs[need_id] = value
        else:
            fb_needs[need_id] = FuzzyBool(value[0], value[1])

    return matcher.match_all(fb_needs, top_k=top_k, equal_weights=equal_weights)


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test breed matcher")
    parser.add_argument("--need", "-n", action="append", help="Need in format 'id:t,f' e.g. 'hypoallergenic:1,0'")
    parser.add_argument("--top", "-k", type=int, default=10, help="Show top K results")
    parser.add_argument("--breed", "-b", help="Show details for specific breed")
    parser.add_argument("--equal-weights", "-e", action="store_true", help="Use equal weights (1) for all needs")

    args = parser.parse_args()

    matcher = BreedMatcher()

    if args.breed and not args.need:
        # Show all need evaluations for a breed
        print(f"Breed: {args.breed}\n")
        for need_id in matcher.get_need_ids():
            result = matcher.evaluate_need(args.breed, need_id)
            print(f"  {need_id}: t={result.t:.3f}, f={result.f:.3f} ({result.dominant_state()})")

    elif args.need:
        # Parse needs
        user_needs = {}
        for n in args.need:
            parts = n.split(":")
            need_id = parts[0]
            if len(parts) > 1:
                t, f = map(float, parts[1].split(","))
            else:
                t, f = 1.0, 0.0  # Default to TRUE
            user_needs[need_id] = FuzzyBool(t, f)

        print(f"User needs: {list(user_needs.keys())}\n")

        if args.breed:
            # Match single breed
            result = matcher.match_breed(args.breed, user_needs, equal_weights=args.equal_weights)
            print(f"Breed: {result.breed_id}")
            print(f"Score: {result.score}")
            print(f"Equal weights: {args.equal_weights}")
            print("\nDetails:")
            for need_id, detail in result.details.items():
                print(f"  {need_id}:")
                print(f"    User:  t={detail['user']['t']}, f={detail['user']['f']}")
                print(f"    Breed: t={detail['breed']['t']}, f={detail['breed']['f']}")
                print(f"    Match: {detail['match']}, Weight: {detail['weight']}")
        else:
            # Match all
            results = matcher.match_all(user_needs, top_k=args.top, equal_weights=args.equal_weights)
            mode = "equal" if args.equal_weights else "weighted"
            print(f"Top {args.top} matches ({mode} mode):\n")
            for i, r in enumerate(results, 1):
                print(f"{i:2}. {r.breed_id}: {r.score:.3f}")

    else:
        print(f"Loaded {len(matcher.breeds)} breeds, {len(matcher.needs)} needs")
        print("\nUsage examples:")
        print("  python matcher.py --breed labrador-retriever")
        print("  python matcher.py --need hypoallergenic --need apartment_compatible --top 10")
        print("  python matcher.py --need hypoallergenic:1,0 --breed poodle")
        print("  python matcher.py --need hypoallergenic --need low_barking -e  # equal weights mode")
