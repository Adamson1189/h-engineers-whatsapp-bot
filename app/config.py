"""
config.py

WHY THIS FILE EXISTS:
Every setting your app needs (database URL, API keys, tokens) should live in ONE
place, loaded from environment variables — never hardcoded in your business logic.

This gives you three things:
1. Security: secrets never get committed to Git (they stay in a .env file that
   is git-ignored).
2. Flexibility: you can run the exact same code on your laptop, a staging VPS,
   and production, just by swapping the .env file.
3. Validation: pydantic-settings will throw a clear error at startup if a
   required setting is missing, instead of failing weirdly halfway through a
   customer's WhatsApp conversation.

We use `pydantic-settings` (the modern, typed way to do this in FastAPI apps).
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "NETFIBER AI"
    app_tagline: str = "powered by H-Engineers Enterprise"
    environment: str = "development"
    debug: bool = True

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Database (Phase 2) ---
    database_url: str = "postgresql://user:password@localhost:5432/hengineers_db"

    # --- WhatsApp Cloud API (Phase 3) ---
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    # --- OpenAI (Phase 9) ---
    openai_api_key: str = ""

    # --- Paystack (Phase 8) ---
    paystack_secret_key: str = ""

    # --- JWT (Phase 5) ---
    jwt_secret_key: str = "change_me_to_a_long_random_string"
    jwt_algorithm: str = "HS256"

    # Tells pydantic-settings to read from a .env file automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """
    Why lru_cache?
    Without it, every time you call get_settings(), pydantic would re-read and
    re-validate the .env file from disk. That's wasted work on every single
    request. lru_cache means the Settings object is built ONCE, then reused.
    """
    return Settings()
