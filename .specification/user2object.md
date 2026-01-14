# User to Object Mapping

## Logical Operations in fuzzy4

All operations use **4-valued Belnap-Lukasiewicz logic**.
Each value is a vector **(T, F)** where T = truth degree, F = falsity degree.

### Canonical Values

| State    | Vector  |
|----------|---------|
| TRUE     | (1, 0)  |
| FALSE    | (0, 1)  |
| UNKNOWN  | (0, 0)  |
| CONFLICT | (1, 1)  |

---

## 1. NOT (Negation)

```
¬(T, F) = (F, T)
```

| x | ¬x |
|---|-----|
| T | F   |
| F | T   |
| U | U   |
| C | C   |

UNKNOWN and CONFLICT are invariant under negation.

---

## 2. AND (Conjunction)

Uses Lukasiewicz t-norm:

```
T_result = max(0, T_x + T_y - 1)
F_result = min(1, F_x + F_y)
```

| x ∧ y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | F | U | C |
| **F** | F | F | F | F |
| **U** | U | F | U | F |
| **C** | C | F | F | C |

- FALSE is absorbing element
- Both must confirm for truth
- Any can falsify

---

## 3. OR (Disjunction)

Uses Lukasiewicz s-norm:

```
T_result = min(1, T_x + T_y)
F_result = max(0, F_x + F_y - 1)
```

| x ∨ y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | T | T | T |
| **F** | T | F | U | C |
| **U** | T | U | U | T |
| **C** | T | C | T | C |

- TRUE is absorbing element
- One suffices for truth
- Both must falsify

---

## 4. IMPLIES (→)

```
x → y = ¬x ∨ y
```

| x → y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | F | U | C |
| **F** | T | T | T | T |
| **U** | T | U | U | T |
| **C** | T | C | U | C |

False premise → always true.

---

## 5. IFF (↔, Bi-implication)

```
x ↔ y = (x → y) ∧ (y → x)
```

| x ↔ y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | F | U | C |
| **F** | F | T | U | C |
| **U** | U | U | U | U |
| **C** | C | C | U | C |

---

## 6. Formula Evaluation

### CNF Structure

```
Formula = Clause_1 ∧ Clause_2 ∧ ... ∧ Clause_n
Clause = Literal_1 ∨ Literal_2 ∨ ... ∨ Literal_m
Literal = x_i or ¬x_i
```

### Evaluation

1. Map feature x ∈ [0,1] to (T, F):
   - Default: `(x, 1-x)`
   - Unknown: `(0, 0)`

2. Evaluate literals:
   - `x` → `(T, F)`
   - `¬x` → `(F, T)`

3. Evaluate clause (OR):
   - `T = min(1, Σ T_literals)`
   - `F = max(0, Σ F_literals - n + 1)`

4. Evaluate formula (AND):
   - `T = max(0, Σ T_clauses - n + 1)`
   - `F = min(1, Σ F_clauses)`

---

## 7. Scoring

Final object score uses both T and F components:

```
NeedsScore = Σ(weight_k × sat_k.T) / Σ weight_k
ConstraintPenalty = max(weight_l × sat_l.F)
Score = NeedsScore × (1 - ConstraintPenalty)
```

### Hard Exclusion

Object excluded if:
- `constraint_weight ≥ threshold_hard`
- `sat(constraint).F ≥ threshold_violation`

---

## 8. Why fuzzy4?

Advantages over standard [0,1] fuzzy logic:

1. **Handles incomplete knowledge** — UNKNOWN state (0, 0)
2. **Handles conflicting info** — CONFLICT state (1, 1)
3. **Doesn't break on contradictions**
4. **Monotonic and well-defined**
5. **Matches boolean logic at boundaries**

Perfect for:
- Requirement aggregation
- Condition composition
- Gradual information refinement
