from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DNA Adductomics Platform API"
    app_version: str = "0.3.0"
    sqlite_path: str = "adductomics.db"
    upload_dir: str = "data/uploads"
    default_tolerance_ppm: float = 10.0
    default_nl_tolerance_da: float = 0.5
    default_rt_tolerance_min: float = 0.5
    default_isotope_tolerance: float = 0.15
    max_candidates_per_transition: int = 10
    rscript_binary: str = "Rscript"
    r_module_script_path: str = "r_modules/adductomics_stats.R"
    r_output_dir: str = "data/r_reports"
    demo_data_dir: str = "data"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ADDUCT_")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
