from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DNA Adductomics Platform API"
    app_version: str = "0.1.0"
    sqlite_path: str = "adductomics.db"
    default_tolerance_ppm: float = 10.0
    default_nl_tolerance_da: float = 0.5
    max_candidates_per_transition: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ADDUCT_")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
