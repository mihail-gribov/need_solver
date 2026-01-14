# Query Planner - Architecture Plan

## Overview

Universal object recommendation system based on questionnaire surveys with fuzzy logic scoring.

**Stack:** Python 3.11+, JSON configs, SQLite persistence

---

## Architecture Principles

1. **Clean Architecture** - Core library independent of interfaces
2. **Dependency Inversion** - Interfaces depend on core, not vice versa
3. **Separation of Concerns** - Content (catalog/questions/formulas) separate from code
4. **Interface Agnostic** - Same core works with CLI, REST API, GUI, etc.
5. **Domain Isolation** - Each domain model (dog breeds, cat breeds, cars, etc.) is a self-contained data package

---

## Project Structure

```
query_planner/
├── pyproject.toml                 # Project config (uv/poetry)
├── src/
│   └── query_planner/
│       ├── __init__.py
│       │
│       ├── core/                  # Core Library (interface-agnostic)
│       │   ├── __init__.py
│       │   ├── models/            # Domain models (dataclasses)
│       │   │   ├── __init__.py
│       │   │   ├── domain.py      # Domain metadata
│       │   │   ├── catalog.py     # Object, Characteristic
│       │   │   ├── profile.py     # UserProfile (needs R, constraints C)
│       │   │   ├── formula.py     # CNF formulas, literals, clauses
│       │   │   ├── question.py    # Question, Answer, UpdateRule
│       │   │   └── session.py     # Session state
│       │   │
│       │   ├── scoring/           # Scoring engine
│       │   │   ├── __init__.py
│       │   │   ├── fuzzy.py       # Fuzzy logic evaluation
│       │   │   ├── scorer.py      # NeedsScore, ConstraintsPenalty
│       │   │   └── ranker.py      # Ranking, filtering, top-N
│       │   │
│       │   ├── engine/            # Main engine
│       │   │   ├── __init__.py
│       │   │   ├── survey.py      # Survey orchestration
│       │   │   ├── selector.py    # Adaptive question selection
│       │   │   └── explainer.py   # Result explanations
│       │   │
│       │   └── ports/             # Abstract interfaces (ports)
│       │       ├── __init__.py
│       │       ├── domain_repo.py     # DomainRepository (ABC)
│       │       ├── catalog_repo.py    # CatalogRepository (ABC)
│       │       ├── question_repo.py   # QuestionRepository (ABC)
│       │       ├── formula_repo.py    # FormulaRepository (ABC)
│       │       └── session_repo.py    # SessionRepository (ABC)
│       │
│       ├── adapters/              # Concrete implementations (adapters)
│       │   ├── __init__.py
│       │   ├── json_loader.py     # JSON file loading
│       │   ├── sqlite_sessions.py # SQLite session persistence
│       │   └── memory_sessions.py # In-memory sessions (for testing)
│       │
│       ├── schemas/               # JSON schemas for validation
│       │   ├── domain.schema.json
│       │   ├── catalog.schema.json
│       │   ├── formulas.schema.json
│       │   └── questions.schema.json
│       │
│       └── cli/                   # CLI Interface
│           ├── __init__.py
│           ├── app.py             # Main CLI app (click/typer)
│           ├── commands/
│           │   ├── __init__.py
│           │   ├── survey.py      # Interactive survey command
│           │   ├── validate.py    # Validate config files
│           │   └── info.py        # Show catalog/question info
│           └── formatters/
│               ├── __init__.py
│               └── results.py     # Result formatting for terminal
│
├── domains/                       # Domain projects (isolated)
│   └── dog_breeds/                # Domain project: Dog Breeds
│       ├── data-spec.md           # Domain specification
│       ├── content/               # Static content (see Domain Projects section)
│       │   ├── meta/
│       │   ├── schemas/
│       │   ├── features/
│       │   ├── breeds/
│       │   ├── criteria/
│       │   ├── questions/
│       │   ├── rules/
│       │   ├── explanation/
│       │   └── scoring/
│       ├── scripts/               # Domain scripts (miner.py, validate.py)
│       ├── cache/                 # LLM cache
│       └── data/                  # Runtime DB (sessions.db) - not in git
│
└── tests/
    ├── unit/
    │   ├── test_fuzzy.py
    │   ├── test_scorer.py
    │   └── test_selector.py
    └── integration/
        └── test_survey_flow.py
```

---

## Core Modules Description

### 1. models/ - Domain Models

**domain.py:**
```python
@dataclass
class Domain:
    id: str
    name: str
    description: str
    version: str
    locale: str = "en"
```

**catalog.py:**
```python
@dataclass
class Characteristic:
    id: str
    name: str
    description: str | None = None

@dataclass
class CatalogObject:
    id: str
    name: str
    features: dict[str, float]  # {characteristic_id: value 0..1}
    metadata: dict[str, Any]    # Display-only properties
```

**profile.py:**
```python
@dataclass
class UserProfile:
    needs: dict[str, float]        # {need_id: intensity 0..1}
    constraints: dict[str, float]  # {constraint_id: intensity 0..1}
```

**formula.py:**
```python
@dataclass
class Literal:
    var: str           # characteristic id
    negated: bool = False

@dataclass
class Clause:
    literals: list[Literal]  # OR of literals

@dataclass
class Formula:
    id: str
    name: str
    clauses: list[Clause]    # AND of clauses (CNF)
```

**question.py:**
```python
@dataclass
class UpdateRule:
    target: str         # need_id or constraint_id
    target_type: Literal["need", "constraint"]
    operation: Literal["set", "add", "multiply"]
    value: float

@dataclass
class Answer:
    id: str
    text: str
    updates: list[UpdateRule]
    disables: list[str]  # question IDs to disable

@dataclass
class Question:
    id: str
    text: str
    answers: list[Answer]
    priority: int = 0    # For initial ordering
```

**session.py:**
```python
@dataclass
class Session:
    id: str
    domain_id: str               # Which domain this session belongs to
    profile: UserProfile
    answered: dict[str, str]     # {question_id: answer_id}
    disabled: set[str]           # Disabled question IDs
    created_at: datetime
    updated_at: datetime
```

### 2. scoring/ - Scoring Engine

**fuzzy.py:**
- `evaluate_literal(lit: Literal, features: dict) -> float`
- `evaluate_clause(clause: Clause, features: dict) -> float` (max of literals)
- `evaluate_formula(formula: Formula, features: dict) -> float` (weighted avg of clauses)

**scorer.py:**
- `calculate_need_satisfaction(obj, formula, profile) -> float`
- `calculate_constraint_penalty(obj, formula, profile) -> float`
- `calculate_score(obj, needs_formulas, constraint_formulas, profile) -> ObjectScore`

**ranker.py:**
- `rank_objects(objects, scores) -> list[RankedObject]`
- `filter_by_constraints(objects, threshold) -> list[CatalogObject]`
- `get_top_n(ranked, n) -> list[RankedObject]`

### 3. engine/ - Main Engine

**survey.py:**
```python
class SurveyEngine:
    def __init__(self, catalog_repo, question_repo, formula_repo, session_repo): ...

    def start_session(self, catalog_id: str) -> Session: ...
    def get_next_question(self, session: Session) -> Question | None: ...
    def submit_answer(self, session: Session, question_id: str, answer_id: str): ...
    def get_results(self, session: Session, top_n: int = 10) -> SurveyResults: ...
    def get_current_ranking(self, session: Session) -> list[RankedObject]: ...
```

**selector.py:**
- Adaptive question selection algorithm
- Information gain calculation
- Strategy: constraints first -> needs -> refinement

**explainer.py:**
- Generate explanations for each object score
- Why object is in top / excluded
- Which needs satisfied / constraints violated

### 4. ports/ - Abstract Interfaces

```python
class CatalogRepository(ABC):
    @abstractmethod
    def get_catalog(self, catalog_id: str) -> list[CatalogObject]: ...

    @abstractmethod
    def get_characteristics(self, catalog_id: str) -> list[Characteristic]: ...

class SessionRepository(ABC):
    @abstractmethod
    def save(self, session: Session) -> None: ...

    @abstractmethod
    def get(self, session_id: str) -> Session | None: ...

    @abstractmethod
    def delete(self, session_id: str) -> None: ...
```

---

## Domain Projects

Each domain is a **separate project** with its own database, content, and configuration.
Core library is shared, but all domain-specific data is isolated.

```
domains/
└── dog_breeds/                    # Domain project: Dog Breeds
    │
    ├── data-spec.md               # Domain specification
    │
    ├── content/                   # Static content (version-controlled)
    │   ├── meta/
    │   │   ├── manifest.json      # Content version, checksums
    │   │   └── locales/
    │   │       ├── en.json
    │   │       └── ru.json
    │   │
    │   ├── schemas/               # JSON schemas for validation
    │   │   ├── feature_schema.json
    │   │   ├── criteria_schema.json
    │   │   └── question_schema.json
    │   │
    │   ├── features/              # Feature definitions
    │   │   ├── breed_features.json    # Feature basis (energy, size, ...)
    │   │   └── derived_features.json  # Computed features
    │   │
    │   ├── breeds/                # Object catalog
    │   │   ├── index.json         # Breed list with versions
    │   │   └── breeds.jsonl       # Breed data (one per line)
    │   │
    │   ├── criteria/              # Needs and constraints
    │   │   ├── needs.json
    │   │   ├── constraints.json
    │   │   └── derived_criteria.json
    │   │
    │   ├── questions/             # Survey questions by blocks
    │   │   ├── blocks.json        # Block order (constraints → purpose → lifestyle)
    │   │   ├── q_experience.json
    │   │   ├── q_purpose.json
    │   │   ├── q_housing.json
    │   │   ├── q_activity.json
    │   │   ├── q_children.json
    │   │   └── ...
    │   │
    │   ├── rules/                 # Automation rules
    │   │   ├── purpose_rules.json     # purpose → criteria weights
    │   │   ├── auto_weight_rules.json # experience/housing → criteria
    │   │   ├── disable_rules.json     # Question disable logic
    │   │   ├── gating_rules.json      # Question order strategy
    │   │   └── normalization_rules.json
    │   │
    │   ├── explanation/           # Explanation templates
    │   │   ├── criteria_texts.json
    │   │   ├── conflict_texts.json
    │   │   └── pros_cons_mapping.json
    │   │
    │   └── scoring/               # Scoring configuration
    │       ├── scoring_config.json    # Thresholds, weights, formula
    │       └── sat_semantics.json     # Fuzzy logic rules
    │
    ├── scripts/                   # Domain-specific scripts
    │   ├── miner.py               # Feature extraction (rules + LLM)
    │   └── validate.py            # Content validation
    │
    ├── cache/                     # LLM response cache
    │   └── llm_responses.json
    │
    └── data/                      # Runtime data (DB, not in git)
        ├── sessions.db            # SQLite database
        └── .gitkeep

```

**Key principles:**
1. **Domain isolation** — each domain has its own DB, content, rules
2. **Core is shared** — `src/query_planner/` used by all domains
3. **Content versioning** — `manifest.json` tracks content version
4. **No cross-domain dependencies** — domains don't reference each other

### Domain Database (SQLite)

Each domain has its own `data/sessions.db`:

```sql
-- Sessions
sessions (
    id TEXT PRIMARY KEY,
    content_version TEXT,      -- For reproducibility
    locale TEXT,
    status TEXT,               -- active/completed
    created_at, updated_at
)

-- Raw answers
session_answers (
    session_id, question_id, answer_id,
    answered_at, payload_json
)

-- Aggregated state
session_user_factors (
    session_id PRIMARY KEY,
    user_factors_json,         -- owner_experience, purpose, housing, ...
    updated_at
)

session_criteria_weights (
    session_id PRIMARY KEY,
    weights_json,              -- {need_id: weight, constraint_id: weight, ...}
    updated_at
)

session_question_state (
    session_id PRIMARY KEY,
    asked_json, disabled_json, available_json,
    updated_at
)

-- Scoring snapshots (for debug/analytics)
session_scoring_runs (
    id, session_id, run_no,
    trigger,                   -- answer_submitted/manual/resume
    params_json, created_at
)

session_breed_scores (
    run_id, breed_id,
    score, needs_score, constraints_penalty,
    hard_excluded, rank,
    details_json               -- per-criterion breakdown
)

session_recommendation (
    session_id PRIMARY KEY,
    run_id,                    -- latest run
    top_json,                  -- top-N with explanations
    excluded_json,             -- excluded with reasons
    next_question_id,
    updated_at
)

-- Rule trace (optional, for debugging)
session_rule_trace (
    run_id, rule_id, rule_type,
    applied, diff_json, created_at
)
```

### domain.json (metadata)
```json
{
  "id": "dog_breeds",
  "name": "Dog Breed Selector",
  "description": "Find the perfect dog breed for your lifestyle",
  "version": "1.0.0",
  "locale": "en"
}
```

---

## JSON Schema Examples

### catalog.json
```json
{
  "characteristics": [
    {"id": "energy", "name": "Energy Level", "description": "Activity and exercise needs"},
    {"id": "trainability", "name": "Trainability", "description": "Ease of training"},
    {"id": "shedding", "name": "Shedding", "description": "Amount of hair shedding"},
    {"id": "size", "name": "Size", "description": "Adult dog size"},
    {"id": "child_friendly", "name": "Child Friendly", "description": "Good with children"},
    {"id": "apartment_ok", "name": "Apartment Suitable", "description": "Can live in apartment"}
  ],
  "objects": [
    {
      "id": "labrador",
      "name": "Labrador Retriever",
      "features": {
        "energy": 0.8,
        "trainability": 0.9,
        "shedding": 0.7,
        "size": 0.7,
        "child_friendly": 0.95,
        "apartment_ok": 0.3
      },
      "metadata": {"origin": "Canada", "lifespan": "10-12 years", "group": "Sporting"}
    },
    {
      "id": "french_bulldog",
      "name": "French Bulldog",
      "features": {
        "energy": 0.4,
        "trainability": 0.6,
        "shedding": 0.3,
        "size": 0.25,
        "child_friendly": 0.85,
        "apartment_ok": 0.95
      },
      "metadata": {"origin": "France", "lifespan": "10-12 years", "group": "Non-Sporting"}
    }
  ]
}
```

### formulas.json
```json
{
  "needs": [
    {
      "id": "active_lifestyle",
      "name": "Active Lifestyle Companion",
      "formula": {"clauses": [[{"var": "energy"}]]}
    },
    {
      "id": "easy_training",
      "name": "Easy to Train",
      "formula": {"clauses": [[{"var": "trainability"}]]}
    },
    {
      "id": "family_dog",
      "name": "Family Dog",
      "formula": {"clauses": [[{"var": "child_friendly"}]]}
    }
  ],
  "constraints": [
    {
      "id": "low_shedding",
      "name": "Low Shedding Required",
      "formula": {"clauses": [[{"var": "shedding", "negated": true}]]}
    },
    {
      "id": "apartment_living",
      "name": "Must Be Apartment Suitable",
      "formula": {"clauses": [[{"var": "apartment_ok"}]]}
    },
    {
      "id": "small_size",
      "name": "Small Size Required",
      "formula": {"clauses": [[{"var": "size", "negated": true}]]}
    }
  ]
}
```

### questions.json
```json
{
  "questions": [
    {
      "id": "q_living",
      "text": "Where do you live?",
      "priority": 100,
      "answers": [
        {
          "id": "apartment",
          "text": "Apartment or condo",
          "updates": [
            {"target": "apartment_living", "type": "constraint", "op": "set", "value": 0.9}
          ],
          "disables": ["q_yard_size"]
        },
        {
          "id": "house_small_yard",
          "text": "House with small yard",
          "updates": [
            {"target": "apartment_living", "type": "constraint", "op": "set", "value": 0.3}
          ]
        },
        {
          "id": "house_large_yard",
          "text": "House with large yard",
          "updates": []
        }
      ]
    },
    {
      "id": "q_activity_level",
      "text": "How active is your lifestyle?",
      "priority": 90,
      "answers": [
        {
          "id": "very_active",
          "text": "Very active - daily runs, hiking, outdoor activities",
          "updates": [
            {"target": "active_lifestyle", "type": "need", "op": "set", "value": 0.9}
          ]
        },
        {
          "id": "moderate",
          "text": "Moderate - daily walks, occasional activities",
          "updates": [
            {"target": "active_lifestyle", "type": "need", "op": "set", "value": 0.5}
          ]
        },
        {
          "id": "low",
          "text": "Low activity - prefer relaxed lifestyle",
          "updates": [
            {"target": "active_lifestyle", "type": "need", "op": "set", "value": 0.1}
          ]
        }
      ]
    },
    {
      "id": "q_children",
      "text": "Do you have children?",
      "priority": 80,
      "answers": [
        {
          "id": "young_children",
          "text": "Yes, young children (under 10)",
          "updates": [
            {"target": "family_dog", "type": "need", "op": "set", "value": 1.0}
          ]
        },
        {
          "id": "older_children",
          "text": "Yes, older children or teenagers",
          "updates": [
            {"target": "family_dog", "type": "need", "op": "set", "value": 0.7}
          ]
        },
        {
          "id": "no_children",
          "text": "No children",
          "updates": []
        }
      ]
    },
    {
      "id": "q_shedding",
      "text": "How important is low shedding to you?",
      "priority": 70,
      "answers": [
        {
          "id": "very_important",
          "text": "Very important - allergies or clean home priority",
          "updates": [
            {"target": "low_shedding", "type": "constraint", "op": "set", "value": 0.95}
          ]
        },
        {
          "id": "somewhat",
          "text": "Somewhat important",
          "updates": [
            {"target": "low_shedding", "type": "constraint", "op": "set", "value": 0.5}
          ]
        },
        {
          "id": "not_important",
          "text": "Not important",
          "updates": []
        }
      ]
    }
  ]
}
```

---

## CLI Interface

**Commands:**

```bash
# List available domains
qplanner domains

# Start interactive survey for a domain
qplanner survey dog_breeds
qplanner survey --domain ./domains/dog_breeds/

# Validate domain configuration files
qplanner validate dog_breeds
qplanner validate ./domains/dog_breeds/

# Show domain info (breeds count, questions count, etc.)
qplanner info dog_breeds

# Resume session
qplanner survey --resume <session_id>

# Export results
qplanner results <session_id> --format json|table

# List sessions
qplanner sessions --domain dog_breeds
```

**Interactive Survey Flow:**
1. Load catalog, formulas, questions
2. Create or resume session
3. Loop: show question -> get answer -> update profile -> show current top-3
4. When stable or no more questions: show final results with explanations

---

## Key Design Decisions

### 1. Ports & Adapters Pattern
- Core has no knowledge of JSON/SQLite/CLI
- All I/O through abstract interfaces (ports)
- Easy to add REST API, GraphQL, or GUI later

### 2. Stateless Core
- SurveyEngine is stateless, receives Session object
- Session contains all state (profile, answers, disabled questions)
- Enables easy scaling and testing

### 3. Formula Representation
- CNF (Conjunctive Normal Form) for formulas
- Simple JSON serialization
- Efficient fuzzy evaluation

### 4. Extensibility Points
- New catalogs: add JSON files
- New question selection strategies: implement selector interface
- New interfaces: implement CLI-like wrapper using SurveyEngine

---

## Implementation Order

1. **Phase 1: Core Models**
   - Domain models (dataclasses)
   - JSON schema definitions

2. **Phase 2: Scoring Engine**
   - Fuzzy logic evaluation
   - Scoring and ranking

3. **Phase 3: Adapters**
   - JSON file loading
   - SQLite session persistence

4. **Phase 4: Survey Engine**
   - Question selection
   - Survey orchestration
   - Explainer

5. **Phase 5: CLI**
   - Commands implementation
   - Interactive survey mode

6. **Phase 6: Dog Breeds Domain**
   - Data converter (see `domains/dog_breeds/data-spec.md`)
   - 170+ breeds from existing dataset
   - Unit and integration tests

---

## Verification Plan

1. **Unit tests**: scoring, fuzzy logic, ranking
2. **Integration test**: full survey flow with dog_breeds domain
3. **Manual CLI test**: interactive survey with dog breeds
4. **Validate**: JSON schema validation for domain files
5. **Domain test**: verify all breeds have valid features, all formulas reference existing characteristics
