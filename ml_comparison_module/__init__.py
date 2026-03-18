"""Machine learning module for donor/sample comparison workflows."""

from .metrics import cllr, cmc_top_k_accuracy, roc_summary, to_likelihood_ratio
from .model import ComparisonModel, build_pair_dataset
from .schema import (
    REQUIRED_METADATA_COLUMNS,
    build_feature_matrix,
    load_skyline_export,
    validate_metadata,
)

__all__ = [
    "REQUIRED_METADATA_COLUMNS",
    "ComparisonModel",
    "build_feature_matrix",
    "build_pair_dataset",
    "cllr",
    "cmc_top_k_accuracy",
    "load_skyline_export",
    "roc_summary",
    "to_likelihood_ratio",
    "validate_metadata",
]
