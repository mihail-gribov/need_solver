#!/usr/bin/env python3
"""
Cluster dog breeds by their feature vectors to find similar/different groups.
"""

import json
from pathlib import Path
import math

SCRIPT_DIR = Path(__file__).parent
DOMAIN_DIR = SCRIPT_DIR.parent


def load_breeds() -> dict[str, dict]:
    """Load all breed fuzzy data."""
    fuzzy_dir = DOMAIN_DIR / "fuzzy"
    breeds = {}

    for fpath in fuzzy_dir.glob("*.json"):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        breeds[data["breed_id"]] = data

    return breeds


def load_breed_names() -> dict[str, str]:
    """Load breed display names."""
    breeds_file = DOMAIN_DIR / "content" / "breeds.json"
    with open(breeds_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {b["id"]: b.get("name_ru") or b["name_en"] for b in data["breeds"]}


def breed_to_vector(breed_data: dict) -> list[float]:
    """Convert breed data to feature vector using (t - f) as value."""
    vector = []

    # Features
    for feat_id, feat_data in sorted(breed_data.get("features", {}).items()):
        # Use t - f as the effective value (-1 to +1 range)
        value = feat_data["t"] - feat_data["f"]
        vector.append(value)

    # Categories (size, height, lifespan)
    for group_id in ["size_group", "height_group", "lifespan_group"]:
        group = breed_data.get("categories", {}).get(group_id, {})
        for cat_id, cat_data in sorted(group.get("values", {}).items()):
            value = cat_data["t"] - cat_data["f"]
            vector.append(value)

    return vector


def euclidean_distance(v1: list[float], v2: list[float]) -> float:
    """Calculate Euclidean distance between two vectors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))


def find_most_different_pairs(breeds: dict, names: dict, top_k: int = 20):
    """Find breed pairs with maximum distance."""
    vectors = {bid: breed_to_vector(data) for bid, data in breeds.items()}

    distances = []
    breed_ids = list(vectors.keys())

    for i, bid1 in enumerate(breed_ids):
        for bid2 in breed_ids[i+1:]:
            dist = euclidean_distance(vectors[bid1], vectors[bid2])
            distances.append((bid1, bid2, dist))

    distances.sort(key=lambda x: x[2], reverse=True)

    print(f"\n{'='*70}")
    print(f"  TOP {top_k} MOST DIFFERENT BREED PAIRS")
    print(f"{'='*70}\n")

    for bid1, bid2, dist in distances[:top_k]:
        name1 = names.get(bid1, bid1)
        name2 = names.get(bid2, bid2)
        print(f"  {dist:.2f}  {name1} <-> {name2}")


def find_most_similar_pairs(breeds: dict, names: dict, top_k: int = 20):
    """Find breed pairs with minimum distance."""
    vectors = {bid: breed_to_vector(data) for bid, data in breeds.items()}

    distances = []
    breed_ids = list(vectors.keys())

    for i, bid1 in enumerate(breed_ids):
        for bid2 in breed_ids[i+1:]:
            dist = euclidean_distance(vectors[bid1], vectors[bid2])
            distances.append((bid1, bid2, dist))

    distances.sort(key=lambda x: x[2])

    print(f"\n{'='*70}")
    print(f"  TOP {top_k} MOST SIMILAR BREED PAIRS")
    print(f"{'='*70}\n")

    for bid1, bid2, dist in distances[:top_k]:
        name1 = names.get(bid1, bid1)
        name2 = names.get(bid2, bid2)
        print(f"  {dist:.2f}  {name1} <-> {name2}")


def simple_kmeans(vectors: dict[str, list[float]], k: int = 5, max_iter: int = 100):
    """Simple K-means clustering."""
    import random

    breed_ids = list(vectors.keys())
    n_features = len(next(iter(vectors.values())))

    # Initialize centroids randomly
    centroid_ids = random.sample(breed_ids, k)
    centroids = [vectors[bid].copy() for bid in centroid_ids]

    assignments = {}

    for _ in range(max_iter):
        # Assign breeds to nearest centroid
        new_assignments = {}
        for bid, vec in vectors.items():
            distances = [euclidean_distance(vec, c) for c in centroids]
            cluster = distances.index(min(distances))
            new_assignments[bid] = cluster

        if new_assignments == assignments:
            break
        assignments = new_assignments

        # Update centroids
        for c in range(k):
            members = [vectors[bid] for bid, cluster in assignments.items() if cluster == c]
            if members:
                centroids[c] = [
                    sum(m[i] for m in members) / len(members)
                    for i in range(n_features)
                ]

    return assignments, centroids


def load_user_needs() -> dict:
    """Load user needs definitions."""
    needs_file = DOMAIN_DIR / "content" / "user_needs.json"
    with open(needs_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {n["id"]: n for n in data["needs"]}


def get_feature_names(breeds: dict) -> list[str]:
    """Get ordered list of feature names matching vector indices."""
    sample = next(iter(breeds.values()))
    names = []

    for feat_id in sorted(sample.get("features", {}).keys()):
        names.append(feat_id)

    for group_id in ["size_group", "height_group", "lifespan_group"]:
        group = sample.get("categories", {}).get(group_id, {})
        for cat_id in sorted(group.get("values", {}).keys()):
            names.append(cat_id)

    return names


def analyze_cluster_characteristics(
    breeds: dict,
    names: dict,
    assignments: dict,
    top_features: int = 5
) -> dict:
    """Analyze distinctive characteristics for each cluster."""
    vectors = {bid: breed_to_vector(data) for bid, data in breeds.items()}
    feature_names = get_feature_names(breeds)
    n_features = len(feature_names)

    # Calculate global mean for each feature
    all_vectors = list(vectors.values())
    global_mean = [
        sum(v[i] for v in all_vectors) / len(all_vectors)
        for i in range(n_features)
    ]

    # Group by cluster
    clusters = {}
    for bid, cluster in assignments.items():
        if cluster not in clusters:
            clusters[cluster] = []
        clusters[cluster].append(bid)

    cluster_profiles = {}

    for cluster_id, member_ids in clusters.items():
        member_vectors = [vectors[bid] for bid in member_ids]

        # Calculate cluster mean
        cluster_mean = [
            sum(v[i] for v in member_vectors) / len(member_vectors)
            for i in range(n_features)
        ]

        # Calculate deviation from global mean
        deviations = []
        for i, feat_name in enumerate(feature_names):
            deviation = cluster_mean[i] - global_mean[i]
            deviations.append((feat_name, deviation, cluster_mean[i]))

        # Sort by absolute deviation
        deviations.sort(key=lambda x: abs(x[1]), reverse=True)

        cluster_profiles[cluster_id] = {
            "members": member_ids,
            "top_positive": [(f, d, m) for f, d, m in deviations if d > 0][:top_features],
            "top_negative": [(f, d, m) for f, d, m in deviations if d < 0][:top_features],
        }

    return cluster_profiles


def map_features_to_needs(features: list[tuple], user_needs: dict) -> list[str]:
    """Find user needs that match given features."""
    matched_needs = []

    for need_id, need in user_needs.items():
        formula = need.get("formula", "")
        for feat_name, deviation, _ in features:
            # Check if feature appears in formula (simple string match)
            if feat_name in formula:
                # Determine if need is satisfied by high or low value
                is_negated = f"~{feat_name}" in formula
                if (deviation > 0 and not is_negated) or (deviation < 0 and is_negated):
                    matched_needs.append((need_id, need.get("name", need_id)))
                    break

    return matched_needs


def cluster_breeds(breeds: dict, names: dict, k: int = 5):
    """Cluster breeds and display results with characteristics."""
    vectors = {bid: breed_to_vector(data) for bid, data in breeds.items()}

    assignments, centroids = simple_kmeans(vectors, k=k)

    # Analyze cluster characteristics
    profiles = analyze_cluster_characteristics(breeds, names, assignments)
    user_needs = load_user_needs()

    print(f"\n{'='*70}")
    print(f"  K-MEANS CLUSTERING (k={k})")
    print(f"{'='*70}")

    # Group by cluster
    clusters = {}
    for bid, cluster in assignments.items():
        if cluster not in clusters:
            clusters[cluster] = []
        clusters[cluster].append(bid)

    for cluster_id in sorted(clusters.keys()):
        members = clusters[cluster_id]
        profile = profiles[cluster_id]

        print(f"\n  {'─'*66}")
        print(f"  CLUSTER {cluster_id + 1} ({len(members)} breeds)")
        print(f"  {'─'*66}")

        # Show breeds
        print(f"\n  Breeds:")
        for bid in sorted(members, key=lambda x: names.get(x, x)):
            print(f"    • {names.get(bid, bid)}")

        # Show distinctive HIGH features
        print(f"\n  HIGH characteristics (above average):")
        for feat, dev, mean in profile["top_positive"]:
            bar = "+" * int(abs(dev) * 10)
            print(f"    ↑ {feat:<28} {mean:+.2f} ({bar})")

        # Show distinctive LOW features
        print(f"\n  LOW characteristics (below average):")
        for feat, dev, mean in profile["top_negative"]:
            bar = "-" * int(abs(dev) * 10)
            print(f"    ↓ {feat:<28} {mean:+.2f} ({bar})")

        # Map to user needs
        all_features = profile["top_positive"] + profile["top_negative"]
        matched = map_features_to_needs(all_features, user_needs)

        if matched:
            print(f"\n  Best for users who need:")
            for need_id, need_name in matched[:7]:
                print(f"    ✓ {need_name}")

    print()


def analyze_needs_coverage(breeds: dict, k: int = 6):
    """Check if dominant cluster features are covered by user needs."""
    vectors = {bid: breed_to_vector(data) for bid, data in breeds.items()}
    assignments, _ = simple_kmeans(vectors, k=k)
    names = load_breed_names()

    profiles = analyze_cluster_characteristics(breeds, names, assignments, top_features=10)
    user_needs = load_user_needs()

    # Build feature -> needs mapping
    feature_to_needs = {}
    for need_id, need in user_needs.items():
        formula = need.get("formula", "")
        # Extract feature names from formula (simple parsing)
        import re
        features_in_formula = re.findall(r'[a-z_]+', formula)
        for feat in features_in_formula:
            if feat not in feature_to_needs:
                feature_to_needs[feat] = []
            feature_to_needs[feat].append((need_id, need.get("name", need_id)))

    print(f"\n{'='*70}")
    print(f"  NEEDS COVERAGE ANALYSIS")
    print(f"{'='*70}")

    all_uncovered = set()
    all_covered = set()

    for cluster_id, profile in sorted(profiles.items()):
        print(f"\n  {'─'*66}")
        print(f"  CLUSTER {cluster_id + 1}")
        print(f"  {'─'*66}")

        all_features = profile["top_positive"] + profile["top_negative"]

        covered = []
        uncovered = []

        for feat, dev, mean in all_features:
            needs = feature_to_needs.get(feat, [])
            if needs:
                covered.append((feat, dev, needs))
                all_covered.add(feat)
            else:
                uncovered.append((feat, dev))
                all_uncovered.add(feat)

        if covered:
            print(f"\n  ✓ COVERED features (have matching needs):")
            for feat, dev, needs in covered:
                direction = "↑" if dev > 0 else "↓"
                need_names = ", ".join(n[1] for n in needs[:2])
                print(f"    {direction} {feat:<25} → {need_names}")

        if uncovered:
            print(f"\n  ✗ UNCOVERED features (NO matching needs!):")
            for feat, dev in uncovered:
                direction = "↑" if dev > 0 else "↓"
                print(f"    {direction} {feat:<25} ← NEED QUESTION FOR THIS!")

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Total covered features:   {len(all_covered)}")
    print(f"  Total uncovered features: {len(all_uncovered)}")

    if all_uncovered:
        print(f"\n  UNCOVERED FEATURES (need new user_needs):")
        for feat in sorted(all_uncovered):
            print(f"    • {feat}")

        print(f"\n  SUGGESTED NEW NEEDS:")
        suggestions = {
            "coat_type": ("grooming_tolerant", "Готовы к регулярному грумингу", "coat_type"),
            "dander_level": ("low_dander", "Низкий уровень перхоти", "~dander_level"),
            "genetic_risk": ("low_genetic_risk", "Низкий генетический риск", "~genetic_risk"),
            "noise_tolerance": ("noise_tolerant_home", "Шумная обстановка дома", "noise_tolerance"),
            "stranger_friendly": ("welcomes_guests", "Частые гости дома", "stranger_friendly"),
            "territoriality": ("territorial_guard", "Нужна территориальность", "territoriality"),
            "prey_drive": ("safe_with_small_pets", "Безопасность мелких питомцев", "~prey_drive"),
            "mental_stimulation": ("mental_games_lover", "Любитель интеллектуальных игр", "mental_stimulation"),
            "stress_sensitivity": ("calm_environment", "Спокойная обстановка", "~stress_sensitivity"),
            "health_robustness": ("robust_health", "Крепкое здоровье", "health_robustness"),
        }

        for feat in sorted(all_uncovered):
            if feat in suggestions:
                need_id, name, formula = suggestions[feat]
                print(f"\n    {feat}:")
                print(f"      id: {need_id}")
                print(f"      name: {name}")
                print(f"      formula: {formula}")


def analyze_cluster_differentiation(breeds: dict, k: int = 6):
    """Find overlapping needs between clusters and suggest differentiating questions."""
    vectors = {bid: breed_to_vector(data) for bid, data in breeds.items()}
    assignments, _ = simple_kmeans(vectors, k=k)
    names = load_breed_names()
    feature_names = get_feature_names(breeds)

    profiles = analyze_cluster_characteristics(breeds, names, assignments, top_features=10)
    user_needs = load_user_needs()

    # Get needs for each cluster
    cluster_needs = {}
    for cluster_id, profile in profiles.items():
        all_features = profile["top_positive"] + profile["top_negative"]
        matched = map_features_to_needs(all_features, user_needs)
        cluster_needs[cluster_id] = set(n[0] for n in matched)

    print(f"\n{'='*70}")
    print(f"  CLUSTER DIFFERENTIATION ANALYSIS")
    print(f"{'='*70}")

    # Calculate cluster centroids for comparison
    clusters = {}
    for bid, cluster in assignments.items():
        if cluster not in clusters:
            clusters[cluster] = []
        clusters[cluster].append(bid)

    cluster_centroids = {}
    for cluster_id, member_ids in clusters.items():
        member_vectors = [vectors[bid] for bid in member_ids]
        cluster_centroids[cluster_id] = [
            sum(v[i] for v in member_vectors) / len(member_vectors)
            for i in range(len(feature_names))
        ]

    # Find overlapping clusters
    cluster_ids = sorted(profiles.keys())
    overlaps = []

    for i, c1 in enumerate(cluster_ids):
        for c2 in cluster_ids[i+1:]:
            common_needs = cluster_needs[c1] & cluster_needs[c2]
            if common_needs:
                # Calculate centroid distance
                dist = euclidean_distance(cluster_centroids[c1], cluster_centroids[c2])
                overlap_ratio = len(common_needs) / max(len(cluster_needs[c1]), len(cluster_needs[c2]), 1)
                overlaps.append((c1, c2, common_needs, dist, overlap_ratio))

    # Sort by overlap ratio (most similar first)
    overlaps.sort(key=lambda x: x[4], reverse=True)

    for c1, c2, common_needs, dist, overlap_ratio in overlaps:
        if overlap_ratio < 0.3:
            continue

        print(f"\n  {'─'*66}")
        print(f"  CLUSTERS {c1+1} and {c2+1} - {overlap_ratio*100:.0f}% overlap")
        print(f"  {'─'*66}")

        # Show breeds in each cluster
        print(f"\n  Cluster {c1+1}: {', '.join(names.get(b, b) for b in sorted(clusters[c1])[:5])}...")
        print(f"  Cluster {c2+1}: {', '.join(names.get(b, b) for b in sorted(clusters[c2])[:5])}...")

        print(f"\n  Common needs ({len(common_needs)}):")
        for need_id in list(common_needs)[:5]:
            need_name = user_needs.get(need_id, {}).get("name", need_id)
            print(f"    • {need_name}")

        # Find features that differentiate these clusters
        print(f"\n  DIFFERENTIATING FEATURES (to split these clusters):")
        diffs = []
        for i, feat in enumerate(feature_names):
            diff = cluster_centroids[c1][i] - cluster_centroids[c2][i]
            if abs(diff) > 0.2:  # Significant difference
                diffs.append((feat, diff, cluster_centroids[c1][i], cluster_centroids[c2][i]))

        diffs.sort(key=lambda x: abs(x[1]), reverse=True)

        for feat, diff, val1, val2 in diffs[:5]:
            # Check if this feature has a need
            has_need = any(feat in need.get("formula", "") for need in user_needs.values())
            status = "✓" if has_need else "✗ NEED NEW QUESTION"
            arrow = ">" if diff > 0 else "<"
            print(f"    {feat:<25} C{c1+1}={val1:+.2f} {arrow} C{c2+1}={val2:+.2f}  {status}")

        # Suggest new needs
        uncovered_diffs = [(f, d, v1, v2) for f, d, v1, v2 in diffs[:5]
                          if not any(f in need.get("formula", "") for need in user_needs.values())]

        if uncovered_diffs:
            print(f"\n  SUGGESTED NEW NEEDS to differentiate:")
            for feat, diff, val1, val2 in uncovered_diffs:
                if diff > 0:
                    print(f"    → Question revealing HIGH {feat} (matches cluster {c1+1})")
                else:
                    print(f"    → Question revealing HIGH {feat} (matches cluster {c2+1})")


def analyze_feature_variance(breeds: dict):
    """Find features with highest variance (best discriminators)."""
    # Collect all feature values
    feature_values = {}

    for breed_data in breeds.values():
        for feat_id, feat_data in breed_data.get("features", {}).items():
            if feat_id not in feature_values:
                feature_values[feat_id] = []
            feature_values[feat_id].append(feat_data["t"] - feat_data["f"])

    # Calculate variance for each feature
    variances = []
    for feat_id, values in feature_values.items():
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        variances.append((feat_id, variance, min(values), max(values)))

    variances.sort(key=lambda x: x[1], reverse=True)

    print(f"\n{'='*70}")
    print(f"  FEATURE VARIANCE (best discriminators first)")
    print(f"{'='*70}\n")

    print(f"  {'Feature':<30} {'Variance':>10} {'Min':>8} {'Max':>8}")
    print(f"  {'-'*30} {'-'*10} {'-'*8} {'-'*8}")

    for feat_id, var, min_val, max_val in variances:
        print(f"  {feat_id:<30} {var:>10.3f} {min_val:>8.2f} {max_val:>8.2f}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cluster dog breeds")
    parser.add_argument("--similar", "-s", action="store_true", help="Show most similar pairs")
    parser.add_argument("--different", "-d", action="store_true", help="Show most different pairs")
    parser.add_argument("--cluster", "-c", type=int, default=0, help="K-means clustering with K clusters")
    parser.add_argument("--variance", "-v", action="store_true", help="Show feature variance")
    parser.add_argument("--coverage", action="store_true", help="Check needs coverage for cluster features")
    parser.add_argument("--diff", action="store_true", help="Find overlapping clusters and suggest differentiating needs")
    parser.add_argument("--top", "-k", type=int, default=20, help="Number of pairs to show")

    args = parser.parse_args()

    breeds = load_breeds()
    names = load_breed_names()

    print(f"\nLoaded {len(breeds)} breeds")

    if not any([args.similar, args.different, args.cluster, args.variance, args.coverage, args.diff]):
        # Default: show all
        args.variance = True
        args.different = True
        args.similar = True
        args.cluster = 5

    if args.coverage:
        analyze_needs_coverage(breeds, k=args.cluster if args.cluster > 0 else 6)

    if args.diff:
        analyze_cluster_differentiation(breeds, k=args.cluster if args.cluster > 0 else 6)

    if args.variance:
        analyze_feature_variance(breeds)

    if args.different:
        find_most_different_pairs(breeds, names, top_k=args.top)

    if args.similar:
        find_most_similar_pairs(breeds, names, top_k=args.top)

    if args.cluster > 0:
        cluster_breeds(breeds, names, k=args.cluster)


if __name__ == "__main__":
    main()
