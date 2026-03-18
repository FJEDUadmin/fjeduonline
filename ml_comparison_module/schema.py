"""Data schema and feature preparation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

REQUIRED_METADATA_COLUMNS = (
    "sample_id",
    "donor_id",
    "session_id",
    "phase",
)


@dataclass(frozen=True)
class FeatureConfig:
    """Configuration for feature extraction from Skyline-like tables."""

    id_columns: Sequence[str] = REQUIRED_METADATA_COLUMNS
    internal_standard_suffix: str = "_is"
    eps: float = 1e-9


def load_skyline_export(path: str) -> pd.DataFrame:
    """Load Skyline export table from CSV/TSV based on file extension."""
    separator = "\t" if path.lower().endswith(".tsv") else ","
    return pd.read_csv(path, sep=separator)


def validate_metadata(df: pd.DataFrame, required: Iterable[str] = REQUIRED_METADATA_COLUMNS) -> None:
    """Validate required metadata columns before feature processing."""
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required metadata columns: {missing}")


def _numeric_columns(df: pd.DataFrame, id_columns: Sequence[str]) -> list[str]:
    return [
        col
        for col in df.columns
        if col not in id_columns and pd.api.types.is_numeric_dtype(df[col])
    ]


def build_feature_matrix(
    df: pd.DataFrame,
    config: FeatureConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build model-ready feature matrix.

    Strategy:
    1. Keep required metadata.
    2. For each analyte ``x`` with an internal-standard partner ``x_is``,
       compute log-ratio ``log((x + eps) / (x_is + eps))``.
    3. For remaining numeric channels, apply ``log1p``.
    """
    config = config or FeatureConfig()
    validate_metadata(df, config.id_columns)

    numeric_columns = _numeric_columns(df, config.id_columns)
    features: dict[str, np.ndarray] = {}
    consumed: set[str] = set()

    for column in numeric_columns:
        if column.endswith(config.internal_standard_suffix):
            continue

        is_column = f"{column}{config.internal_standard_suffix}"
        if is_column in df.columns:
            ratio = (df[column].to_numpy() + config.eps) / (
                df[is_column].to_numpy() + config.eps
            )
            features[f"log_ratio__{column}"] = np.log(ratio)
            consumed.update({column, is_column})

    for column in numeric_columns:
        if column in consumed:
            continue
        features[f"log1p__{column}"] = np.log1p(df[column].to_numpy())

    metadata = df[list(config.id_columns)].copy()
    feature_matrix = pd.DataFrame(features, index=df.index)
    return metadata, feature_matrix
