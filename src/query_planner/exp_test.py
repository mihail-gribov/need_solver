"""
Truth tables for 4-valued fuzzy logic operations.

Uses 4-valued Belnap-Lukasiewicz logic from fuzzy4 library.
Each value is a (T, F) vector: TRUE=(1,0), FALSE=(0,1), UNKNOWN=(0,0), CONFLICT=(1,1).

Expressions are evaluated via eval() with fuzzy4 operators:
  ~ (NOT), & (AND), | (OR), >> (IMPLIES), .iff() (bi-implication)
"""

from fuzzy4 import FuzzyBool, TRUE, FALSE, UNKNOWN, CONFLICT

# Canonical values
VALUES = [TRUE, CONFLICT, UNKNOWN, FALSE]
NAMES = {
    (1.0, 0.0): "T",
    (1.0, 1.0): "C",
    (0.0, 0.0): "U",
    (0.0, 1.0): "F",
}


def name(v: FuzzyBool) -> str:
    """Get short name for a fuzzy value."""
    return NAMES.get((v.t, v.f), f"({v.t:.1f},{v.f:.1f})")


def print_unary_table(op_name: str, op):
    """Print truth table for unary operation."""
    print(f"\n{op_name}:")
    print("-" * 10)
    print("  x | result")
    print("-" * 10)
    for x in VALUES:
        result = op(x)
        print(f"  {name(x)} |   {name(result)}")
    print()


def print_binary_table(op_name: str, op):
    """Print truth table for binary operation."""
    print(f"\n{op_name}:")
    print("-" * 22)
    print("      |  T    C    U    F")
    print("-" * 22)
    for x in VALUES:
        row = f"  {name(x)}   |"
        for y in VALUES:
            result = op(x, y)
            row += f"  {name(result)}  "
        print(row)
    print()


# NOT
print_unary_table("NOT (~x)", lambda x: ~x)

# AND
print_binary_table("AND (x & y)", lambda x, y: x & y)

# OR
print_binary_table("OR (x | y)", lambda x, y: x | y)

# IMPLIES
print_binary_table("IMPLIES (x >> y)", lambda x, y: x >> y)

# IFF (bi-implication)
print_binary_table("IFF (x <-> y)", lambda x, y: x.iff(y))
