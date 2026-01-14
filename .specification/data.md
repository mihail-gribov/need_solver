# Data Specification

## 1. Static Data (Content)

### 1.1. Directory Structure

```text
content/
  meta/
    content_manifest.json
    locales/
      ru.json

  schemas/
    feature_schema.json
    user_factors_schema.json
    criteria_schema.json
    question_schema.json
    rules_schema.json

  features/
    breed_features.json          # feature basis for objects
    derived_features.json        # computed features (optional)

  breeds/
    index.json                   # object list with versions
    breeds.jsonl                 # one object per line
    facts_fields.json            # UI display fields

  criteria/
    needs.json
    constraints.json
    derived_criteria.json        # meta-criteria for grouping (optional)

  questions/
    blocks.json                  # stage order (constraints → purpose → lifestyle → prefs)
    q_owner_experience.json
    q_purpose.json
    q_housing.json
    ...

  rules/
    auto_weight_rules.json       # auto weight adjustment
    disable_rules.json           # question disable logic
    purpose_rules.json           # purpose → criteria weights
    gating_rules.json            # hard-first strategy
    normalization_rules.json     # normalization/clipping/conflicts

  explanation/
    criteria_texts.json          # explanation templates
    conflict_texts.json          # exclusion templates
    pros_cons_mapping.json       # sat/weights → pros/cons

  scoring/
    scoring_config.json          # aggregation formula, thresholds, defaults
    sat_semantics.json           # 4-valued fuzzy logic rules (fuzzy4)
```

---

### 1.2. Key Static Structures

#### A) Features (`features/breed_features.json`)

Object feature basis:
- `float01` features: `energy, trainability, grooming, shedding, ...`
- `onehot_soft` groups: `size` (toy/small/medium/large/giant)
- Extensions: `territoriality, reactivity, alone_tolerance, ...`

#### B) User Factors (`schemas/user_factors_schema.json`)

User profile derived from answers:
- `owner_experience`: `{animal_handling, dog_training, behavior_management}`
- `purpose`: onehot_soft distribution
- `housing`: locations + time_share + context
- `absence_daily`: hours_out
- `absence_trips`: frequency, duration
- `backup_care`: availability (0..1)

#### C) Criteria (`criteria/*.json`)

Needs and constraints with CNF formulas.

**Important**: Evaluation uses **4-valued fuzzy logic** (fuzzy4):
- Each formula evaluates to vector `(T, F)` where T=truth degree, F=falsity degree
- Four states: TRUE `(1,0)`, FALSE `(0,1)`, UNKNOWN `(0,0)`, CONFLICT `(1,1)`
- Operations use Lukasiewicz t-norm/s-norm

Formula types:
- `expr_cnf`: standard CNF over object features
- `expr_custom`: bridges between user_factors and object features

#### D) Questions and Rules (`questions/*.json`, `rules/*.json`)

Question structure:
- `answers[].effects[]` — declarative updates to `user_factors` and `criteria_weights`
- `answers[].disable[]` — static question disabling
- `show_if` — display conditions

Rules files:
- `purpose_rules.json` — purpose → criteria weights
- `auto_weight_rules.json` — experience/housing/children → criteria adjustment
- `disable_rules.json` — conditional question disabling
- `gating_rules.json` — question ordering strategy

#### E) Explanation Templates (`explanation/*.json`)

- Criteria explanation texts
- Hard constraint conflict templates
- Pros/cons rules (e.g., pros if `weight≥0.6 & sat.T≥0.75`)

---

## 2. Computed Data (Database)

SQLite database per domain.

### 2.1. Sessions

```sql
sessions (
    id TEXT PRIMARY KEY,
    content_version TEXT,
    locale TEXT,
    status TEXT,              -- active/completed
    created_at TEXT,
    updated_at TEXT
)

session_answers (
    session_id TEXT,
    question_id TEXT,
    answer_id TEXT,
    answered_at TEXT,
    payload_json TEXT,
    UNIQUE(session_id, question_id)
)
```

### 2.2. Aggregated State

```sql
session_user_factors (
    session_id TEXT PRIMARY KEY,
    user_factors_json TEXT,   -- owner_experience, purpose, housing, ...
    updated_at TEXT
)

session_criteria_weights (
    session_id TEXT PRIMARY KEY,
    weights_json TEXT,        -- {need_id: weight, constraint_id: weight, ...}
    updated_at TEXT
)

session_question_state (
    session_id TEXT PRIMARY KEY,
    asked_json TEXT,
    disabled_json TEXT,
    available_json TEXT,
    updated_at TEXT
)
```

### 2.3. Scoring Snapshots

```sql
session_scoring_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    run_no INTEGER,
    trigger TEXT,             -- answer_submitted/manual/resume
    params_json TEXT,
    created_at TEXT
)

session_breed_scores (
    run_id TEXT,
    breed_id TEXT,
    score REAL,
    needs_score_t REAL,       -- truth component
    needs_score_f REAL,       -- falsity component
    constraints_penalty REAL,
    hard_excluded INTEGER,
    rank INTEGER,
    details_json TEXT         -- per-criterion (T,F) breakdown
)

session_recommendation (
    session_id TEXT PRIMARY KEY,
    run_id TEXT,
    top_json TEXT,
    excluded_json TEXT,
    next_question_id TEXT,
    updated_at TEXT
)
```

### 2.4. Rule Trace (optional)

```sql
session_rule_trace (
    run_id TEXT,
    rule_id TEXT,
    rule_type TEXT,           -- auto_weight/disable/purpose/normalization
    applied INTEGER,
    diff_json TEXT,
    created_at TEXT
)
```

---

## 3. Scoring with 4-Valued Logic

### 3.1. Feature Evaluation

Each object feature `x ∈ [0,1]` maps to fuzzy4 vector:
```
feature_to_fuzzy4(x) = (x, 1-x)  -- default mapping
```

For unknown features:
```
unknown_feature() = (0, 0)  -- UNKNOWN state
```

### 3.2. Formula Evaluation

CNF formula evaluation:
- Literal: `x` → `(T, F)`, `¬x` → `(F, T)`
- Clause (OR): `T = min(1, ΣT)`, `F = max(0, ΣF - n + 1)`
- Formula (AND): `T = max(0, ΣT - n + 1)`, `F = min(1, ΣF)`

### 3.3. Score Aggregation

Final score considers both truth and falsity:
```
score = weighted_avg(sat.T) * (1 - constraint_penalty)
constraint_penalty = max(violated_constraint.F * weight)
```

---

## 4. MVP Entity Set

**Static:**
- feature_schema + breeds.jsonl
- criteria needs/constraints (15-25)
- questions: experience, purpose, housing, absence, allergies, noise, children
- rules: purpose_rules + disable_rules + scoring_config + sat_semantics
- explanation texts

**Database:**
- sessions
- session_answers
- session_user_factors
- session_criteria_weights
- session_scoring_runs
- session_breed_scores
- session_recommendation
