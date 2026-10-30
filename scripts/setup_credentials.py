"""First-run local credential setup for Lapka.

Never prints secrets and never commits .env. Existing environment variables override .env.
"""
from __future__ import annotations
import getpass
import os
import secrets
from pathlib import Path
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def configure():
    saved = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    current = os.environ.get("ADMIN_PASSWORD") or saved.get("ADMIN_PASSWORD")
    if current:
        source = "переменная окружения" if os.environ.get("ADMIN_PASSWORD") else ".env"
        print(f"ADMIN_PASSWORD настроен ({source}).")
        return

    print("\nПервый запуск: задайте постоянный пароль администратора.")
    print("Он сохранится только в локальном .env (файл исключён из Git).")
    password = getpass.getpass("Новый пароль администратора: ")
    password_confirm = getpass.getpass("Повторите пароль: ")
    if not password or password != password_confirm:
        print("Пароль пустой или не совпадает. Настройка прервана; запуск без администрирования.")
        return
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    if not saved.get("SECRET_KEY"):
        set_key(str(ENV_PATH), "SECRET_KEY", secrets.token_urlsafe(48), quote_mode="always")
    set_key(str(ENV_PATH), "ADMIN_PASSWORD", password, quote_mode="always")
    print("Пароль сохранён в .env.")
    if not (os.environ.get("LAPKA_API_KEY") or saved.get("LAPKA_API_KEY")):
        key = getpass.getpass("API-ключ (Enter — создать автоматически): ")
        set_key(str(ENV_PATH), "LAPKA_API_KEY", key or secrets.token_urlsafe(32), quote_mode="always")
        print("API-ключ сохранён в .env (его можно прочитать в файле локально).")


if __name__ == "__main__":
    configure()
