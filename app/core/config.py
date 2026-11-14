"""
YottaFlex KYC Onboarding Evidence Management System
Application configuration and settings.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://kyc_user:kyc_password@localhost:5432/yottaflex_kyc"

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-this-secret"

    # Generator
    generator_seed: int = 20261022
    generator_mode: str = "full"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
