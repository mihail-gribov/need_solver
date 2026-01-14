# fuzzy4 — 4-Valued Fuzzy Logic

## 1. Truth Carrier

Each proposition is a **two-component truth vector**:

```
x = (T, F),  T, F ∈ [0,1]
```

- T = degree of confirmation
- F = degree of refutation

**No constraint** T + F = 1.

---

## 2. Basic Logic States

| State      | Vector  |
|------------|---------|
| TRUE       | (1, 0)  |
| FALSE      | (0, 1)  |
| UNKNOWN    | (0, 0)  |
| CONFLICT   | (1, 1)  |

This is **Belnap's 4-valued logic** with continuous weights.

---

## 3. T-norm (Lukasiewicz)

### AND (T-norm)

```
a ⊗ b = max(0, a + b - 1)
```

### OR (S-norm)

```
a ⊕ b = min(1, a + b)
```

### NOT

```
¬a = 1 - a
```

---

## 4. Negation

For vector:

```
¬(T, F) = (F, T)
```

Meaning:
- Confirmation and refutation swap
- **CONFLICT and UNKNOWN preserve form**

---

## 5. Conjunction (AND)

Given:
```
x = (T_x, F_x),  y = (T_y, F_y)
```

### Truth

```
T_{x∧y} = max(0, T_x + T_y - 1)
```

### Falsity

```
F_{x∧y} = min(1, F_x + F_y)
```

**Interpretation:**
- To assert AND, need confirmation of both
- To refute AND, suffices to refute either

---

## 6. Disjunction (OR)

### Truth

```
T_{x∨y} = min(1, T_x + T_y)
```

### Falsity

```
F_{x∨y} = max(0, F_x + F_y - 1)
```

**Interpretation:**
- To assert OR, one suffices
- To refute OR, must refute both

---

## 7. Implication

Via Lukasiewicz construction:

```
x → y := ¬x ∨ y
```

Thus:
```
T = min(1, F_x + T_y)
F = max(0, T_x + F_y - 1)
```

---

## 8. Neutral Elements

| Operation | Neutral Element |
|-----------|-----------------|
| AND       | (1, 0)          |
| OR        | (0, 1)          |
| NOT       | involution      |

---

## 9. Properties

✔ All operations:
- Closed in [0,1]²
- Monotonic in respective arguments
- Match boolean logic at {0,1}

---

## 10. Key Implications

This algebra:
- Allows **incomplete knowledge**
- Allows **contradictory knowledge**
- Doesn't "break" on conflict
- Perfect for:
  - Requirement aggregation
  - Condition composition
  - Gradual information refinement

---

# Truth Tables

Canonical 4 values {T, F, U, C}:
- **T** = (1, 0)
- **F** = (0, 1)
- **U** = (0, 0)
- **C** = (1, 1)

## NOT

| x | ¬x |
|---|-----|
| T | F   |
| F | T   |
| U | U   |
| C | C   |

## AND (∧)

| x ∧ y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | F | U | C |
| **F** | F | F | F | F |
| **U** | U | F | U | F |
| **C** | C | F | F | C |

## OR (∨)

| x ∨ y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | T | T | T |
| **F** | T | F | U | C |
| **U** | T | U | U | T |
| **C** | T | C | T | C |

## IMPLIES (→)

| x → y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | F | U | C |
| **F** | T | T | T | T |
| **U** | T | U | U | T |
| **C** | T | C | U | C |

## IFF (↔)

| x ↔ y | T | F | U | C |
|-------|---|---|---|---|
| **T** | T | F | U | C |
| **F** | F | T | U | C |
| **U** | U | U | U | U |
| **C** | C | C | U | C |

---

## Constants

```python
TRUE     = (1, 0)
FALSE    = (0, 1)
UNKNOWN  = (0, 0)
CONFLICT = (1, 1)
```

## Library

See [fuzzy4](https://github.com/mihail-gribov/fuzzy4) for Python implementation.
