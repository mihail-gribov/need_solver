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
from .user_profile import UserProfile


# Blocks that represent hard constraints (facts about user's situation)
# vs soft preferences (what user would like)
CONSTRAINT_BLOCKS = {"size_constraints", "housing_environment"}


@dataclass
class UserNeed:
    """A single user need/requirement."""
    need_id: str
    need_name: str
    user_wants: bool  # True = user wants this, False = user doesn't need this
    is_constraint: bool  # True = constraint (size, housing), False = preference


@dataclass
class BreedRecommendation:
    """Data for a single breed recommendation."""
    breed_id: str
    breed_name: str
    score: float
    # How breed matches EACH user need (same order as ExplanationData.user_needs)
    # [{"need_name": str, "is_match": bool}, ...]
    need_matches: list[dict]


@dataclass
class ExplanationData:
    """Data prepared for LLM explanation generation."""
    # User's clearest needs - the basis for explanation
    user_needs: list[UserNeed]
    # Top breeds with matches for each user need
    breeds: list[BreedRecommendation]


DOMAIN_DIR = Path(__file__).parent


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
        filepath = DOMAIN_DIR / "data" / "interview_latest.json"
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
    max_preferences: int = 4
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

    # Analyze user's answers: find clear needs (high certainty, low contradiction)
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

    # Filter to clear needs only (high certainty, low contradiction)
    clear_needs = [
        n for n in user_analysis
        if n["consistency"] > 0.7 and n["certainty"] > 0.5
    ]
    clear_needs.sort(key=lambda x: x["clarity"], reverse=True)

    # Split into constraints and preferences, take top of each
    clear_constraints = [n for n in clear_needs if n["is_constraint"]][:max_constraints]
    clear_preferences = [n for n in clear_needs if not n["is_constraint"]][:max_preferences]

    # Combine into single list of needs to explain (constraints first, then preferences)
    needs_to_explain = clear_constraints + clear_preferences

    # Create UserNeed objects
    user_needs = [
        UserNeed(
            need_id=n["need_id"],
            need_name=n["need_name"],
            user_wants=n["user_wants"],
            is_constraint=n["is_constraint"]
        )
        for n in needs_to_explain
    ]

    # Build recommendation for each top breed
    breeds = []
    for breed_id, total_score in results:
        breed_row = matcher.eval_matrix[breed_id]
        breed_context = matcher.breed_contexts.get(breed_id, {})

        # Evaluate breed against EACH need in user_needs (same order)
        need_matches = []
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
                is_match = False

            # Extract component values from breed context
            components = {}
            for var in extract_formula_variables(formula):
                var_val = breed_context.get(var)
                if var_val:
                    score = var_val.t - var_val.f
                    # Describe as positive/negative/neutral
                    if score > 0.3:
                        components[var] = "высокий"
                    elif score < -0.3:
                        components[var] = "низкий"
                    else:
                        components[var] = "средний"

            need_matches.append({
                "need_name": need_data["need_name"],
                "formula": formula,
                "components": components,
                "is_match": is_match
            })

        breeds.append(BreedRecommendation(
            breed_id=breed_id,
            breed_name=breed_names.get(breed_id, breed_id),
            score=round(total_score, 2),
            need_matches=need_matches
        ))

    return ExplanationData(
        user_needs=user_needs,
        breeds=breeds
    )


def build_prompt(data: ExplanationData) -> str:
    """
    Build LLM prompt for explanation generation.

    Args:
        data: Explanation data collected from profile and matcher

    Returns:
        Prompt string for LLM
    """
    # Format user needs with type marker
    constraints = [n for n in data.user_needs if n.is_constraint]
    preferences = [n for n in data.user_needs if not n.is_constraint]

    user_needs_text = ""
    if constraints:
        user_needs_text += "Ограничения (условия жизни):\n"
        user_needs_text += "\n".join(
            f"  - {n.need_name}: {'важно' if n.user_wants else 'не требуется'}"
            for n in constraints
        )
        user_needs_text += "\n"
    if preferences:
        user_needs_text += "Предпочтения (характер, поведение):\n"
        user_needs_text += "\n".join(
            f"  - {n.need_name}: {'важно' if n.user_wants else 'не требуется'}"
            for n in preferences
        )

    # Format each breed with matches for ALL user needs
    breeds_text = ""
    for i, breed in enumerate(data.breeds, 1):
        breeds_text += f"\n{i}. {breed.breed_name}\n"
        for match in breed.need_matches:
            status = "✓" if match["is_match"] else "✗"
            # Show formula and component values
            components_str = ", ".join(f"{k}={v}" for k, v in match["components"].items())
            breeds_text += f"  [{status}] {match['need_name']}"
            if components_str:
                breeds_text += f" ({components_str})"
            breeds_text += "\n"

    prompt = f'''Ты — кинолог-консультант. Объясни пользователю, почему эти три породы могут ему подойти.

Что выяснилось о пользователе:
{user_needs_text}
(«важно» = пользователь этого хочет, «не требуется» = для пользователя это не критерий)

Рекомендуемые породы (✓ = соответствует, ✗ = не соответствует):
В скобках указаны фактические характеристики породы, влияющие на результат.
{breeds_text}
Инструкции:
- Форматируй ответ в HTML (используй <p>, <strong>, <ul>, <li> и т.д.)
- Пиши на русском языке, грамотно. "Low Drooling" = "минимальное слюноотделение" (не "слюнет" — такого слова нет)
- Основывайся ТОЛЬКО на фактах из контекста выше — не додумывай информацию
- Объясняй через фактические характеристики породы (указаны в скобках), а не абстрактно
  Пример: вместо "не подходит для квартиры" → "подходит по размеру (apartment_ok=высокий), но много лает (barking=высокий)"
- Вступление: 2-3 предложения — ключевые требования пользователя
- По каждой породе: 3-5 предложений, объясняя через конкретные характеристики
- Характеристики «не требуется» — НЕ упоминай
- Тон: спокойный, информативный, без восторженных оценок
- В конце: 2-3 предложения — что учесть при выборе (без заголовка)'''

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
    # Collect data
    data = collect_explanation_data(profile, matcher)

    # Build prompt
    prompt = build_prompt(data)

    # Call LLM
    client = OpenAI(
        base_url="https://api.tokenfactory.nebius.com/v1/",
        api_key=api_key or os.environ.get("NEBIUS_API_KEY")
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1200
    )

    return response.choices[0].message.content


# For testing
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

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

    # Show prompt
    prompt = build_prompt(data)
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
