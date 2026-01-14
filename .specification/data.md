Ок. Ниже — **полный набор статических данных** (как файлы/пакет контента) + **структуры вычисляемых данных**, которые логично хранить в БД для сессий, скоринга, объяснений и аналитики.

---

# 1) Статические данные (файлы, “контент отдельно от кода”)

## 1.1. Дерево файлов

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
    breed_features.json              # список признаков пород + типы
    derived_features.json            # (опц.) как вычислять производные признаки

  breeds/
    index.json                       # список пород + версии
    breeds.jsonl                     # каждая строка = порода (удобно грузить пачками)
    facts_fields.json                # какие facts показываем в UI

  criteria/
    needs.json
    constraints.json
    derived_criteria.json            # (опц.) мета-критерии для объяснений/группировки

  questions/
    blocks.json                      # порядок/стадии (constraints → purpose → lifestyle → prefs)
    q_owner_experience.json
    q_purpose.json
    q_housing.json
    q_absence_daily.json
    q_trips.json
    q_backup_care.json
    q_allergy_shedding.json
    q_noise.json
    q_kids_pets.json
    q_activity.json
    ...                              # остальные

  rules/
    auto_weight_rules.json           # правила авто-установки/усиления весов criteria
    disable_rules.json               # правила отключения вопросов
    purpose_rules.json               # purpose → набор весов criteria
    gating_rules.json                # hard-first стратегия (что спрашивать раньше)
    normalization_rules.json         # нормализация/клиппинг/конфликты

  explanation/
    criteria_texts_ru.json           # шаблоны объяснений по критериям
    conflict_texts_ru.json           # шаблоны “почему исключено”
    pros_cons_mapping.json           # как из sat/weights строить pros/cons

  scoring/
    scoring_config.json              # формула агрегации, пороги hard/soft, веса по умолчанию
    sat_semantics.json               # fuzzy sat (литералы/and/or)
```

---

## 1.2. Ключевые статические структуры

### A) `schemas/feature_schema.json` + `features/breed_features.json`

**Что хранит:** базис признаков пород.

* `float01` признаки: `energy, trainability, grooming, shedding, ...`
* `onehot_soft` группы: `size` (toy/small/medium/large/giant)
* расширения: `territoriality`, `reactivity`, `alone_tolerance`, `sitter_compatibility`, `separation_anxiety_risk`, `handler_experience_need` и т.п.

---

### B) `schemas/user_factors_schema.json`

**Что хранит:** факторы пользователя, которые выводятся из ответов.

Минимум (по нашей ветке):

* `owner_experience`: `{animal_handling, dog_training, behavior_management}`
* `purpose`: onehot_soft (companion_apartment / family_kids / guard_property / …)
* `housing`: multi-location + time_share + (опц.) context (neighbors_sensitivity и т.п.)
* `absence_daily`: hours_out
* `absence_trips`: frequency, typical_duration
* `backup_care`: availability (0..1)  ← нейтрально, без причин

---

### C) `criteria/*.json` + `scoring/sat_semantics.json`

**Что хранит:** критерии (needs/constraints) и их формулы.

* `expr_cnf` для обычных критериев (над breed.features)
* `expr_custom` для “мостов” user_factors ↔ breed.features (например поездки/передержка)

---

### D) `questions/*.json` + `rules/*.json`

**Что хранит:** опросник и rules-автоматика.

Важные элементы у вопроса:

* `answers[].effects[]` — декларативные операции, которые обновляют `user_factors` и `criteria_weights`
* `answers[].disable[]` — статическое отключение
* `show_if` — простая логика показа (без “почему”, только условия)

Rules-файлы:

* `purpose_rules.json` — цель → веса критериев
* `auto_weight_rules.json` — опыт/квартира/дети → усиление критериев
* `disable_rules.json` — опыт/цель/уже известное → отключение вопросов
* `gating_rules.json` — стратегия порядка (что задаём раньше)

---

### E) `explanation/*.json`

**Что хранит:** тексты и правила сборки объяснений, чтобы engine не содержал русских фраз.

* тексты по критериям
* шаблоны конфликтов hard constraints
* правила pros/cons (например: pros если `weight≥0.6 & sat≥0.75`)

---

# 2) Вычисляемые данные (храним в БД)

Ниже — практичный набор таблиц (под Postgres, но подойдёт и для любой SQL).
Рекомендация: хранить “сырые ответы” + “агрегированное состояние” + “снимки скоринга” (для отладки/аналитики).

## 2.1. Сессии

### `sessions`

* `id` (uuid, pk)
* `content_version` (text) — версия статического контента (важно для воспроизводимости)
* `created_at`, `updated_at`
* `status` (active/completed)
* `locale`
* `user_id` (nullable, если аноним)

### `session_answers`

* `session_id` (fk)
* `question_id`
* `answer_id`
* `answered_at`
* `payload_json` (jsonb, опц.) — если ответ содержит число/слайдер

Уникальный ключ: `(session_id, question_id)`

---

## 2.2. Агрегированное состояние (user-vector + веса)

### `session_user_factors`

Храним **нормализованный** user-vector как jsonb (гибко), но можно и колонками.

* `session_id` (pk/fk)
* `user_factors_json` (jsonb)

  * owner_experience (3 floats)
  * purpose distribution
  * housing (locations/time_share/context)
  * absence_daily / absence_trips
  * backup_care.availability
* `updated_at`

### `session_criteria_weights`

Можно хранить отдельно, чтобы быстро считать score.

* `session_id` (pk/fk)
* `weights_json` (jsonb)
  пример: `{ "need_low_barking":0.7, "constraint_owner_experience":1.0, ... }`
* `updated_at`

### `session_question_state`

* `session_id` (pk/fk)
* `asked_json` (jsonb array) — какие уже задавали (для UI/логики)
* `disabled_json` (jsonb array)
* `available_json` (jsonb array, опц.) — кэш кандидатов вопросов
* `updated_at`

---

## 2.3. Снимки скоринга (самое полезное для дебага/аналитики)

### `session_scoring_runs`

Каждый пересчёт — отдельная запись.

* `id` (uuid pk)
* `session_id` (fk)
* `run_no` (int) — 1..N
* `trigger` (text) — answer_submitted / manual / resume
* `created_at`
* `params_json` (jsonb) — пороги, topN, стратегия и т.п.

### `session_breed_scores`

Храним результаты по породам для конкретного run.

* `run_id` (fk)
* `breed_id` (text)
* `score` (float)
* `needs_score` (float)
* `constraints_penalty` (float)
* `hard_excluded` (bool)
* `rank` (int)
* `details_json` (jsonb)

  * per-criterion: `{criterion_id: {sat, weight, clause_sats?...}}`
  * hard_violation reasons

Индекс: `(run_id, rank)` и `(run_id, breed_id)`.

### `session_recommendation`

Чтобы UI быстро брал “текущий ответ”:

* `session_id` (pk)
* `run_id` (fk to latest)
* `top_json` (jsonb) — topN ids + краткое explain
* `excluded_json` (jsonb) — список исключенных с причинами
* `next_question_id` (text)
* `updated_at`

---

## 2.4. Логи применения правил (опционально, но очень полезно)

### `session_rule_trace`

* `run_id`
* `rule_id`
* `rule_type` (auto_weight/disable/purpose/normalization)
* `applied` (bool)
* `diff_json` (jsonb) — что поменяли (например вес критерия был 0.2 → 0.7)
* `created_at`

Это превращает систему в “объяснимую для разработчиков”.

---

# 3) Минимальный набор сущностей для старта (MVP)

Если хочешь быстро сделать v0:
**Статика:**

* feature_schema + breeds.jsonl
* criteria needs/constraints (штук 15–25)
* questions: опыт, цель, жильё, ежедневное отсутствие, поездки+передержка, аллергия/линька, лай, дети/питомцы
* rules: purpose_rules + disable_rules + scoring_config + sat_semantics
* explanation texts

**БД:**

* sessions
* session_answers
* session_user_factors (jsonb)
* session_criteria_weights (jsonb)
* session_scoring_runs
* session_breed_scores
* session_recommendation

---

# 4) Как связать всё вместе (важная договорённость)

* `answers` — источник фактов
* `effects` + `rules` — интерпретация
* `user_factors` + `criteria_weights` — агрегированное состояние (то, с чем работает engine)
* `scoring_runs` — воспроизводимость и дебаг

---

Если хочешь, в следующем сообщении я могу:

* выдать **конкретные JSON-шаблоны** для каждого файла (скелет с полями),
* или сразу набросать **SQL DDL** под эти таблицы (Postgres) с индексами и ограничениями.
b