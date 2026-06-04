import json
from pathlib import Path

PROFILE_PATH = Path(__file__).parent / "profile.json"


def load_profile() -> dict:
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def update_profile(key: str, value):
    profile = load_profile()
    if isinstance(profile.get(key), list):
        if value not in profile[key]:
            profile[key].append(value)
    else:
        profile[key] = value
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def profile_to_text() -> str:
    p = load_profile()
    lines = [
        f"Имя: {p.get('name', '—')}",
        f"Город: {p.get('city', '—')}",
        f"Направления работы: {', '.join(p.get('work', []))}",
        f"Сферы жизни: {', '.join(p.get('life_spheres', []))}",
    ]
    if p.get("preferences"):
        lines.append(f"Предпочтения: {', '.join(p['preferences'])}")
    if p.get("goals"):
        lines.append(f"Цели: {', '.join(p['goals'])}")
    if p.get("notes"):
        lines.append(f"Заметки о человеке: {', '.join(p['notes'])}")
    return "\n".join(lines)
