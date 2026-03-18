"""Pair generation for same-source vs different-source comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass
class PairConfig:
    max_positive_pairs: int | None = 200_000
    max_negative_pairs: int | None = 200_000
    random_seed: int = 42


def _sample_pairs(
    pairs: list[tuple[int, int]],
    max_pairs: int | None,
    rng: np.random.Generator,
) -> list[tuple[int, int]]:
    if max_pairs is None or len(pairs) <= max_pairs:
        return pairs
    indices = rng.choice(len(pairs), size=max_pairs, replace=False)
    return [pairs[index] for index in indices]


def generate_pairs(
    metadata: pd.DataFrame,
    donor_column: str = "donor_id",
    config: PairConfig | None = None,
) -> pd.DataFrame:
    """Generate positive (same donor) and negative (different donor) sample pairs."""
    config = config or PairConfig()
    rng = np.random.default_rng(config.random_seed)

    positive_pairs: list[tuple[int, int]] = []
    donor_groups = metadata.groupby(donor_column).groups
    donor_indices = {donor: list(indices) for donor, indices in donor_groups.items()}

    for indices in donor_indices.values():
        positive_pairs.extend(combinations(indices, 2))
    positive_pairs = _sample_pairs(positive_pairs, config.max_positive_pairs, rng)

    all_donors = list(donor_indices.keys())
    negative_pairs: list[tuple[int, int]] = []
    for i, donor_a in enumerate(all_donors):
        for donor_b in all_donors[i + 1 :]:
            for idx_a in donor_indices[donor_a]:
                for idx_b in donor_indices[donor_b]:
                    negative_pairs.append((idx_a, idx_b))
    negative_pairs = _sample_pairs(negative_pairs, config.max_negative_pairs, rng)

    records = (
        [{"left": a, "right": b, "is_same_donor": 1} for a, b in positive_pairs]
        + [{"left": a, "right": b, "is_same_donor": 0} for a, b in negative_pairs]
    )
    return pd.DataFrame(records)


def pair_features(
    feature_matrix: pd.DataFrame,
    pairs: pd.DataFrame,
    methods: Iterable[str] = ("abs_diff", "prod"),
) -> pd.DataFrame:
    """
    Build pairwise feature representation.

    - ``abs_diff``: absolute difference per feature.
    - ``prod``: feature-wise product (captures co-elevation/co-suppression patterns).
    """
    left = feature_matrix.iloc[pairs["left"].to_numpy()].to_numpy()
    right = feature_matrix.iloc[pairs["right"].to_numpy()].to_numpy()

    features: dict[str, np.ndarray] = {}
    names = feature_matrix.columns.to_list()

    if "abs_diff" in methods:
        for index, name in enumerate(names):
            features[f"abs_diff__{name}"] = np.abs(left[:, index] - right[:, index])

    if "prod" in methods:
        for index, name in enumerate(names):
            features[f"prod__{name}"] = left[:, index] * right[:, index]

    return pd.DataFrame(features)
