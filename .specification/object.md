# Object Feature Basis

Requirements:
- Atomic features (no duplicates)
- Objective (not task-specific)
- Compatible with boolean and fuzzy logic
- Covers all user-space axes

All features normalized to [0,1] except size categories.

---

## 1. Physical / Biology

### 1.1 Size (categorical, one-hot/soft)

1. **size_toy**
2. **size_small**
3. **size_medium**
4. **size_large**
5. **size_giant**

### 1.2 Body (optional)

6. **body_mass**
7. **body_compactness**

### 1.3 Coat

8. **shedding** — shedding intensity
9. **coat_length**
10. **coat_density**
11. **grooming_need**
12. **coat_smell_proneness**

> `hypoallergenic` is derived, not stored

---

## 2. Health

13. **health_robustness**
14. **genetic_risk**
15. **lifespan_expectancy**
16. **vet_cost_level**
17. **heat_tolerance**
18. **cold_tolerance**

---

## 3. Activity / Energy

19. **energy_level**
20. **exercise_need**
21. **mental_stimulation_need**
22. **playfulness**

---

## 4. Behavior / Temperament

23. **reactivity**
24. **stress_sensitivity**
25. **emotional_stability**
26. **impulsivity**

> `emotional_stability ≈ 1 - reactivity - stress_sensitivity` (can be derived)

---

## 5. Sociability

27. **child_friendly**
28. **pet_friendly**
29. **stranger_friendly**
30. **affection_level**
31. **independence**

---

## 6. Vocalization

32. **barking_level**
33. **alertness**

---

## 7. Territoriality / Protection

34. **territoriality**
35. **protectiveness**
36. **prey_drive**

---

## 8. Separation / Adaptation

37. **alone_tolerance**
38. **separation_anxiety_risk**
39. **sitter_compatibility**
40. **environment_adaptability**

---

## 9. Training / Management

41. **trainability**
42. **handler_sensitivity**
43. **stubbornness**
44. **working_drive**

---

## 10. Owner Requirements (meta-features)

Not dog behavior, but what dog "demands" from owner.

45. **owner_animal_handling_need**
46. **owner_dog_training_need**
47. **owner_behavior_management_need**

> Critical for matching owner experience

---

## 11. Environment Compatibility

48. **apartment_compatibility**
49. **urban_tolerance**
50. **travel_tolerance**

---

## 12. Summary

### Minimal Set (~30)

- size (5)
- shedding, grooming_need
- health_robustness, genetic_risk
- energy_level, exercise_need, mental_stimulation_need
- reactivity, stress_sensitivity
- child_friendly, pet_friendly, stranger_friendly
- affection_level, independence
- barking_level
- territoriality
- alone_tolerance, separation_anxiety_risk, sitter_compatibility
- trainability
- owner_*_need (3)
- apartment_compatibility

### Full Set (~50)

All features listed above.

---

## 13. Mapping to User Needs

Each user need k is a formula over these features.

Examples:
- `low_barking` → `¬barking_level`
- `first_time_friendly` → `trainability ∧ ¬reactivity ∧ ¬owner_behavior_management_need`
- `hypoallergenic` → `¬shedding ∧ ¬coat_smell_proneness`

Formulas evaluated using **fuzzy4** (4-valued Belnap-Lukasiewicz logic).
