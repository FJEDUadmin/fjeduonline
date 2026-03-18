"""Model training utilities for donor comparison."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .pairs import PairConfig, generate_pairs, pair_features


@dataclass
class TrainResult:
    model: "ComparisonModel"
    auc: float
    n_train_pairs: int
    n_test_pairs: int
    test_scores: np.ndarray
    test_labels: np.ndarray


class ComparisonModel:
    """Pair-based comparison model with probability calibration."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        base = Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        random_state=random_state,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        self._model = CalibratedClassifierCV(base, method="sigmoid", cv=3)

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> "ComparisonModel":
        self._model.fit(X, y)
        return self

    def predict_proba_same(self, X: pd.DataFrame) -> np.ndarray:
        return self._model.predict_proba(X)[:, 1]


def build_pair_dataset(
    metadata: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    pair_config: PairConfig | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    pairs = generate_pairs(metadata, config=pair_config)
    X_pairs = pair_features(feature_matrix, pairs)
    y_pairs = pairs["is_same_donor"].astype(int)
    return X_pairs, y_pairs


def donor_wise_train_eval(
    metadata: pd.DataFrame,
    feature_matrix: pd.DataFrame,
    test_size: float = 0.25,
    random_state: int = 42,
) -> TrainResult:
    """Hold out donors to avoid identity leakage across train/test."""
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=random_state,
    )
    split = next(
        splitter.split(
            feature_matrix,
            groups=metadata["donor_id"],
        )
    )
    train_idx, test_idx = split

    train_meta = metadata.iloc[train_idx].reset_index(drop=True)
    train_feat = feature_matrix.iloc[train_idx].reset_index(drop=True)
    test_meta = metadata.iloc[test_idx].reset_index(drop=True)
    test_feat = feature_matrix.iloc[test_idx].reset_index(drop=True)

    train_X, train_y = build_pair_dataset(train_meta, train_feat)
    test_X, test_y = build_pair_dataset(test_meta, test_feat)

    model = ComparisonModel(random_state=random_state).fit(train_X, train_y)
    scores = model.predict_proba_same(test_X)
    auc = roc_auc_score(test_y, scores)

    return TrainResult(
        model=model,
        auc=float(auc),
        n_train_pairs=int(len(train_X)),
        n_test_pairs=int(len(test_X)),
        test_scores=scores,
        test_labels=test_y.to_numpy(),
    )
