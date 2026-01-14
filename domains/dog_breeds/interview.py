#!/usr/bin/env python3
"""
Interactive dog breed recommendation interview.

Run: python interview.py
"""

import json
import random
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# For interactive input when stdin is not a TTY
_tty_file = None


def get_input(prompt: str = "") -> str:
    """Read input from TTY, even if stdin is not interactive."""
    global _tty_file

    if sys.stdin.isatty():
        return input(prompt)

    # Open /dev/tty for interactive input
    if _tty_file is None:
        try:
            _tty_file = open("/dev/tty", "r")
        except OSError:
            print("\n" + "=" * 60)
            print("  ОШИБКА: Интерактивный режим недоступен")
            print("=" * 60)
            print("\n  Запустите скрипт в терминале:")
            print("    uv run python domains/dog_breeds/interview.py")
            print()
            sys.exit(1)

    if prompt:
        print(prompt, end="", flush=True)

    line = _tty_file.readline()
    if not line:
        raise EOFError()
    return line.rstrip("\n")

from matcher import BreedMatcher
from user_profile import UserProfile

# Load config
CONFIG_FILE = SCRIPT_DIR / "config.json"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


def load_questions() -> dict[str, dict]:
    """Load all question files."""
    questions_dir = SCRIPT_DIR / "questions"
    questions = {}
    for fpath in questions_dir.glob("*.json"):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        questions[data["need_id"]] = data
    return questions


def load_breeds_names() -> dict[str, str]:
    """Load breed display names."""
    breeds_file = SCRIPT_DIR / "content" / "breeds.json"
    with open(breeds_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {b["id"]: b.get("name_ru") or b["name_en"] for b in data["breeds"]}


def load_needs_names() -> dict[str, str]:
    """Load need display names."""
    needs_file = SCRIPT_DIR / "content" / "user_needs.json"
    with open(needs_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {n["id"]: n["name"] for n in data["needs"]}


def clear_screen():
    print("\033[2J\033[H", end="")


def print_header(step: int, total_questions: int):
    print("=" * 60)
    print(f"  Подбор породы собаки  |  Вопрос {step}")
    print("=" * 60)
    print()


def print_top_breeds(matcher: BreedMatcher, profile: UserProfile, breed_names: dict, top_k: int = 5, equal_weights: bool = False):
    needs = profile.get_needs()
    if not needs:
        print("  (ответьте на первый вопрос)")
        return

    results = matcher.match_fast(needs, top_k=top_k, equal_weights=equal_weights)

    print(f"  Топ-{top_k} пород:")
    for i, (breed_id, score) in enumerate(results, 1):
        name = breed_names.get(breed_id, breed_id)
        bar = "█" * int(score * 20)
        print(f"  {i}. {name:<30} {score:.2f} {bar}")
    print()


def get_answer() -> str | None:
    """Get user's answer."""
    print("  Ответы:")
    print("    1 или д  - Да")
    print("    2 или н  - Нет")
    print("    3 или ?  - Не знаю")
    print("    4 или -  - Мне всё равно")
    print("    q        - Выход")
    print()

    while True:
        try:
            answer = get_input("  Ваш ответ: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None

        if answer in ("1", "д", "да", "y", "yes"):
            return "true"
        elif answer in ("2", "н", "нет", "n", "no"):
            return "false"
        elif answer in ("3", "?", "не знаю"):
            return "unknown"
        elif answer in ("4", "-", "всё равно", "все равно"):
            return "independent"
        elif answer in ("q", "quit", "exit", "выход"):
            return None
        else:
            print("  Неверный ввод. Попробуйте ещё раз.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Interactive dog breed interview")
    parser.add_argument("--equal-weights", "-e", action="store_true",
                        help="Use equal weights for all needs (ignore user confidence)")
    args = parser.parse_args()

    equal_weights = args.equal_weights

    print("Загрузка данных...")
    if equal_weights:
        print("  Режим: равные веса для всех потребностей")

    matcher = BreedMatcher()
    profile = UserProfile()
    questions = load_questions()
    breed_names = load_breeds_names()
    need_names = load_needs_names()

    step = 1
    exhausted_needs: set[str] = set()  # Needs with all questions asked
    confidence_threshold = CONFIG["fuzzy"]["threshold"]["high"]  # Stop asking when confidence >= this

    while True:
        clear_screen()
        print_header(step, len(questions))

        # Show current top breeds
        print_top_breeds(matcher, profile, breed_names, equal_weights=equal_weights)

        # Build excluded set: exhausted needs + needs with high confidence + independent
        confident_needs = {
            nid for nid in profile.get_needs()
            if profile.get_need_confidence(nid) >= confidence_threshold
        }
        excluded = exhausted_needs | confident_needs | profile._independent

        best_need, split_score = matcher.select_next_question(
            profile.get_needs(),
            excluded,
            equal_weights=equal_weights
        )

        if best_need is None:
            print("  Все вопросы заданы!")
            break

        if split_score < 0.01:
            print("  Дополнительные вопросы не улучшат результат.")
            print("  Нажмите Enter для выхода.")
            get_input()
            break

        # Get question data
        q_data = questions.get(best_need)
        if not q_data:
            print(f"  Ошибка: вопросы для {best_need} не найдены")
            break

        # Get unanswered questions for this need
        all_q = q_data.get("questions", [])
        unanswered = [q for q in all_q if not profile.is_question_asked(q.get("id", ""))]

        # If all questions for this need are asked, mark as exhausted and retry
        if not unanswered:
            exhausted_needs.add(best_need)
            continue

        # Pick a random unanswered question
        question = random.choice(unanswered)
        question_id = question.get("id", f"{best_need}_q{random.randint(1,100)}")
        weight = question.get("weight", 1.0)

        print(f"  {question['text']}")
        print()
        confidence = profile.get_need_confidence(best_need)
        print(f"  (потребность: {q_data['need_name']}, вес: {weight:.1f}, conf: {confidence:.2f})")
        print()

        # Get answer
        answer = get_answer()

        if answer is None:
            print("\n  До свидания!")
            break

        # Add answer to profile with question_id and weight
        profile.add_answer(best_need, answer, question["text"], question_id, weight)
        step += 1

    # Final results
    print()
    print("=" * 60)
    mode_str = " (равные веса)" if equal_weights else ""
    print(f"  ФИНАЛЬНЫЙ РЕЗУЛЬТАТ{mode_str}")
    print("=" * 60)
    print()
    print_top_breeds(matcher, profile, breed_names, top_k=25, equal_weights=equal_weights)

    # Needs report
    print("  Профиль потребностей:")
    print(f"  {'Потребность':<30} {'T':>5} {'F':>5} {'T-F':>6} {'Conf':>5} {'Состояние':<8}")
    print(f"  {'-'*30} {'-'*5} {'-'*5} {'-'*6} {'-'*5} {'-'*8}")

    for need_id, val in sorted(profile.get_needs().items(), key=lambda x: x[1].t - x[1].f, reverse=True):
        conf = profile.get_need_confidence(need_id)
        score = val.t - val.f
        if score > 0.3:
            state_ru = "ДА"
        elif score < -0.3:
            state_ru = "НЕТ"
        else:
            state_ru = "~"
        name = need_names.get(need_id, need_id)
        print(f"  {name:<30} {val.t:>5.2f} {val.f:>5.2f} {score:>+6.2f} {conf:>5.2f} {state_ru:<8}")

    if profile._independent:
        independent_names = [need_names.get(nid, nid) for nid in profile._independent]
        print(f"\n  Безразличны: {', '.join(independent_names)}")
    print()

    print("  История ответов:")
    for ans in profile.get_answer_history():
        symbol = {"true": "✓", "false": "✗", "unknown": "?", "independent": "-"}[ans.answer_type]
        name = need_names.get(ans.need_id, ans.need_id)
        print(f"    [{symbol}] {name} (w={ans.weight:.1f})")
    print()

    # Save profile to file
    save_profile(profile)


def save_profile(profile: UserProfile) -> Path:
    """Save interview results to JSON file."""
    from datetime import datetime

    data_dir = SCRIPT_DIR / "data"
    data_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"interview_{timestamp}.json"
    filepath = data_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)

    # Also save as "latest" for easy access
    latest_path = data_dir / "interview_latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)

    print(f"  Результаты сохранены: {filepath.name}")
    print(f"  (также: {latest_path.name})")
    print()

    return filepath


if __name__ == "__main__":
    main()
