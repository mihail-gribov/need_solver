#!/usr/bin/env python3
"""
Convert extracted breed features to 4-valued fuzzy logic format.

Formula for single source entry:
    t = value × confidence
    f = (1 - value) × confidence

Aggregation of multiple sources uses fuzzy4 accumulation (+):
    T_result = min(1, T1 + T2 + ...)
    F_result = min(1, F1 + F2 + ...)

This means:
    - Multiple confirmations → T grows (approaches TRUE)
    - Multiple refutations → F grows (approaches FALSE)
    - Conflicting sources → both grow (approaches CONFLICT)
    - No data → both stay 0 (UNKNOWN)

Formula for numerical parameters (one-hot categories):
    For each category, collect votes from all sources:
    - If value in range → vote FOR with confidence weight
    - If value not in range → vote AGAINST with confidence weight
    Then accumulate votes using fuzzy4 (+)

States:
    - TRUE:    high t, low f
    - FALSE:   low t, high f
    - UNKNOWN: low t, low f
    - CONFLICT: high t, high f
"""

import json
import sys
from pathlib import Path

from fuzzy4 import FuzzyBool

# Setup paths
SCRIPT_DIR = Path(__file__).parent
DOMAIN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = DOMAIN_DIR / "config.json"


def load_config() -> dict:
    """Load domain config."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()
CONTENT_DIR = DOMAIN_DIR / CONFIG["paths"]["content"]
EXTRACTED_DIR = DOMAIN_DIR / CONFIG["paths"]["extracted"]
FUZZY_DIR = DOMAIN_DIR / CONFIG["paths"]["fuzzy"]


def load_feature_spec() -> dict:
    """Load object_features.json with category definitions."""
    spec_path = CONTENT_DIR / "object_features.json"
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_single_entry(value: float, confidence: float) -> FuzzyBool:
    """
    Convert single value + confidence to fuzzy (t, f) vector.
    """
    if value is None:
        return FuzzyBool(0, 0)  # UNKNOWN

    t = value * confidence
    f = (1 - value) * confidence
    return FuzzyBool(t, f)


def aggregate_feature_entries(entries: list[dict]) -> dict:
    """
    Aggregate multiple source entries into single fuzzy value.

    Uses fuzzy4 accumulation (+) to combine evidence from multiple sources:
    - Multiple confirmations → T accumulates
    - Multiple refutations → F accumulates
    - Conflicting sources → both T and F grow → CONFLICT state

    Args:
        entries: List of {"value": X, "confidence": Y, "source": "..."}

    Returns:
        Fuzzy result dict with t, f, state, sources
    """
    if not entries:
        return {
            "t": 0, "f": 0,
            "state": "U",
            "sources": []
        }

    # Filter out null values
    valid_entries = [e for e in entries if e.get("value") is not None]

    if not valid_entries:
        return {
            "t": 0, "f": 0,
            "state": "U",
            "sources": [e.get("source", "unknown") for e in entries],
            "note": "all values null"
        }

    # Convert each entry to FuzzyBool and accumulate
    accumulated = FuzzyBool(0, 0)  # Start with UNKNOWN

    for entry in valid_entries:
        value = entry["value"]
        confidence = entry.get("confidence", 0.5)

        # Convert to fuzzy: t = value * conf, f = (1-value) * conf
        fb = convert_single_entry(value, confidence)

        # Accumulate evidence using fuzzy4 + operator
        accumulated = accumulated + fb

    return {
        "t": round(accumulated.t, 3),
        "f": round(accumulated.f, 3),
        "state": accumulated.dominant_state(),
        "sources": [e.get("source", "unknown") for e in valid_entries],
        "n_sources": len(valid_entries),
        "components": {
            "truth": round(accumulated.truth, 3),
            "falsity": round(accumulated.falsity, 3),
            "unknown": round(accumulated.unknown, 3),
            "conflict": round(accumulated.conflict, 3),
        }
    }


def value_in_range(value: float, min_val: float | None, max_val: float | None) -> bool:
    """Check if value falls within [min_val, max_val] range."""
    if min_val is not None and value < min_val:
        return False
    if max_val is not None and value >= max_val:
        return False
    return True


def convert_parameter_to_categories(
    measurements: list[dict],
    category_group: dict
) -> dict[str, dict]:
    """
    Convert numerical measurements to fuzzy one-hot categories.

    Args:
        measurements: List of {"value": [min, max] or X, "confidence": Y, "source": "..."}
        category_group: Category definition with "values" list

    Returns:
        Dict mapping category_id to fuzzy result
    """
    results = {}

    # Compute base categories
    for category in category_group["values"]:
        cat_id = category["id"]
        cat_min = category.get("min")
        cat_max = category.get("max")

        votes_for = []
        votes_against = []

        for m in measurements:
            value = m.get("value")
            confidence = m.get("confidence", 0.5)

            if value is None:
                continue

            # Handle range values [min, max]
            if isinstance(value, list) and len(value) == 2:
                val_min, val_max = value
                # Check if ranges overlap
                range_overlaps = not (val_max < cat_min if cat_min else False) and \
                                 not (val_min >= cat_max if cat_max else False)
                # Use midpoint for single-value comparison
                midpoint = (val_min + val_max) / 2

                if range_overlaps or value_in_range(midpoint, cat_min, cat_max):
                    votes_for.append(confidence)
                else:
                    votes_against.append(confidence)
            else:
                # Single value
                if value_in_range(value, cat_min, cat_max):
                    votes_for.append(confidence)
                else:
                    votes_against.append(confidence)

        # Calculate t and f as average of votes
        n = len(votes_for) + len(votes_against)
        t = sum(votes_for) / n if n > 0 else 0
        f = sum(votes_against) / n if n > 0 else 0

        fb = FuzzyBool(t, f)

        results[cat_id] = {
            "t": round(t, 3),
            "f": round(f, 3),
            "state": fb.dominant_state(),
            "votes_for": len(votes_for),
            "votes_against": len(votes_against),
        }

    # Compute derived categories (OR of base categories)
    for derived in category_group.get("derived", []):
        derived_id = derived["id"]
        formula = derived["formula"]

        # Parse formula: "cat1 | cat2 | cat3"
        parts = [p.strip() for p in formula.split("|")]

        # OR = max of t values, min of f values (optimistic)
        t_values = [results[p]["t"] for p in parts if p in results]
        f_values = [results[p]["f"] for p in parts if p in results]

        if t_values:
            # Use FuzzyBool OR operation
            combined = FuzzyBool(t_values[0], f_values[0])
            for i in range(1, len(t_values)):
                combined = combined | FuzzyBool(t_values[i], f_values[i])

            results[derived_id] = {
                "t": round(combined.t, 3),
                "f": round(combined.f, 3),
                "state": combined.dominant_state(),
                "derived_from": parts,
            }

    return results


def convert_breed(extracted_data: dict, spec: dict) -> dict:
    """Convert all features for a breed to fuzzy format."""
    result = {
        "breed_id": extracted_data["breed_id"],
        "features": {},
        "categories": {},
        "parameters_raw": extracted_data.get("parameters", {}),
        "notes": extracted_data.get("notes", ""),
        "sources": extracted_data.get("sources", []),
    }

    # Convert float features (now arrays of source entries)
    for feature_id, entries in extracted_data["features"].items():
        if isinstance(entries, list):
            # New format: array of source entries
            fuzzy = aggregate_feature_entries(entries)
        elif isinstance(entries, dict):
            # Legacy format: single entry
            fuzzy = aggregate_feature_entries([entries])
        else:
            # Unexpected format
            fuzzy = {"t": 0, "f": 0, "state": "U", "error": f"unexpected type: {type(entries)}"}

        result["features"][feature_id] = fuzzy

    # Convert numerical parameters to categories
    params = extracted_data.get("parameters", {})

    # Map parameter -> category group
    param_to_group = {
        "weight_kg": "size_group",
        "height_cm": "height_group",
        "lifespan_years": "lifespan_group",
    }

    for param_name, group_name in param_to_group.items():
        if param_name in params and group_name in spec:
            measurements = params[param_name]
            if isinstance(measurements, list):
                category_result = convert_parameter_to_categories(
                    measurements,
                    spec[group_name]
                )
                result["categories"][group_name] = {
                    "source_param": param_name,
                    "values": category_result
                }

    return result


def process_file(input_path: Path, output_path: Path, spec: dict) -> bool:
    """Process a single extracted file."""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        fuzzy_data = convert_breed(data, spec)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(fuzzy_data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        print(f"Error processing {input_path.name}: {e}", file=sys.stderr)
        return False


def main():
    """Convert all extracted files to fuzzy format."""
    FUZZY_DIR.mkdir(parents=True, exist_ok=True)

    # Load feature specification
    spec = load_feature_spec()

    extracted_files = list(EXTRACTED_DIR.glob("*.json"))

    if not extracted_files:
        print("No extracted files found.")
        return

    print(f"Converting {len(extracted_files)} files...")

    success = 0
    for path in extracted_files:
        output_path = FUZZY_DIR / path.name
        if process_file(path, output_path, spec):
            print(f"[OK] {path.name}")
            success += 1
        else:
            print(f"[ERROR] {path.name}")

    print(f"\nDone: {success}/{len(extracted_files)} converted")


if __name__ == "__main__":
    main()
