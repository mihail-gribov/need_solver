# Dog Breeds Domain Architecture

## Overview

Recommendation system for matching user needs to dog breeds using 4-valued fuzzy logic (Belnap-Lukasiewicz).

## Configuration

**All settings must be stored in `config.json`** - single source of truth for:
- LLM model settings (model, temperature, timeout, retries)
- Extraction settings (web search)
- Question generation settings (count per need, answer options)
- Fuzzy logic thresholds
- Directory paths

Scripts must read from `config.json`, not hardcode values.

## Directory Structure

```
domains/dog_breeds/
├── config.json              # Central configuration (ALL SETTINGS HERE)
├── ARCHITECTURE.md          # This file
├── matcher.py               # Core matching engine
├── user_profile.py          # User profile (needs vector)
├── content/                  # Domain knowledge definitions
│   ├── breeds.json          # List of 181 breeds (id, name_en, name_ru)
│   ├── object_features.json # Feature specs + category groups
│   └── user_needs.json      # 38 needs with formulas, organized in blocks
├── source/                   # Raw source data (from external sources)
│   └── breed_*.json
├── extracted/                # LLM-extracted data (value + confidence)
│   └── {breed_id}.json
├── fuzzy/                    # Converted to fuzzy format (t, f vectors)
│   └── {breed_id}.json
├── questions/                # Generated questions for needs
│   └── {need_id}.json
├── prompts/                  # LLM prompt templates (Jinja2)
│   ├── extract_features.prompt.md
│   └── generate_questions.prompt.md
└── scripts/                  # Processing scripts
    ├── extract_features.py   # Extract breed data via LLM + web search
    ├── convert_to_fuzzy.py   # Convert extracted → fuzzy format
    └── generate_questions.py # Generate interview questions
```

## Data Flow

```
source/ → [extract_features.py] → extracted/ → [convert_to_fuzzy.py] → fuzzy/
                  ↓
            OpenAI API
          (with web search)

user_needs.json → [generate_questions.py] → questions/
                          ↓
                    OpenAI API
                  (no web search)
```

## Fuzzy Logic

### 4-Valued States
- **TRUE**: high t, low f
- **FALSE**: low t, high f
- **UNKNOWN**: low t, low f
- **CONFLICT**: high t, high f

### Conversion Formula
```
t = value × confidence
f = (1 - value) × confidence
```

### Answer Mapping
| Answer | t | f | State |
|--------|---|---|-------|
| Да (Yes) | 1.0 | 0.0 | TRUE |
| Нет (No) | 0.0 | 1.0 | FALSE |
| Не знаю | 0.0 | 0.0 | UNKNOWN |
| Мне всё равно | null | null | Skip (not used in formula) |

## Core Components

### UserProfile (user_profile.py)
User as a vector in needs space.

```python
profile = UserProfile()

# Add answers
profile.add_answer("hypoallergenic", "true", "У вас есть аллергия?")
profile.add_answer("guard_role", "independent", "Нужна охрана?")

# Get vector for matching
user_needs = profile.get_needs()  # dict[str, FuzzyBool]

# Serialize/deserialize
data = profile.to_dict()
profile = UserProfile.from_dict(data)
```

Storage:
- `_answers` — raw answer history (all responses)
- `_needs` — computed vector (aggregated FuzzyBool per need)
- `_independent` — needs user doesn't care about

Answer types → fuzzy mapping:
| Answer | (t, f) | State |
|--------|--------|-------|
| true | (1, 0) | TRUE |
| false | (0, 1) | FALSE |
| unknown | (0, 0) | UNKNOWN |
| independent | null | Skip |

Multiple answers to same need → weighted average (consensus).

### BreedMatcher (matcher.py)
Core matching engine with precomputed matrix.

```python
matcher = BreedMatcher()

# Fast matching
results = matcher.match_fast(user_needs, top_k=10)
# Returns: [(breed_id, score), ...]

# With specific breeds
results = matcher.match_fast(user_needs, breed_ids=['poodle', 'bulldog'])

# With details
results = matcher.match_all(user_needs, top_k=10)
# Returns: [MatchResult(breed_id, score, details), ...]
```

Optimizations:
- Pre-compiled formulas (`compile()` at load time)
- Pre-computed eval matrix (breed × need → FuzzyBool)
- O(1) lookup for `evaluate_need()`
- Inline similarity in hot loop

### Question Selection

Select next question by **expected split quality**:
- Simulate answer TRUE → compute all breed scores
- Simulate answer FALSE → compute all breed scores
- Split score = mean(|score_true - score_false|) across all breeds
- Higher split = answer matters more = better question

```python
# Get best next question
best_need, split_score = matcher.select_next_question(
    profile.get_needs(),
    profile.get_answered_need_ids()
)

# Get ranked list of questions
rankings = matcher.get_question_rankings(
    profile.get_needs(),
    profile.get_answered_need_ids(),
    top_k=10
)
```

Performance: ~0.8ms for all 38 questions (52 breeds).

## Key Files

### config.json
Central configuration. All scripts must read settings from here.

### object_features.json
- 31 float features (0-1 scale)
- 3 category groups (size, height, lifespan) with:
  - Base categories (min/max ranges)
  - Derived categories (OR combinations for ordinal ranges)

### user_needs.json
- 38 needs organized in 9 blocks
- Each need has a formula referencing object features
- Formulas use &, |, ~ operators (CNF format)

## Scripts

### extract_features.py
```bash
uv run python scripts/extract_features.py              # All breeds
uv run python scripts/extract_features.py --breed akita
uv run python scripts/extract_features.py --dry-run
```

### convert_to_fuzzy.py
```bash
uv run python scripts/convert_to_fuzzy.py
```

### generate_questions.py
```bash
uv run python scripts/generate_questions.py            # All needs
uv run python scripts/generate_questions.py --need hypoallergenic
uv run python scripts/generate_questions.py --dry-run
```
