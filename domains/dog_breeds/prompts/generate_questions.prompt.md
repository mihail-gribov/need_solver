# Role

You are a UX researcher, questionnaire designer, and domain expert in dog breeds. Your task is to:
1. Create clear, user-friendly questions that help match a person with a suitable dog breed
2. Define a logical formula that expresses this need through breed characteristics

# Task

For the following user need:
1. Generate {{ questions_count }} different question formulations
2. Create a formula expressing this need through breed features

# Context

**Block:** {{ block_name }}
{{ block_description }}

**Need ID:** `{{ need_id }}`
**Need Name:** {{ need_name }}
**Need Description:** {{ need_description }}

# Available Breed Features

Use ONLY these feature IDs in formulas. Each feature is a float value from 0 to 1.

## Base Features
{% for feature in features %}
- `{{ feature.id }}`: {{ feature.description }}
{% endfor %}

## Size Categories (one-hot soft)
{% for value in size_group['values'] %}
- `{{ value.id }}`: {{ value.name }} ({{ value.min }}-{{ value.max if value.max else '∞' }} kg)
{% endfor %}
{% for derived in size_group['derived'] %}
- `{{ derived.id }}`: {{ derived.name }}
{% endfor %}

## Height Categories (one-hot soft)
{% for value in height_group['values'] %}
- `{{ value.id }}`: {{ value.name }} ({{ value.min }}-{{ value.max if value.max else '∞' }} cm)
{% endfor %}
{% for derived in height_group['derived'] %}
- `{{ derived.id }}`: {{ derived.name }}
{% endfor %}

## Lifespan Categories (one-hot soft)
{% for value in lifespan_group['values'] %}
- `{{ value.id }}`: {{ value.name }} ({{ value.min }}-{{ value.max if value.max else '∞' }} years)
{% endfor %}
{% for derived in lifespan_group['derived'] %}
- `{{ derived.id }}`: {{ derived.name }}
{% endfor %}

# Formula Syntax

Build formulas using these operators:
- `&` — AND (conjunction): both conditions must be true
- `|` — OR (disjunction): at least one condition must be true
- `~` — NOT (negation): inverts the value

**Format:** CNF (Conjunctive Normal Form) preferred: `clause1 & clause2 & ...` where each clause is a literal or `(lit1 | lit2 | ...)`

**Examples:**
- `~shedding` — low shedding (negation of high shedding)
- `~shedding & ~dander_level` — hypoallergenic (low shedding AND low dander)
- `apartment_ok & ~barking` — apartment compatible
- `size_toy | size_small` — small size (toy OR small)
- `trainability & ~dominance` — easy for beginners
- `protectiveness & ~stranger_friendly` — good guard dog

**Guidelines for formulas:**
- Use 1-4 features typically (keep it focused)
- Prefer direct features over complex combinations
- Use negation `~` when the need is about ABSENCE of a trait
- Use OR `|` for alternatives (e.g., size categories)
- Use AND `&` for required combinations

# Critical Principle

**Questions should help understand the user's situation to match them with a suitable breed.**

Choose the most natural formulation for each question:
- Sometimes it's better to ask about USER'S life: "Вы живёте в квартире?", "У вас есть аллергия?"
- Sometimes it's better to ask about the DOG's role: "Собака будет охранять дом?", "Собака будет жить в квартире?"
- Sometimes a mixed approach works best: "Готовы ли вы к длительным прогулкам с собакой?"

Use whatever sounds most natural and clear for the specific need.

**Key rule: Questions must be NEUTRAL.** They should not hint at the "right" answer or make the user feel judged for either response. Both "Да" and "Нет" must be equally valid and socially acceptable.

**Ask about FACTS and SITUATIONS, not about VALUES or CARING:**
- ❌ "Важно ли вам, чтобы собака хорошо себя чувствовала в квартире?" — answering "Нет" makes user seem uncaring
- ❌ "Хотите ли вы, чтобы собаке было комфортно?" — impossible to say no
- ✓ "Собака будет жить в квартире?" — neutral fact, both answers are fine
- ✓ "У вас квартира или частный дом?" — neutral fact

# Requirements

1. **Generate {{ questions_count }} distinct question formulations** that reveal user's lifestyle relevant to this need
2. **Each question must work with these 4 answer options:**
   - "Да" (Yes) - user confirms this applies to them
   - "Нет" (No) - user denies this
   - "Не знаю" (Don't know) - user is uncertain
   - "Мне всё равно" (Don't care) - this factor is not important for their choice

3. **Self-verification:** For each question, verify that:
   - A "Да" answer genuinely indicates the user's situation matches this need
   - A "Нет" answer genuinely indicates the opposite situation
   - The question is about the USER, not about dogs

4. **Question style guidelines:**
   - Ask about USER'S life: housing, schedule, family, activity level, experience
   - Use simple, everyday language
   - **NEVER use negations in questions.** Forbidden patterns:
     - "У вас нет...?" ❌ → "У вас есть...?" ✓
     - "Вы не...?" ❌ → "Вы ...?" ✓
     - "Не будет ли...?" ❌ → "Будет ли...?" ✓
     - "Вам не важно...?" ❌ → rephrase completely
   - **All questions must be in POSITIVE form** — "Да" means presence/agreement, "Нет" means absence/disagreement
   - **ONE question = ONE idea.** Never combine multiple conditions with "и"/"или":
     - ❌ "Вы заводите собаку впервые и не имеете опыта?" (two conditions)
     - ✓ "Это будет ваша первая собака?"
   - **Ask about FACTS, not VALUES** — both "Да" and "Нет" should be equally acceptable answers
   - Avoid "socially desirable" questions where most people would say "Да"
   - Vary the phrasing style across questions (direct, situational, preference-based)
   - **Questions can be longer if it makes them clearer** — add context, explain the situation
   - Use natural, conversational tone — not robotic or too direct
   - It's OK to mention dogs as context, but the question should be about USER'S situation

5. **Bad examples to AVOID:**

   **Negations (confuse users — "Да" and "Нет" become ambiguous):**
   - "У вас нет двора?" ❌ (Да = нет двора? Нет = есть двор? Confusing!)
   - "Вам не важно, есть ли двор?" ❌
   - "Вам не обязательно иметь тихую собаку?" ❌
   - "Не будет ли проблемой шум?" ❌
   - "Вас не беспокоит линька?" ❌
   - "У вас нет постоянного доступа к участку?" ❌

   **STRICT: Never start questions with "У вас нет...", "Вы не...", "Не ...", "Нет ли..."**
   **Always rephrase to POSITIVE form: "У вас есть...?", "Вы ...?"**

   **Leading questions (hint at the answer):**
   - "Вам важна безопасность семьи?" ❌ (implies you should say yes)
   - "Хотите ли вы здоровую собаку?" ❌ (obvious yes)
   - "Вам удобно, когда животные занимают мало места?" ❌ (hints at yes)
   - "Согласитесь, что тихая собака лучше?" ❌ (leading)
   - "Разве вам не хочется активную собаку?" ❌ (manipulative)

   **"Caring" questions (impossible to answer "no"):**
   - "Важно ли вам, чтобы собака хорошо себя чувствовала в квартире?" ❌
   - "Хотите ли вы, чтобы собаке было комфортно?" ❌
   - "Заботит ли вас здоровье питомца?" ❌

   **Good neutral alternatives:**
   - "Вы живёте в частном доме с участком?" ✓
   - "Собака будет жить в квартире?" ✓
   - "Вам нужна собака для охраны?" ✓
   - "В вашей семье есть маленькие дети?" ✓

6. **Good examples:**
   - "Ваше жильё позволяет комфортно разместить крупное животное, или пространство ограничено?" ✓
   - "Кто-то из вашей семьи страдает аллергией на шерсть или перхоть животных?" ✓
   - "Ваш образ жизни предполагает много движения — пробежки, походы, активный отдых?" ✓
   - "Бывает ли так, что вы уходите из дома на весь день и никого не остаётся?" ✓
   - "Есть ли в семье дети младше 7 лет, которые будут контактировать с собакой?" ✓
   - "Вы раньше держали собаку и знакомы с особенностями ухода за ней?" ✓
   - "Готовы ли вы выделять минимум час в день на активные прогулки в любую погоду?" ✓
   - "Вы живёте в частном доме с участком, который нужно охранять от посторонних?" ✓

# Output Format

Return ONLY valid JSON:

```json
{
  "need_id": "{{ need_id }}",
  "formula": "feature1 & ~feature2",
  "formula_reasoning": "Brief explanation of why these features represent this need",
  "questions": [
    {
      "id": "{{ need_id }}_q1",
      "text": "Question text here?",
      "weight": 0.8,
      "style": "direct|situational|indirect",
      "verification": "Brief explanation why Yes=need present, No=need absent"
    }
  ]
}
```

**Weight guidelines:**
- **0.9-1.0**: Direct factual question with clear answer (e.g., "Кто-то в семье страдает астмой?")
- **0.6-0.8**: Good indicator but not definitive (e.g., "Вы живёте в многоквартирном доме?")
- **0.3-0.5**: Indirect/correlational indicator (e.g., "Вы часто носите тёмную одежду?")
- **0.1-0.2**: Weak hint, needs other questions to confirm

**Style types:**
- **direct**: Прямой вопрос о факте
- **situational**: Вопрос о ситуации/контексте
- **indirect**: Косвенный индикатор (вес обычно ниже)

# Example

For need "apartment_compatible" (Suitable for apartment living):

```json
{
  "need_id": "apartment_compatible",
  "formula": "apartment_ok & ~barking",
  "formula_reasoning": "Apartment living requires breed suitable for apartments (apartment_ok) and low barking tendency to avoid disturbing neighbors (~barking)",
  "questions": [
    {
      "id": "apartment_compatible_q1",
      "text": "Вы живёте в многоквартирном доме?",
      "weight": 0.95,
      "style": "direct",
      "verification": "Да = квартира. Нет = частный дом."
    },
    {
      "id": "apartment_compatible_q2",
      "text": "Вы живёте на верхнем этаже без лифта?",
      "weight": 0.7,
      "style": "situational",
      "verification": "Да = сложно с крупной собакой. Нет = этаж не проблема."
    },
    {
      "id": "apartment_compatible_q3",
      "text": "Вы ездите на работу на общественном транспорте?",
      "weight": 0.3,
      "style": "indirect",
      "verification": "Да = вероятно городская квартира. Нет = возможно пригород/авто."
    }
  ]
}
```

For need "hypoallergenic" (Low shedding):

```json
{
  "need_id": "hypoallergenic",
  "formula": "~shedding & ~dander_level",
  "formula_reasoning": "Hypoallergenic breeds must have minimal shedding (~shedding) AND low dander production (~dander_level) - both are primary allergen sources",
  "questions": [
    {
      "id": "hypoallergenic_q1",
      "text": "Кто-то в вашей семье страдает астмой или аллергией на животных?",
      "weight": 0.95,
      "style": "direct",
      "verification": "Да = медицинская необходимость. Нет = аллергии нет."
    },
    {
      "id": "hypoallergenic_q2",
      "text": "У вас дома есть робот-пылесос?",
      "weight": 0.2,
      "style": "indirect",
      "verification": "Да = возможно готовы к шерсти. Нет = слабый сигнал."
    },
    {
      "id": "hypoallergenic_q3",
      "text": "Вы часто носите тёмную одежду?",
      "weight": 0.4,
      "style": "indirect",
      "verification": "Да = шерсть будет заметна. Нет = менее критично."
    }
  ]
}
```

# Language

Generate all questions in **Russian**.
