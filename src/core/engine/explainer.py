"""
Explanation generator for breed recommendations.

Uses LLM (OSS-120B via Nebius API) to generate human-friendly explanations
of why a particular breed matches user's needs.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from .matcher import BreedMatcher
from ..models.user_profile import UserProfile


# Blocks that represent hard constraints (facts about user's situation)
# vs soft preferences (what user would like)
CONSTRAINT_BLOCKS = {"size_constraints", "housing_environment"}

# Paths (relative to this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DOMAIN_DIR = PROJECT_ROOT / "domains" / "dog_breeds"
DATA_DIR = PROJECT_ROOT / "data"


def load_config() -> dict:
    """Load domain config."""
    with open(DOMAIN_DIR / "config.json", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class UserNeed:
    """A single user need/requirement."""
    need_id: str
    need_name: str
    user_wants: bool  # True = user wants this, False = user doesn't need this
    is_constraint: bool  # True = constraint (size, housing), False = preference
    score_0_9: int = 0  # Normalized importance score (0-9)


@dataclass
class BreedRecommendation:
    """Data for a single breed recommendation."""
    breed_id: str
    breed_name: str
    score: float
    score_0_9: int = 0  # Normalized match score (0-9)
    # How breed matches EACH user need (same order as ExplanationData.user_needs)
    # [{"need_name": str, "is_match": bool, "score_0_9": int, "components": {...}}, ...]
    need_matches: list[dict] = None


@dataclass
class ExplanationData:
    """Data prepared for LLM explanation generation."""
    # User's clearest needs - the basis for explanation
    user_needs: list[UserNeed]
    # Top breeds with matches for each user need
    breeds: list[BreedRecommendation]


def normalize_to_0_9(value: float, min_val: float, max_val: float) -> int:
    """Normalize a value to 0-9 scale."""
    if max_val == min_val:
        return 5  # Neutral if no range
    normalized = (value - min_val) / (max_val - min_val)
    return max(0, min(9, int(normalized * 9 + 0.5)))


def normalize_scores_0_9(scores: list[float]) -> list[int]:
    """Normalize a list of scores to 0-9 scale."""
    if not scores:
        return []
    min_val = min(scores)
    max_val = max(scores)
    return [normalize_to_0_9(s, min_val, max_val) for s in scores]


def load_breed_names() -> dict[str, str]:
    """Load breed ID to Russian name mapping."""
    breeds_file = DOMAIN_DIR / "content" / "breeds.json"
    with open(breeds_file) as f:
        data = json.load(f)
    return {b["id"]: b["name_ru"] for b in data["breeds"]}


def load_needs_info() -> dict[str, dict]:
    """Load need ID to info mapping (name, block, formula)."""
    needs_file = DOMAIN_DIR / "content" / "user_needs.json"
    with open(needs_file) as f:
        data = json.load(f)
    return {
        n["id"]: {"name": n["name"], "block": n["block"], "formula": n["formula"]}
        for n in data["needs"]
    }


def extract_formula_variables(formula: str) -> list[str]:
    """Extract variable names from a formula string."""
    import re
    # Remove operators and parentheses, get variable names
    # Variables are identifiers like: apartment_ok, barking, size_small
    variables = re.findall(r'[a-z_][a-z0-9_]*', formula)
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for v in variables:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def load_profile(filepath: str | Path | None = None) -> UserProfile:
    """
    Load user profile from JSON file.

    Args:
        filepath: Path to profile JSON file. If None, loads latest interview result.

    Returns:
        UserProfile instance
    """
    if filepath is None:
        filepath = DATA_DIR / "interview_latest.json"
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Profile not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    return UserProfile.from_dict(data)


def collect_explanation_data(
    profile: UserProfile,
    matcher: BreedMatcher,
    top_k: int = 3,
    max_constraints: int = 3,
    max_preferences: int = 4,
    min_need_score: int = 3
) -> ExplanationData:
    """
    Collect data for explanation from user profile and matcher results.

    Args:
        profile: User profile with answered needs
        matcher: Breed matcher instance
        top_k: Number of top breeds to include (default 3)
        max_constraints: Max constraint needs to include (default 3)
        max_preferences: Max preference needs to include (default 4)

    Returns:
        ExplanationData ready for prompt generation
    """
    breed_names = load_breed_names()
    needs_info = load_needs_info()

    user_needs_raw = profile.get_needs()
    results = matcher.match_fast(user_needs_raw, top_k=top_k)

    if not results:
        raise ValueError("No matching breeds found")

    # Analyze ALL user's answers (for proper normalization)
    user_analysis = []
    for need_id, user_val in user_needs_raw.items():
        info = needs_info.get(need_id, {"name": need_id, "block": "unknown"})
        user_score = user_val.t - user_val.f
        certainty = abs(user_score)
        consistency = 1 - min(user_val.t, user_val.f)

        user_analysis.append({
            "need_id": need_id,
            "need_name": info["name"],
            "block": info["block"],
            "is_constraint": info["block"] in CONSTRAINT_BLOCKS,
            "user_wants": user_score > 0,
            "user_score": user_score,
            "certainty": certainty,
            "consistency": consistency,
            "clarity": certainty * consistency
        })

    # Normalize clarity scores across ALL user needs (not just filtered)
    all_clarities = [n["clarity"] for n in user_analysis]
    all_scores_0_9 = normalize_scores_0_9(all_clarities)

    # Add normalized scores to analysis
    for i, n in enumerate(user_analysis):
        n["score_0_9"] = all_scores_0_9[i] if i < len(all_scores_0_9) else 5

    # Filter to clear needs only (high certainty, low contradiction, high score)
    clear_needs = [
        n for n in user_analysis
        if n["consistency"] > 0.7 and n["certainty"] > 0.5 and n["score_0_9"] >= min_need_score
    ]
    clear_needs.sort(key=lambda x: x["clarity"], reverse=True)

    # Split into constraints and preferences, take top of each
    clear_constraints = [n for n in clear_needs if n["is_constraint"]][:max_constraints]
    clear_preferences = [n for n in clear_needs if not n["is_constraint"]][:max_preferences]

    # Combine into single list of needs to explain (constraints first, then preferences)
    needs_to_explain = clear_constraints + clear_preferences

    # Create UserNeed objects with normalized scores
    user_needs = [
        UserNeed(
            need_id=n["need_id"],
            need_name=n["need_name"],
            user_wants=n["user_wants"],
            is_constraint=n["is_constraint"],
            score_0_9=n["score_0_9"]
        )
        for n in needs_to_explain
    ]

    # Get ALL breed scores for proper normalization (not just top_k)
    all_results = matcher.match_fast(user_needs_raw, top_k=None)
    all_breed_scores = [score for _, score in all_results]

    # Create mapping from breed_id to normalized score
    all_breed_scores_0_9 = normalize_scores_0_9(all_breed_scores)
    breed_score_map = {
        breed_id: all_breed_scores_0_9[i]
        for i, (breed_id, _) in enumerate(all_results)
    }

    # Collect all component values across ALL breeds for proper normalization
    # component_id -> list of all values across all breeds
    all_component_values: dict[str, list[float]] = {}

    for breed_id in matcher.breed_contexts:
        breed_context = matcher.breed_contexts[breed_id]
        for comp_id, comp_val in breed_context.items():
            score = comp_val.t - comp_val.f
            if comp_id not in all_component_values:
                all_component_values[comp_id] = []
            all_component_values[comp_id].append(score)

    # Pre-compute normalized scores for each component
    component_score_maps: dict[str, dict[float, int]] = {}
    for comp_id, values in all_component_values.items():
        if not values:
            continue
        min_val = min(values)
        max_val = max(values)
        # Create mapping from raw score to 0-9
        component_score_maps[comp_id] = {
            v: normalize_to_0_9(v, min_val, max_val)
            for v in set(values)
        }

    # First pass: collect ALL raw match scores across all breeds for normalization
    all_raw_matches = []
    breed_match_data = {}  # breed_id -> list of match data

    for breed_id, total_score in results:
        breed_row = matcher.eval_matrix[breed_id]
        breed_context = matcher.breed_contexts.get(breed_id, {})

        need_match_data = []
        for need_data in needs_to_explain:
            need_id = need_data["need_id"]
            info = needs_info.get(need_id, {})
            formula = info.get("formula", "")
            breed_val = breed_row.get(need_id)

            if breed_val:
                breed_score = breed_val.t - breed_val.f
                match = need_data["user_score"] * breed_score
                is_match = match > 0
            else:
                breed_score = 0.0
                match = 0.0
                is_match = False

            # Extract component values with proper normalization across all breeds
            components = {}
            for var in extract_formula_variables(formula):
                var_val = breed_context.get(var)
                if var_val:
                    score = var_val.t - var_val.f
                    # Get normalized score from pre-computed map
                    if var in component_score_maps and score in component_score_maps[var]:
                        comp_0_9 = component_score_maps[var][score]
                    else:
                        # Fallback to fixed range normalization
                        comp_0_9 = normalize_to_0_9(score, -1.0, 1.0)
                    components[var] = comp_0_9

            all_raw_matches.append(match)
            need_match_data.append({
                "need_name": need_data["need_name"],
                "components": components,
                "is_match": is_match,
                "raw_match": match
            })

        breed_match_data[breed_id] = need_match_data

    # Normalize ALL match scores together (across all breeds and needs)
    all_match_scores_0_9 = normalize_scores_0_9(all_raw_matches)

    # Second pass: build breed recommendations with normalized scores
    breeds = []
    match_idx = 0
    for breed_id, total_score in results:
        need_match_data = breed_match_data[breed_id]

        need_matches = []
        for data in need_match_data:
            need_matches.append({
                "need_name": data["need_name"],
                "components": data["components"],
                "is_match": data["is_match"],
                "score_0_9": all_match_scores_0_9[match_idx] if match_idx < len(all_match_scores_0_9) else 5
            })
            match_idx += 1

        breeds.append(BreedRecommendation(
            breed_id=breed_id,
            breed_name=breed_names.get(breed_id, breed_id),
            score=round(total_score, 2),
            score_0_9=breed_score_map.get(breed_id, 5),
            need_matches=need_matches
        ))

    return ExplanationData(
        user_needs=user_needs,
        breeds=breeds
    )


def build_prompt(data: ExplanationData, language: str = "Russian") -> str:
    """
    Build LLM prompt for explanation generation.

    Args:
        data: Explanation data collected from profile and matcher
        language: Language for the response (from config)

    Returns:
        Prompt string for LLM
    """
    # Format user needs with type marker and scores
    constraints = [n for n in data.user_needs if n.is_constraint]
    preferences = [n for n in data.user_needs if not n.is_constraint]

    user_needs_text = ""
    if constraints:
        user_needs_text += "Constraints (living conditions):\n"
        user_needs_text += "\n".join(
            f"  - {n.need_name}:{n.score_0_9} {'important' if n.user_wants else 'not required'}"
            for n in constraints
        )
        user_needs_text += "\n"
    if preferences:
        user_needs_text += "Preferences (character, behavior):\n"
        user_needs_text += "\n".join(
            f"  - {n.need_name}:{n.score_0_9} {'important' if n.user_wants else 'not required'}"
            for n in preferences
        )

    # Format each breed with matches for ALL user needs
    breeds_text = ""
    for i, breed in enumerate(data.breeds, 1):
        breeds_text += f"\n{i}. {breed.breed_name}:{breed.score_0_9}\n"
        for match in breed.need_matches:
            status = "✓" if match["is_match"] else "✗"
            # Show component values with scores
            components_str = ", ".join(f"{k}:{v}" for k, v in match["components"].items())
            breeds_text += f"  [{status}] {match['need_name']}:{match['score_0_9']}"
            if components_str:
                breeds_text += f" ({components_str})"
            breeds_text += "\n"

    prompt = f'''You are a canine consultant. Explain to the user why these three breeds may suit them.

DATA FORMAT:
The number after the colon (0–9) is a service score.
Use them for: comparisons, setting priorities, final conclusions.
DO NOT mention the numbers themselves, DO NOT use words like "score", "points", "out of 9".

User requirements:
{user_needs_text}
("important" = user wants this, "not required" = not a criterion for the user)

Recommended breeds (✓ = matches, ✗ = does not match):
{breeds_text}
Instructions:
- Format the response in HTML (use <p>, <strong>, <ul>, <li>, etc.)
- Write in {language}, grammatically correct
- Base your response ONLY on facts from the context above — do not invent information
- Use scores to set priorities: high scores — emphasize, low scores — mention as drawbacks
- Introduction: 2-3 sentences — user's key requirements (based on high need scores)
- For each breed: 3-5 sentences, prioritizing by characteristic scores
- Do NOT mention characteristics marked "not required"
- Tone: calm, informative, without enthusiastic evaluations
- At the end: 2-3 sentences — what to consider when choosing (no heading)'''

    return prompt


def generate_explanation(
    profile: UserProfile,
    matcher: BreedMatcher,
    api_key: str | None = None
) -> str:
    """
    Generate human-friendly explanation for breed recommendation.

    Args:
        profile: User profile with answered needs
        matcher: Breed matcher instance
        api_key: Nebius API key (defaults to NEBIUS_API_KEY env var)

    Returns:
        Generated explanation text
    """
    # Load config
    config = load_config()
    explanation_config = config.get("explanation", {})
    language = explanation_config.get("language", "Russian")

    # Collect data
    data = collect_explanation_data(profile, matcher)

    # Build prompt with language from config
    prompt = build_prompt(data, language=language)

    # Call LLM
    client = OpenAI(
        base_url="https://api.tokenfactory.nebius.com/v1/",
        api_key=api_key or os.environ.get("NEBIUS_API_KEY")
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000
    )

    message = response.choices[0].message
    # gpt-oss-120b is a reasoning model: content may be None, use reasoning_content as fallback
    return message.content or getattr(message, 'reasoning_content', None)


# For testing
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(str(PROJECT_ROOT / ".env"))

    # Load profile from file or use default
    profile_path = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        profile = load_profile(profile_path)
        source = profile_path or "interview_latest.json"
        print(f"Loaded profile from: {source}")
    except FileNotFoundError:
        print("No saved interview found. Creating sample profile...")
        profile = UserProfile()
        profile.add_answer("apartment_compatible", "true")
        profile.add_answer("low_shedding", "true")
        profile.add_answer("child_friendly", "true")
        profile.add_answer("first_time_friendly", "true")

    print(f"Answers in profile: {len(profile.get_answer_history())}")
    print()

    matcher = BreedMatcher()

    # Show collected data
    data = collect_explanation_data(profile, matcher)

    print("User needs to explain:")
    constraints = [n for n in data.user_needs if n.is_constraint]
    preferences = [n for n in data.user_needs if not n.is_constraint]
    if constraints:
        print("  Constraints:")
        for need in constraints:
            direction = "wants" if need.user_wants else "not needed"
            print(f"    - {need.need_name}: {direction}")
    if preferences:
        print("  Preferences:")
        for need in preferences:
            direction = "wants" if need.user_wants else "not needed"
            print(f"    - {need.need_name}: {direction}")
    print()

    print("Top 3 breeds (matches for each need):")
    for breed in data.breeds:
        print(f"\n  {breed.breed_name} (score={breed.score})")
        for match in breed.need_matches:
            status = "✓" if match["is_match"] else "✗"
            components = ", ".join(f"{k}={v}" for k, v in match["components"].items())
            line = f"    [{status}] {match['need_name']}"
            if components:
                line += f" ({components})"
            print(line)
    print()

    # Load language from config
    config = load_config()
    language = config.get("explanation", {}).get("language", "Russian")

    # Show prompt
    prompt = build_prompt(data, language=language)
    print("=== PROMPT ===")
    print(prompt)
    print()

    # Generate explanation (if API key available)
    if os.environ.get("NEBIUS_API_KEY"):
        print("=== EXPLANATION ===")
        explanation = generate_explanation(profile, matcher)
        print(explanation)
    else:
        print("Set NEBIUS_API_KEY to generate explanation")
