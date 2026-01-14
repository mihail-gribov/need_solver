# Need Solver — Main Specification

## Goal

Build a universal system that recommends objects from a catalog based on questionnaire survey results.

Examples: dog/cat breeds, car models, courses, products, etc.

## System Requirements

1. Collect user **needs** and **constraints**
2. Match them against object characteristics
3. Compute **satisfaction scores** and rank objects
4. Select **next question adaptively** to minimize questions until stable top-N

---

## Data Model

### 1) Object Catalog

Catalog O = {o_1, ..., o_n}, each object has feature vector:

```
X^(o) = [x_1, x_2, ..., x_d], x_i ∈ [0,1]
```

Feature basis requirements:
- Covers all user needs/constraints
- Minimal, no duplicates
- Supports continuous [0,1] and categorical (one-hot) features

### 2) User Profile

Formed during survey, consists of:
- **Needs** R = [r_1, ..., r_K], r_k ∈ [0,1]
- **Constraints** C = [c_1, ..., c_L], c_l ∈ [0,1]

Interpretation:
- 0 = not important / no constraint
- 1 = critical / hard requirement

### 3) Formulas (CNF with 4-valued fuzzy logic)

Each need/constraint is a formula over object features.
Format: **CNF** — conjunction of disjunctions:
- Literal: x_i or ¬x_i
- Clause: L_1 ∨ ... ∨ L_m
- Formula: K_1 ∧ ... ∧ K_n

**Evaluation uses fuzzy4** (4-valued Belnap-Lukasiewicz logic):
- Each formula evaluates to (T, F) vector
- States: TRUE (1,0), FALSE (0,1), UNKNOWN (0,0), CONFLICT (1,1)
- Operations: Lukasiewicz t-norm/s-norm

---

## Questionnaire

### Question Structure

Each question has:
- Text
- Answer options
- For each answer:
  - Profile update rules (set/adjust r_k or c_l)
  - Disabled questions list
  - (optional) Branching rules

Rules are declarative (JSON) — survey logic editable without code changes.

---

## Scoring

### 1) Constraint Filtering

- Hard exclusion: if c_l ≥ T_hard and sat(G_l).F > threshold
- Soft penalty: reduce final score

### 2) Object Score

```
Score(o) = NeedsScore(o) × ConstraintsPenalty(o)
```

Where:
- NeedsScore = weighted average of sat(need).T with weights r_k
- ConstraintsPenalty = penalty based on sat(constraint).F with weights c_l

### 3) Output

- Ranked object list (top-N)
- Explanations: which needs satisfied/unsatisfied, which constraints violated
- Object metadata for display

---

## Adaptive Question Selection

Select next question based on:
- Current R, C values
- Current candidate pool S ⊆ O
- Available (not asked, not disabled) questions

Goal: minimize expected |S| after answer (maximize information gain)

Strategy:
1. Constraints first (hard filters)
2. Then needs (preferences)
3. Then refinement (aesthetics)

---

## Implementation Modules

1. Object catalog + feature profiles loader
2. Needs/constraints + formulas loader
3. Questions + update rules + disable logic loader
4. Survey session state manager
5. Scoring + filtering + explanation engine
6. Adaptive question selector
7. API interface (REST/GraphQL) or library interface

---

## Quality Criteria

- Minimize questions to stable top-N
- Interpretability (explanations for ranking/exclusion)
- Extensibility (easy to add object types and questions)
- Separation of content (catalog/questions/formulas) from code
