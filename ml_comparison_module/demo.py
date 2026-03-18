"""Synthetic end-to-end demo for the ML comparison module."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import cllr, roc_summary, to_likelihood_ratio
from .model import build_pair_dataset, donor_wise_train_eval
from .schema import build_feature_matrix


def make_synthetic_data(
    n_donors: int = 40,
    sessions_per_donor: int = 3,
    samples_per_session: int = 2,
    n_analytes: int = 20,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    donor_signatures = rng.normal(0.0, 1.0, size=(n_donors, n_analytes))

    sample_index = 0
    for donor in range(n_donors):
        for session in range(sessions_per_donor):
            session_shift = rng.normal(0.0, 0.3, size=n_analytes)
            for _ in range(samples_per_session):
                noise = rng.normal(0.0, 0.4, size=n_analytes)
                values = donor_signatures[donor] + session_shift + noise
                values = np.exp(values)  # keep channels positive

                row = {
                    "sample_id": f"S{sample_index:05d}",
                    "donor_id": f"D{donor:03d}",
                    "session_id": f"T{session:02d}",
                    "phase": "Layer-B",
                }
                for i, value in enumerate(values):
                    row[f"a{i:02d}"] = float(value)
                    row[f"a{i:02d}_is"] = float(value * rng.uniform(0.8, 1.2))

                rows.append(row)
                sample_index += 1

    return pd.DataFrame(rows)


def main() -> None:
    raw = make_synthetic_data()
    metadata, feature_matrix = build_feature_matrix(raw)
    train_result = donor_wise_train_eval(metadata, feature_matrix, test_size=0.25)

    # Rebuild test-pair scores for metric illustration.
    # In production, keep explicit train/test pair objects and cache scores.
    X_pairs, y_pairs = build_pair_dataset(metadata, feature_matrix)
    probs = train_result.model.predict_proba_same(X_pairs)
    lrs = to_likelihood_ratio(probs)

    lr_same = lrs[y_pairs.to_numpy() == 1]
    lr_diff = lrs[y_pairs.to_numpy() == 0]

    print("=== ML Comparison Module Demo ===")
    print(f"Donor-wise test AUC: {train_result.auc:.4f}")
    print(f"All-pairs ROC summary: {roc_summary(y_pairs, probs)}")
    print(f"Cllr: {cllr(lr_same, lr_diff):.4f}")
    print(
        f"Pairs: train={train_result.n_train_pairs}, "
        f"test={train_result.n_test_pairs}, all={len(X_pairs)}"
    )


if __name__ == "__main__":
    main()
