# Role

You are a canine expert and data analyst. Your task is to extract precise numerical characteristics for dog breeds based on available data and web research.

# Task

Extract feature scores for the dog breed: **{{ breed_name }}** (ID: `{{ breed_id }}`).

# Input Data

Existing breed information:
```json
{{ breed_data | tojson(indent=2) }}
```

# Features to Extract

For each feature, collect **multiple values from different sources**. Each source entry contains:
1. **value** (0.0 to 1.0): The characteristic score from this source
2. **confidence** (0.0 to 1.0): How reliable this source is
   - 0.9-1.0 = Official standards (AKC, UKC, FCI)
   - 0.7-0.8 = Veterinary sources, breed clubs
   - 0.5-0.6 = Reputable pet sites (PetMD, Purina)
   - 0.3-0.4 = General sites (Wikipedia, forums)
3. **source**: Name of the source (e.g., "AKC", "PetMD", "Purina")

## Coat & Allergens

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `shedding` | Amount of hair shedding | 0=none, 1=heavy |
| `coat_type` | Coat maintenance complexity | 0=simple/short, 1=complex/long |
| `dander_level` | Amount of dander produced (allergen) | 0=hypoallergenic, 1=high allergen |
| `grooming` | Required grooming effort | 0=minimal, 1=extensive |

## Health

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `health_robustness` | Overall breed health/genetic stability | 0=many issues, 1=very robust |
| `genetic_risk` | Risk of genetic health issues | 0=low risk, 1=high risk |

## Living Conditions

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `apartment_ok` | Apartment suitability | 0=not suitable, 1=ideal |
| `barking` | Barking frequency | 0=silent, 1=very vocal |
| `energy` | Overall energy level | 0=very low, 1=very high |
| `reactivity` | Reaction intensity to stimuli | 0=calm, 1=highly reactive |
| `noise_tolerance` | Tolerance to urban noise/sounds | 0=sensitive, 1=tolerant |
| `exercise_need` | Required daily exercise | 0=minimal, 1=extensive |

## Alone Time & Adaptability

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `alone_tolerance` | Ability to stay alone | 0=cannot be alone, 1=independent |
| `separation_anxiety_risk` | Risk of separation anxiety | 0=low risk, 1=high risk |
| `sitter_compatibility` | Ease of staying with other people | 0=difficult, 1=easy |
| `adaptability` | Ability to adapt to changes | 0=rigid, 1=very adaptable |

## Social Compatibility

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `child_friendly` | Safety and comfort with children | 0=not recommended, 1=excellent |
| `pet_friendly` | Compatibility with other pets | 0=poor, 1=excellent |
| `stranger_friendly` | Friendliness toward strangers | 0=wary, 1=very friendly |
| `territoriality` | Territorial behavior intensity | 0=none, 1=highly territorial |
| `protectiveness` | Protective instinct level | 0=none, 1=highly protective |

## Temperament

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `stress_sensitivity` | Sensitivity to stressful situations | 0=resilient, 1=very sensitive |
| `affection_level` | Human orientation and affection | 0=aloof, 1=very affectionate |
| `independence` | Level of independence from owner | 0=very dependent, 1=very independent |
| `playfulness` | Playfulness and game drive | 0=low, 1=very playful |

## Training & Work

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `trainability` | Ease of training | 0=stubborn, 1=very trainable |
| `working_drive` | Drive for work and tasks | 0=none, 1=very high |
| `behavior_management_need` | Need for behavior correction | 0=easy, 1=needs work |
| `mental_stimulation` | Need for mental challenges | 0=low, 1=high |

## Hunting Instincts

| Feature ID | Description | Scale |
|------------|-------------|-------|
| `prey_drive` | Hunting/prey chase instinct | 0=none, 1=very strong |
| `hunting_instinct` | Hunting behavior tendency | 0=none, 1=very strong |

## Numerical Parameters

For each parameter, collect **ranges from different sources**:

| Parameter | Unit | Description |
|-----------|------|-------------|
| `weight_kg` | kg | Adult weight range |
| `height_cm` | cm | Height at withers range |
| `lifespan_years` | years | Expected lifespan range |

For each source, provide:
- **value**: array `[min, max]` with the range
- **confidence**: source reliability (0.9+ for AKC/FCI/UKC, 0.7-0.8 for breed clubs, 0.5-0.6 for general sites)
- **source**: name of the source

# Output Format

Return ONLY valid JSON with exactly these 31 features and 3 parameters. **All values must be arrays with multiple source entries**.

```json
{
  "breed_id": "{{ breed_id }}",
  "features": {
    "shedding": [
      {"value": 0.8, "confidence": 0.9, "source": "AKC"},
      {"value": 0.7, "confidence": 0.7, "source": "PetMD"}
    ],
    "coat_type": [
      {"value": 0.3, "confidence": 0.9, "source": "AKC"},
      {"value": 0.4, "confidence": 0.6, "source": "Purina"}
    ],
    "dander_level": [...],
    "grooming": [...],
    "health_robustness": [...],
    "genetic_risk": [...],
    "apartment_ok": [...],
    "barking": [...],
    "energy": [...],
    "reactivity": [...],
    "noise_tolerance": [...],
    "exercise_need": [...],
    "alone_tolerance": [...],
    "separation_anxiety_risk": [...],
    "sitter_compatibility": [...],
    "adaptability": [...],
    "child_friendly": [...],
    "pet_friendly": [...],
    "stranger_friendly": [...],
    "territoriality": [...],
    "protectiveness": [...],
    "stress_sensitivity": [...],
    "affection_level": [...],
    "independence": [...],
    "playfulness": [...],
    "trainability": [...],
    "working_drive": [...],
    "behavior_management_need": [...],
    "mental_stimulation": [...],
    "prey_drive": [...],
    "hunting_instinct": [...]
  },
  "parameters": {
    "weight_kg": [
      {"value": [25, 32], "confidence": 0.9, "source": "AKC"},
      {"value": [27, 34], "confidence": 0.7, "source": "Purina"},
      {"value": [25, 30], "confidence": 0.5, "source": "Wikipedia"}
    ],
    "height_cm": [
      {"value": [55, 61], "confidence": 0.9, "source": "AKC"},
      {"value": [53, 60], "confidence": 0.6, "source": "PetMD"}
    ],
    "lifespan_years": [
      {"value": [10, 12], "confidence": 0.9, "source": "AKC"},
      {"value": [11, 13], "confidence": 0.7, "source": "Purina"}
    ]
  },
  "notes": "Brief notes about data quality or breed variations"
}
```

# Guidelines

1. **Use web search** to find values from multiple sources
2. **Collect at least 2-3 source values per feature** when available
3. **Do NOT aggregate values** - keep raw values from each source separately
4. **Confidence reflects source reliability**, not your certainty:
   - 0.9-1.0: AKC, UKC, FCI official standards
   - 0.7-0.8: Veterinary sources, breed clubs, specialized databases
   - 0.5-0.6: Reputable pet sites (PetMD, Purina, VetStreet)
   - 0.3-0.4: General sites (Wikipedia, pet forums)
5. **All 31 features are required** - include at least one source per feature
6. **Return ONLY the JSON**, no additional text
