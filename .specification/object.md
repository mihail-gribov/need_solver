
Требования к списку ниже:

* признаки **атомарные** (не дублируют друг друга),
* максимально **объективные** (не “под задачу пользователя”),
* пригодны для:

  * булевой логики,
  * fuzzy-логики,
  * вывода производных признаков,
* покрывают **все оси user-space**, которые ты описал.

---

# 0) Принципиальная структура

Признаки пород делятся на 4 слоя:

1. **Физика и биология** — тело, шерсть, здоровье
2. **Поведение и темперамент** — реакции, характер
3. **Социальность и совместимость** — с людьми/животными
4. **Требования к владельцу и условиям** — управление, уход, среда

Все признаки ниже предполагаются **нормализованными в ([0,1])**, кроме размерных групп.

---

# 1) Физика, тело, шерсть

## 1.1 Размер (категориальный, one-hot / soft)

1. **size_toy**
2. **size_small**
3. **size_medium**
4. **size_large**
5. **size_giant**

> one-hot или softmax (например, medium=0.7, large=0.3)

---

## 1.2 Масса и габариты (опционально, если нужен finer control)

6. **body_mass**
7. **body_compactness** — компактность телосложения

---

## 1.3 Шерсть и уход

8. **shedding** — интенсивность линьки
9. **coat_length** — длина шерсти
10. **coat_density** — плотность подшёрстка
11. **grooming_need** — требуемый уход
12. **coat_smell_proneness** — склонность к запаху

> `hypoallergenic` **не хранить** — это derived.

---

# 2) Здоровье и физиология

13. **health_robustness** — общая устойчивость
14. **genetic_risk** — наследственные риски
15. **lifespan_expectancy** — ожидаемая продолжительность жизни
16. **vet_cost_level** — ожидаемые ветрасходы
17. **heat_tolerance**
18. **cold_tolerance**

---

# 3) Активность и энергия

19. **energy_level** — общий уровень активности
20. **exercise_need** — потребность в физических нагрузках
21. **mental_stimulation_need** — потребность в интеллектуальной работе
22. **playfulness** — склонность к игре во взрослом возрасте

---

# 4) Поведение и темперамент (ключевой блок)

23. **reactivity** — реактивность на раздражители
24. **stress_sensitivity** — чувствительность к ошибкам/стрессу
25. **emotional_stability** — предсказуемость поведения
26. **impulsivity** — импульсивность

> `emotional_stability ≈ 1 - reactivity - stress_sensitivity`
> (можно хранить напрямую или как derived)

---

# 5) Социальность

27. **child_friendly**
28. **pet_friendly**
29. **stranger_friendly**
30. **affection_level** — ориентированность на человека
31. **independence** — автономность

---

# 6) Шум и сигнальное поведение

32. **barking_level** — склонность лаять
33. **alertness** — склонность сигналить (не обязательно лай)

---

# 7) Территориальность и защита

34. **territoriality** — охрана территории
35. **protectiveness** — защита владельца
36. **prey_drive** — добычный инстинкт

---

# 8) Одиночество, разлука, адаптация

37. **alone_tolerance** — переносимость одиночества
38. **separation_anxiety_risk** — риск тревоги разлуки
39. **sitter_compatibility** — адаптация к другому человеку
40. **environment_adaptability** — адаптация к новой среде

---

# 9) Обучение и управление

41. **trainability** — обучаемость
42. **handler_sensitivity** — чувствительность к стилю владельца
43. **stubbornness** — упрямство
44. **working_drive** — потребность в “работе/задаче”

---

# 10) Требования к владельцу (meta-признаки)

Это **не поведение собаки**, а сколько она “просит” от человека.

45. **owner_animal_handling_need**
46. **owner_dog_training_need**
47. **owner_behavior_management_need**

> Эти признаки **критичны** для соответствия опыта владельца.

---

# 11) Совместимость со средой

48. **apartment_compatibility**
49. **urban_tolerance**
50. **travel_tolerance** — переносимость поездок

---

# 12) Итог: минимальный и расширенный набор

### Минимальный (реально достаточный, ~30)

Если хочешь сжать:

* size (5)
* shedding, grooming_need
* health_robustness, genetic_risk
* energy_level, exercise_need, mental_stimulation_need
* reactivity, stress_sensitivity
* child_friendly, pet_friendly, stranger_friendly
* affection_level, independence
* barking_level
* territoriality
* alone_tolerance, separation_anxiety_risk, sitter_compatibility
* trainability
* owner_*_need (3)
* apartment_compatibility

### Полный (≈50)

— список выше.

---

# 13) Ключевое соответствие с user-space

Каждая пользовательская потребность (k) — это формула над **этими признаками**.
Примеры:

* `low_barking` → `NOT barking_level`
* `first_time_friendly` →
  `trainability AND NOT reactivity AND NOT owner_behavior_management_need`
* `hypoallergenic` →
  `NOT shedding AND NOT coat_smell_proneness`

