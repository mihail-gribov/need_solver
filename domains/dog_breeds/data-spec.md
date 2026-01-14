# Dog Breeds Domain - Data Specification

## Overview

Domain project for dog breed recommendation system.
Source data: doggypedia (170+ breeds).

---

## Directory Structure

```
domains/dog_breeds/
│
├── data-spec.md                   # This file
│
├── content/                       # Static content (version-controlled)
│   ├── meta/
│   │   ├── manifest.json          # Content version, checksums
│   │   └── locales/
│   │       ├── en.json
│   │       └── ru.json
│   │
│   ├── schemas/                   # JSON schemas for validation
│   │   ├── feature_schema.json
│   │   ├── criteria_schema.json
│   │   └── question_schema.json
│   │
│   ├── features/                  # Feature definitions
│   │   ├── breed_features.json    # Feature basis X(o)
│   │   └── user_factors.json      # User profile factors
│   │
│   ├── breeds/                    # Object catalog
│   │   ├── index.json             # Breed list with versions
│   │   └── breeds.jsonl           # Breed data (one JSON per line)
│   │
│   ├── criteria/                  # Needs and constraints
│   │   ├── needs.json
│   │   ├── constraints.json
│   │   └── derived_criteria.json
│   │
│   ├── questions/                 # Survey questions by blocks
│   │   ├── blocks.json            # Block order
│   │   ├── q_experience.json
│   │   ├── q_purpose.json
│   │   ├── q_housing.json
│   │   ├── q_absence.json
│   │   ├── q_allergies.json
│   │   ├── q_children.json
│   │   ├── q_pets.json
│   │   ├── q_activity.json
│   │   └── q_preferences.json
│   │
│   ├── rules/                     # Automation rules
│   │   ├── purpose_rules.json
│   │   ├── auto_weight_rules.json
│   │   ├── disable_rules.json
│   │   ├── gating_rules.json
│   │   └── normalization_rules.json
│   │
│   ├── explanation/               # Explanation templates
│   │   ├── criteria_texts.json
│   │   ├── conflict_texts.json
│   │   └── pros_cons_mapping.json
│   │
│   └── scoring/                   # Scoring configuration
│       ├── scoring_config.json
│       └── sat_semantics.json
│
├── scripts/                       # Domain scripts
│   ├── miner.py                   # Feature extraction (rules + LLM)
│   └── validate.py                # Content validation
│
├── cache/                         # LLM response cache (not in git)
│   └── llm_responses.json
│
└── data/                          # Runtime data (not in git)
    ├── sessions.db                # SQLite database
    └── .gitkeep
```

---

## Source Data

**Location:** `/home/mike/Projects/neweb/projects/doggypedia/data/processed/`

**Files:**
- `breed_<id>.json` — English version
- `breed_<id>_rus.json` — Russian version
- `common.json` — breed list with aliases

**Coverage:** 170+ breeds

### Source Structure (breed_*.json)

```json
{
  "id": "labrador-retriever",
  "name": "Labrador Retriever",
  "full_description": "...",
  "parameters": {
    "size": "medium / large",
    "weight": "Males: 65-80 lbs",
    "height": "Males: 22.5-24.5 inches",
    "coat": "short, dense, water-resistant double coat",
    "activity": "high",
    "trainability": "very high",
    "grooming": "regular brushing",
    "lifespan": "10-12 years"
  },
  "behavior": {
    "summary": "...",
    "with_family": "...",
    "with_children": "...",
    "with_other_pets": "...",
    "with_strangers": "...",
    "special_traits": [...]
  },
  "health": {
    "common_issues": [...],
    "prevention_tips": [...]
  },
  "care": {...},
  "faq": [...],
  "sources": [...]
}
```

---

## Content Files Specification

### content/meta/manifest.json

```json
{
  "domain_id": "dog_breeds",
  "domain_name": "Dog Breed Selector",
  "version": "1.0.0",
  "locale": "en",
  "description": "Find the perfect dog breed for your lifestyle",
  "breeds_count": 170,
  "created_at": "2025-01-11",
  "checksums": {
    "breeds": "sha256:...",
    "criteria": "sha256:...",
    "questions": "sha256:..."
  }
}
```

---

### content/features/breed_features.json

Feature basis for breed vectors X(o) = [x1, ..., xd], xi ∈ [0,1].

```json
{
  "features": [
    {
      "id": "energy",
      "name": "Energy Level",
      "description": "Activity and exercise needs",
      "type": "float01",
      "extraction": {
        "method": "RULE",
        "source": "parameters.activity",
        "mapping": {"very low": 0.1, "low": 0.3, "moderate": 0.5, "high": 0.7, "very high": 0.9}
      }
    },
    {
      "id": "trainability",
      "name": "Trainability",
      "description": "Ease of training",
      "type": "float01",
      "extraction": {
        "method": "RULE",
        "source": "parameters.trainability",
        "mapping": {"very low": 0.1, "low": 0.3, "moderate": 0.5, "high": 0.7, "very high": 0.9}
      }
    },
    {
      "id": "size",
      "name": "Size",
      "description": "Physical size",
      "type": "float01",
      "extraction": {
        "method": "RULE",
        "source": "parameters.size",
        "mapping": {"toy": 0.1, "small": 0.25, "medium": 0.5, "large": 0.75, "giant": 0.95}
      }
    },
    {
      "id": "lifespan",
      "name": "Lifespan",
      "description": "Expected lifespan",
      "type": "float01",
      "extraction": {
        "method": "RULE",
        "source": "parameters.lifespan",
        "normalize": {"min_years": 8, "max_years": 18}
      }
    },
    {
      "id": "grooming",
      "name": "Grooming Needs",
      "description": "Maintenance effort required",
      "type": "float01",
      "extraction": {
        "method": "LLM_EXTRACT",
        "sources": ["parameters.grooming", "care.grooming"]
      }
    },
    {
      "id": "shedding",
      "name": "Shedding Level",
      "description": "Amount of hair shedding",
      "type": "float01",
      "extraction": {
        "method": "LLM_EXTRACT",
        "sources": ["parameters.coat", "parameters.grooming"]
      }
    },
    {
      "id": "child_friendly",
      "name": "Good with Children",
      "description": "Safety and patience with kids",
      "type": "float01",
      "extraction": {
        "method": "LLM_EXTRACT",
        "sources": ["behavior.with_children"]
      }
    },
    {
      "id": "pet_friendly",
      "name": "Good with Other Pets",
      "description": "Compatibility with other animals",
      "type": "float01",
      "extraction": {
        "method": "LLM_EXTRACT",
        "sources": ["behavior.with_other_pets"]
      }
    },
    {
      "id": "stranger_friendly",
      "name": "Friendly to Strangers",
      "description": "Openness vs wariness to strangers",
      "type": "float01",
      "extraction": {
        "method": "LLM_EXTRACT",
        "sources": ["behavior.with_strangers"]
      }
    },
    {
      "id": "barking",
      "name": "Barking Tendency",
      "description": "Vocalization level",
      "type": "float01",
      "extraction": {
        "method": "LLM_EXTRACT",
        "sources": ["behavior.special_traits", "full_description"]
      }
    },
    {
      "id": "independence",
      "name": "Independence",
      "description": "Can be left alone vs needs constant attention",
      "type": "float01",
      "extraction": {
        "method": "LLM_GENERATE"
      }
    },
    {
      "id": "apartment_ok",
      "name": "Apartment Suitable",
      "description": "Suitability for apartment living",
      "type": "float01",
      "extraction": {
        "method": "LLM_GENERATE"
      }
    },
    {
      "id": "health_robustness",
      "name": "Health Robustness",
      "description": "General health and low disease risk",
      "type": "float01",
      "extraction": {
        "method": "LLM_EXTRACT",
        "sources": ["health.common_issues"]
      }
    }
  ]
}
```

**Extraction Methods:**
| Method | Description |
|--------|-------------|
| `RULE` | Direct mapping from structured field |
| `LLM_EXTRACT` | LLM extracts score from existing text |
| `LLM_GENERATE` | LLM generates score (no source text) |

---

### content/features/user_factors.json

User profile factors derived from answers.

```json
{
  "factors": [
    {
      "id": "owner_experience",
      "name": "Owner Experience",
      "type": "composite",
      "components": {
        "animal_handling": {"type": "float01", "default": 0.5},
        "dog_training": {"type": "float01", "default": 0.5},
        "behavior_management": {"type": "float01", "default": 0.5}
      }
    },
    {
      "id": "purpose",
      "name": "Purpose",
      "type": "onehot_soft",
      "options": ["companion", "family", "guard", "sport", "work"]
    },
    {
      "id": "housing",
      "name": "Housing",
      "type": "composite",
      "components": {
        "type": {"type": "enum", "options": ["apartment", "house_small", "house_large", "farm"]},
        "has_yard": {"type": "bool", "default": false},
        "neighbors_sensitivity": {"type": "float01", "default": 0.5}
      }
    },
    {
      "id": "absence_daily",
      "name": "Daily Absence",
      "type": "float01",
      "description": "Hours away from home daily (0=always home, 1=10+ hours)"
    },
    {
      "id": "absence_trips",
      "name": "Travel Frequency",
      "type": "composite",
      "components": {
        "frequency": {"type": "float01"},
        "typical_duration_days": {"type": "int"}
      }
    },
    {
      "id": "backup_care",
      "name": "Backup Care Availability",
      "type": "float01",
      "description": "Access to pet sitters, family, etc."
    }
  ]
}
```

---

### content/breeds/breeds.jsonl

One breed per line (JSONL format for efficient loading).

```jsonl
{"id": "labrador-retriever", "name": "Labrador Retriever", "features": {"energy": 0.7, "trainability": 0.9, "size": 0.65, ...}, "facts": {"origin": "Canada", "lifespan": "10-12 years", ...}}
{"id": "golden-retriever", "name": "Golden Retriever", "features": {"energy": 0.7, "trainability": 0.9, "size": 0.65, ...}, "facts": {...}}
...
```

---

### content/criteria/needs.json

```json
{
  "needs": [
    {
      "id": "active_companion",
      "name": "Active Companion",
      "description": "Want energetic dog for activities",
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "energy", "neg": false}]]
      }
    },
    {
      "id": "easy_to_train",
      "name": "Easy to Train",
      "description": "Want dog that learns quickly",
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "trainability", "neg": false}]]
      }
    },
    {
      "id": "family_friendly",
      "name": "Family Friendly",
      "description": "Safe for children and other pets",
      "formula": {
        "type": "cnf",
        "clauses": [
          [{"var": "child_friendly", "neg": false}],
          [{"var": "pet_friendly", "neg": false}]
        ]
      }
    },
    {
      "id": "low_maintenance",
      "name": "Low Maintenance",
      "description": "Minimal grooming effort",
      "formula": {
        "type": "cnf",
        "clauses": [
          [{"var": "grooming", "neg": true}],
          [{"var": "shedding", "neg": true}]
        ]
      }
    },
    {
      "id": "apartment_suitable",
      "name": "Apartment Living",
      "description": "Can live in small space",
      "formula": {
        "type": "cnf",
        "clauses": [
          [{"var": "apartment_ok", "neg": false}],
          [{"var": "barking", "neg": true}]
        ]
      }
    },
    {
      "id": "can_be_alone",
      "name": "Can Be Left Alone",
      "description": "Independent, tolerates absence",
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "independence", "neg": false}]]
      }
    },
    {
      "id": "long_lived",
      "name": "Long Lifespan",
      "description": "Healthy, long-living breed",
      "formula": {
        "type": "cnf",
        "clauses": [
          [{"var": "lifespan", "neg": false}],
          [{"var": "health_robustness", "neg": false}]
        ]
      }
    },
    {
      "id": "social",
      "name": "Social Dog",
      "description": "Friendly with everyone",
      "formula": {
        "type": "cnf",
        "clauses": [
          [{"var": "stranger_friendly", "neg": false}],
          [{"var": "pet_friendly", "neg": false}]
        ]
      }
    }
  ]
}
```

---

### content/criteria/constraints.json

```json
{
  "constraints": [
    {
      "id": "no_shedding",
      "name": "No Shedding",
      "description": "Allergies or clean home priority",
      "hard_threshold": 0.9,
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "shedding", "neg": true}]]
      }
    },
    {
      "id": "must_be_small",
      "name": "Small Size Only",
      "description": "Space or handling limitations",
      "hard_threshold": 0.8,
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "size", "neg": true}]]
      }
    },
    {
      "id": "must_be_large",
      "name": "Large Size Only",
      "description": "Want big dog",
      "hard_threshold": 0.8,
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "size", "neg": false}]]
      }
    },
    {
      "id": "low_energy_only",
      "name": "Low Energy Only",
      "description": "Limited exercise capacity",
      "hard_threshold": 0.7,
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "energy", "neg": true}]]
      }
    },
    {
      "id": "child_safe",
      "name": "Must Be Child Safe",
      "description": "Non-negotiable for families with children",
      "hard_threshold": 0.95,
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "child_friendly", "neg": false}]]
      }
    },
    {
      "id": "pet_compatible",
      "name": "Must Accept Other Pets",
      "description": "Existing pets in home",
      "hard_threshold": 0.8,
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "pet_friendly", "neg": false}]]
      }
    },
    {
      "id": "quiet_required",
      "name": "Must Be Quiet",
      "description": "Noise-sensitive environment",
      "hard_threshold": 0.8,
      "formula": {
        "type": "cnf",
        "clauses": [[{"var": "barking", "neg": true}]]
      }
    }
  ]
}
```

---

### content/questions/blocks.json

Question block order and strategy.

```json
{
  "blocks": [
    {
      "id": "constraints_first",
      "name": "Hard Constraints",
      "description": "Eliminate incompatible breeds early",
      "questions": ["q_allergies", "q_housing", "q_children", "q_pets"]
    },
    {
      "id": "purpose",
      "name": "Purpose & Lifestyle",
      "description": "Understand what user wants",
      "questions": ["q_purpose", "q_experience", "q_activity"]
    },
    {
      "id": "lifestyle",
      "name": "Daily Life",
      "description": "Practical considerations",
      "questions": ["q_absence", "q_backup_care", "q_grooming_time"]
    },
    {
      "id": "preferences",
      "name": "Preferences",
      "description": "Fine-tuning",
      "questions": ["q_size_preference", "q_appearance"]
    }
  ],
  "strategy": "constraints_first_then_information_gain"
}
```

---

### content/questions/q_housing.json

```json
{
  "id": "q_housing",
  "block": "constraints_first",
  "text": {
    "en": "Where will your dog live?",
    "ru": "Где будет жить ваша собака?"
  },
  "answers": [
    {
      "id": "apartment",
      "text": {"en": "Apartment or condo", "ru": "Квартира"},
      "effects": [
        {"target": "housing.type", "op": "set", "value": "apartment"},
        {"target": "housing.has_yard", "op": "set", "value": false}
      ],
      "criteria_updates": [
        {"target": "apartment_suitable", "type": "need", "op": "set", "value": 0.9},
        {"target": "must_be_small", "type": "constraint", "op": "set", "value": 0.6},
        {"target": "quiet_required", "type": "constraint", "op": "set", "value": 0.7}
      ],
      "disables": ["q_yard_size"]
    },
    {
      "id": "house_small_yard",
      "text": {"en": "House with small yard", "ru": "Дом с небольшим двором"},
      "effects": [
        {"target": "housing.type", "op": "set", "value": "house_small"},
        {"target": "housing.has_yard", "op": "set", "value": true}
      ],
      "criteria_updates": []
    },
    {
      "id": "house_large_yard",
      "text": {"en": "House with large yard", "ru": "Дом с большим двором"},
      "effects": [
        {"target": "housing.type", "op": "set", "value": "house_large"},
        {"target": "housing.has_yard", "op": "set", "value": true}
      ],
      "criteria_updates": []
    },
    {
      "id": "farm",
      "text": {"en": "Farm or rural property", "ru": "Ферма или загородный дом"},
      "effects": [
        {"target": "housing.type", "op": "set", "value": "farm"},
        {"target": "housing.has_yard", "op": "set", "value": true}
      ],
      "criteria_updates": [
        {"target": "active_companion", "type": "need", "op": "add", "value": 0.2}
      ]
    }
  ]
}
```

---

### content/rules/purpose_rules.json

```json
{
  "rules": [
    {
      "id": "purpose_companion",
      "condition": {"factor": "purpose", "value": "companion", "min_weight": 0.5},
      "effects": [
        {"target": "social", "type": "need", "op": "set", "value": 0.7},
        {"target": "easy_to_train", "type": "need", "op": "add", "value": 0.2}
      ]
    },
    {
      "id": "purpose_family",
      "condition": {"factor": "purpose", "value": "family", "min_weight": 0.5},
      "effects": [
        {"target": "family_friendly", "type": "need", "op": "set", "value": 0.9},
        {"target": "child_safe", "type": "constraint", "op": "set", "value": 0.8}
      ]
    },
    {
      "id": "purpose_guard",
      "condition": {"factor": "purpose", "value": "guard", "min_weight": 0.5},
      "effects": [
        {"target": "must_be_large", "type": "constraint", "op": "set", "value": 0.6}
      ]
    }
  ]
}
```

---

### content/rules/auto_weight_rules.json

```json
{
  "rules": [
    {
      "id": "novice_needs_easy",
      "condition": {"factor": "owner_experience.dog_training", "op": "<", "value": 0.3},
      "effects": [
        {"target": "easy_to_train", "type": "need", "op": "set", "value": 0.9}
      ]
    },
    {
      "id": "long_absence_needs_independence",
      "condition": {"factor": "absence_daily", "op": ">", "value": 0.6},
      "effects": [
        {"target": "can_be_alone", "type": "need", "op": "set", "value": 0.8}
      ]
    }
  ]
}
```

---

### content/scoring/scoring_config.json

```json
{
  "formula": "Score(o) = NeedsScore(o) × ConstraintsPenalty(o)",
  "needs_aggregation": "weighted_average",
  "constraints_aggregation": "product",
  "hard_constraint_threshold": 0.9,
  "soft_constraint_penalty": "linear",
  "default_need_weight": 0.5,
  "default_constraint_weight": 0.0,
  "top_n": 10
}
```

---

### content/scoring/sat_semantics.json

```json
{
  "literal": {
    "positive": "x",
    "negative": "1 - x"
  },
  "clause": {
    "operator": "max",
    "description": "OR = max of literals"
  },
  "formula": {
    "operator": "weighted_average",
    "weights": "1/clause_size",
    "description": "AND = weighted average, smaller clauses have more weight"
  }
}
```

---

## Scripts

### scripts/miner.py

Feature extraction script using rules and LLM.

**Pipeline:**
```
Source Data → RULE extraction → LLM_EXTRACT → LLM_GENERATE → Validation → breeds.jsonl
```

**Usage:**
```bash
# Full extraction
python scripts/miner.py --source /path/to/doggypedia/data/processed

# Rules only (no LLM)
python scripts/miner.py --source ... --rules-only

# Specific breeds
python scripts/miner.py --source ... --breeds labrador-retriever,golden-retriever

# Force re-extract
python scripts/miner.py --source ... --no-cache
```

**LLM Prompt (LLM_EXTRACT):**
```
You are a dog breed expert. Analyze the text and rate the characteristic.

Breed: {breed_name}
Characteristic: {characteristic_name} - {characteristic_description}

Source text:
---
{source_text}
---

Rate on scale 0.0 to 1.0.
Respond with JSON: {"score": 0.XX, "reasoning": "brief explanation"}
```

**LLM Prompt (LLM_GENERATE):**
```
You are a dog breed expert. Rate the breed based on your knowledge.

Breed: {breed_name}
Characteristic: {characteristic_name} - {characteristic_description}

Rate on scale 0.0 to 1.0.
Respond with JSON: {"score": 0.XX, "reasoning": "brief explanation"}
```

---

### scripts/validate.py

Content validation script.

**Checks:**
1. All breeds have all required features
2. All feature values in [0, 1]
3. All criteria reference existing features
4. All questions reference existing criteria
5. All rules reference existing factors/criteria
6. Schema validation for all JSON files

---

## Database (data/sessions.db)

SQLite database for runtime session data.

```sql
-- Sessions
sessions (id, content_version, locale, status, created_at, updated_at)

-- Answers
session_answers (session_id, question_id, answer_id, answered_at, payload_json)

-- Aggregated state
session_user_factors (session_id, user_factors_json, updated_at)
session_criteria_weights (session_id, weights_json, updated_at)
session_question_state (session_id, asked_json, disabled_json, updated_at)

-- Scoring
session_scoring_runs (id, session_id, run_no, trigger, params_json, created_at)
session_breed_scores (run_id, breed_id, score, needs_score, constraints_penalty, rank, details_json)
session_recommendation (session_id, run_id, top_json, excluded_json, next_question_id, updated_at)
```

---

## Validation Checklist

- [ ] All 170+ breeds extracted with complete feature vectors
- [ ] All features in [0, 1] range
- [ ] No null/NaN values
- [ ] All criteria formulas valid
- [ ] All questions have valid effects
- [ ] All rules reference existing entities
- [ ] Schema validation passes
- [ ] LLM cache populated for reproducibility
