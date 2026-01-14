# User Space Specification

Each element is a **user-space axis** represented as **(T, F)** vector using fuzzy4.

Axes can be:
- Desires (needs)
- Prohibitions (constraints)
- Context facts (allergies, housing, absence)
- Environment constraints

---

## 1. Health / Allergies

Context facts → critical axes.

1. **low_shedding** — minimal shedding
   → `¬shedding`

2. **hypoallergenic** — minimal allergenicity
   → `¬shedding ∧ ¬coat_smell_proneness`

3. **low_smell** — minimal odor
   → `¬coat_smell_proneness`

4. **health_robust** — breed health
   → `health_robustness`

5. **low_vet_costs** — low expected vet expenses
   → `health_robustness ∧ ¬genetic_risk`

---

## 2. Housing / Environment

Strong filters.

6. **apartment_compatible** — suitable for apartment
   → `apartment_compatibility ∧ ¬barking_level ∧ ¬energy_level`

7. **small_space_ok** — comfortable in limited space
   → `¬size_large ∧ ¬size_giant ∧ ¬energy_level`

8. **low_barking** — rarely barks
   → `¬barking_level`

9. **urban_tolerant** — comfortable in city
   → `urban_tolerance ∧ ¬reactivity`

10. **yard_independent** — doesn't need constant yard access
    → `¬exercise_need`

---

## 3. Daily Schedule / Absence

Key failure zone in reality.

11. **tolerates_daily_absence** — handles daily solitude
    → `alone_tolerance ∧ ¬separation_anxiety_risk`

12. **low_separation_anxiety** — low separation anxiety risk
    → `¬separation_anxiety_risk`

13. **sitter_compatible** — easily stays with another person
    → `sitter_compatibility`

14. **travel_flexible** — suitable for trips/business travel
    → `sitter_compatibility ∧ environment_adaptability`

---

## 4. Family / Social Environment

15. **child_friendly** — safe and comfortable with children
    → `child_friendly`

16. **pet_friendly** — gets along with other animals
    → `pet_friendly`

17. **stranger_friendly** — friendly to strangers
    → `stranger_friendly`

18. **not_overprotective** — not prone to excessive guarding
    → `¬territoriality ∧ ¬protectiveness`

---

## 5. Behavior / Character

What user perceives as "fits / doesn't fit".

19. **low_reactivity** — calm response to stimuli
    → `¬reactivity`

20. **emotionally_stable** — predictable temperament
    → `emotional_stability`

21. **affectionate** — human-oriented
    → `affection_level`

22. **independent_ok** — independence acceptable
    → `independence`

23. **playful** — playful nature
    → `playfulness`

---

## 6. Activity / Lifestyle

24. **low_energy** — low activity requirement
    → `¬energy_level`

25. **high_energy** — high activity desired
    → `energy_level`

26. **long_walks_ok** — okay with long walks
    → `exercise_need`

27. **mental_stimulation_ok** — ready for mental load
    → `mental_stimulation_need`

---

## 7. Training / Management

Critical for "first-time / experienced" matching.

28. **easy_to_train** — easy to train
    → `trainability`

29. **first_time_friendly** — suitable for first-time owners
    → `trainability ∧ ¬reactivity ∧ ¬owner_behavior_management_need`

30. **complex_training_ok** — complex training acceptable
    → `trainability ∧ working_drive`

31. **behavior_management_easy** — no complex behavior correction
    → `¬reactivity ∧ ¬owner_behavior_management_need`

---

## 8. Purpose / Role

32. **companion_role** — life companion
    → `affection_level ∧ stranger_friendly`

33. **guard_role** — territory/home protection
    → `territoriality ∧ protectiveness ∧ barking_level`

34. **sport_work_role** — sports / working tasks
    → `energy_level ∧ trainability ∧ working_drive`

35. **hunting_role** — hunting
    → `prey_drive`

---

## 9. Size Constraints

36. **small_size** — small size required
    → `size_toy ∨ size_small`

37. **medium_size** — medium size preferred
    → `size_medium`

38. **large_size_ok** — large size acceptable
    → `size_large ∨ size_giant`

---

## 10. Summary

- **Total:** ~38 axes
- Each axis has **(T, F)** vector (fuzzy4)
- Can be:
  - Activated by answer
  - Remain (0, 0) = UNKNOWN
  - Enter conflict (T ≈ F)

This is the **complete user-space basis** that:
- Covers real-life scenarios
- Doesn't mix causes and facts
- Fully compatible with fuzzy4 optimization model

---

## Key Point

> This is **not** a question list and **not** object feature list.
> This is the **user-space basis** where any question is just a way to set (T, F) values.
