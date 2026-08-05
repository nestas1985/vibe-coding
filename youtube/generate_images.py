"""
Генерация фоторяда через GigaChat API (Kandinsky) по списку промптов.
Использование: python generate_images.py [файл_с_промптами] [папка_вывода]
"""
import os
import re
import sys
import time
import uuid
import base64
import requests
from pathlib import Path

HERE = Path(__file__).parent
ENV_FILE = HERE / ".env"

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

ENV = load_env()
AUTH_KEY = ENV.get("GIGACHAT_AUTH_KEY")
if not AUTH_KEY:
    print("Нет GIGACHAT_AUTH_KEY в youtube/.env")
    sys.exit(1)

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_BASE = "https://gigachat.devices.sberbank.ru/api/v1"

# У GigaChat/NGW сертификаты выпущены Минцифры РФ, их обычно нет в системном
# хранилище доверенных сертификатов -> проверку TLS отключаем (стандартная практика
# именно для этого API, не для внешних сайтов).
VERIFY_SSL = False
if not VERIFY_SSL:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_access_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {AUTH_KEY}",
    }
    data = {"scope": "GIGACHAT_API_PERS"}
    resp = requests.post(OAUTH_URL, headers=headers, data=data, verify=VERIFY_SSL, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def generate_image(token: str, prompt: str) -> str:
    """Возвращает file_id сгенерированной картинки."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": "Ты — Василий Кандинский, рисуешь фотореалистичные кинематографичные кадры."},
            {"role": "user", "content": f"Нарисуй: {prompt}"},
        ],
        "function_call": "auto",
    }
    resp = requests.post(f"{API_BASE}/chat/completions", headers=headers, json=payload, verify=VERIFY_SSL, timeout=120)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    m = re.search(r'src="([a-f0-9\-]+)"', content)
    if not m:
        raise RuntimeError(f"Не нашёл id картинки в ответе: {content[:200]}")
    return m.group(1)


def download_image(token: str, file_id: str, out_path: Path):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/jpg",
    }
    resp = requests.get(f"{API_BASE}/files/{file_id}/content", headers=headers, verify=VERIFY_SSL, timeout=60)
    resp.raise_for_status()
    out_path.write_bytes(resp.content)


def main():
    prompts_file = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "aralsk7_prompts_30.txt"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "images"
    out_dir.mkdir(exist_ok=True)

    prompts = [p.strip() for p in prompts_file.read_text(encoding="utf-8").splitlines() if p.strip()]
    print(f"Промптов: {len(prompts)}. Папка вывода: {out_dir}")

    token = get_access_token()
    print("Токен получен.")

    for i, prompt in enumerate(prompts, 1):
        out_path = out_dir / f"{i:03d}.jpg"
        if out_path.exists():
            print(f"[{i}/{len(prompts)}] уже есть, пропуск")
            continue
        try:
            file_id = generate_image(token, prompt)
            download_image(token, file_id, out_path)
            print(f"[{i}/{len(prompts)}] OK -> {out_path.name}")
        except Exception as e:
            print(f"[{i}/{len(prompts)}] ОШИБКА: {e}")
        time.sleep(1)  # не спамить API

    print("Готово.")


if __name__ == "__main__":
    main()
