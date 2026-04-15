from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    """Load .env from cwd and parent directories so startup path does not matter."""
    candidates: list[Path] = []
    cwd = Path.cwd().resolve()
    candidates.append(cwd / ".env")

    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidates.append(parent / ".env")

    seen: set[Path] = set()
    for env_path in candidates:
        if env_path in seen:
            continue
        seen.add(env_path)
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)


_load_env_files()


@dataclass
class Settings:
    app_env: str = os.getenv('APP_ENV', 'local')
    app_name: str = os.getenv('APP_NAME', 'JanSahayak API')
    debug: bool = os.getenv('DEBUG', 'true').lower() == 'true'
    sarvam_api_key: str = os.getenv('SARVAM_API_KEY', '')
    sarvam_base_url: str = os.getenv('SARVAM_BASE_URL', 'https://api.sarvam.ai')
    sarvam_chat_url: str = os.getenv('SARVAM_CHAT_URL', 'https://api.sarvam.ai/v1/chat/completions')
    sarvam_chat_model: str = os.getenv('SARVAM_CHAT_MODEL', 'sarvam-m')
    sarvam_chat_temperature: float = float(os.getenv('SARVAM_CHAT_TEMPERATURE', '0.2'))
    sarvam_translate_url: str = os.getenv('SARVAM_TRANSLATE_URL', 'https://api.sarvam.ai/translate/text')
    sarvam_translate_model: str = os.getenv('SARVAM_TRANSLATE_MODEL', 'mayura:v1')
    sarvam_translate_mode: str = os.getenv('SARVAM_TRANSLATE_MODE', 'formal')
    sarvam_speaker_gender: str = os.getenv('SARVAM_SPEAKER_GENDER', 'Male')
    sarvam_enable_preprocessing: bool = os.getenv('SARVAM_ENABLE_PREPROCESSING', 'false').lower() == 'true'
    sarvam_numerals_format: str = os.getenv('SARVAM_NUMERALS_FORMAT', 'native')
    default_language: str = os.getenv('DEFAULT_LANGUAGE', 'en-IN')
    default_state: str = os.getenv('DEFAULT_STATE', 'Delhi')
    default_district: str = os.getenv('DEFAULT_DISTRICT', 'New Delhi')
    twilio_account_sid: str = os.getenv('TWILIO_ACCOUNT_SID', '')
    twilio_auth_token: str = os.getenv('TWILIO_AUTH_TOKEN', '')
    twilio_whatsapp_number: str = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')


@lru_cache
def get_settings() -> Settings:
    return Settings()
