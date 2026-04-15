from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path('.env'))


@dataclass
class Settings:
    app_env: str = os.getenv('APP_ENV', 'local')
    app_name: str = os.getenv('APP_NAME', 'JanSahayak API')
    debug: bool = os.getenv('DEBUG', 'true').lower() == 'true'
    sarvam_api_key: str = os.getenv('SARVAM_API_KEY', '')
    sarvam_base_url: str = os.getenv('SARVAM_BASE_URL', 'https://api.sarvam.ai')
    sarvam_translate_model: str = os.getenv('SARVAM_TRANSLATE_MODEL', 'mayura:v1')
    sarvam_translate_mode: str = os.getenv('SARVAM_TRANSLATE_MODE', 'formal')
    sarvam_speaker_gender: str = os.getenv('SARVAM_SPEAKER_GENDER', 'Male')
    sarvam_enable_preprocessing: bool = os.getenv('SARVAM_ENABLE_PREPROCESSING', 'false').lower() == 'true'
    sarvam_numerals_format: str = os.getenv('SARVAM_NUMERALS_FORMAT', 'native')
    default_language: str = os.getenv('DEFAULT_LANGUAGE', 'en-IN')
    default_state: str = os.getenv('DEFAULT_STATE', 'Delhi')
    default_district: str = os.getenv('DEFAULT_DISTRICT', 'New Delhi')


@lru_cache
def get_settings() -> Settings:
    return Settings()
