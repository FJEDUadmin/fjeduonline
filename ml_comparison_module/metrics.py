"""Evaluation metrics for forensic comparison workflows."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def to_likelihood_ratio(prob_same: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Convert calibrated same-source probability to LR with prior odds=1."""
    p = np.clip(np.asarray(prob_same), eps, 1 - eps)
    return p / (1.0 - p)


def cllr(lr_same: np.ndarray, lr_diff: np.ndarray, eps: float = 1e-12) -> float:
    """
    Compute Cllr (log-likelihood-ratio cost).

    Lower is better; 0 is ideal.
    """
    lr_same = np.clip(np.asarray(lr_same), eps, None)
    lr_diff = np.clip(np.asarray(lr_diff), eps, None)
    c1 = np.mean(np.log2(1.0 + 1.0 / lr_same))
    c2 = np.mean(np.log2(1.0 + lr_diff))
    return 0.5 * float(c1 + c2)


def roc_summary(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    """Return compact ROC summary for reporting."""
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    fpr, tpr, _ = roc_curve(y_true, scores)
    return {
        "auc": float(roc_auc_score(y_true, scores)),
        "eer_approx": float(_eer_from_roc(fpr, tpr)),
    }


def _eer_from_roc(fpr: np.ndarray, tpr: np.ndarray) -> float:
    fnr = 1.0 - tpr
    idx = int(np.argmin(np.abs(fpr - fnr)))
    return float((fpr[idx] + fnr[idx]) / 2.0)


def tippett_coordinates(
    lr_same: np.ndarray,
    lr_diff: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return log10 LR arrays used to draw Tippett plots."""
    return {
        "same_log10_lr": np.sort(np.log10(np.asarray(lr_same))),
        "diff_log10_lr": np.sort(np.log10(np.asarray(lr_diff))),
    }


def cmc_top_k_accuracy(similarity_matrix: np.ndarray, query_ids: np.ndarray, gallery_ids: np.ndarray, k: int = 1) -> float:
    """Compute Top-k CMC accuracy from query-to-gallery similarity scores."""
    similarity_matrix = np.asarray(similarity_matrix)
    query_ids = np.asarray(query_ids)
    gallery_ids = np.asarray(gallery_ids)

    if similarity_matrix.shape != (len(query_ids), len(gallery_ids)):
        raise ValueError("Shape mismatch among similarity matrix and ID arrays.")

    correct = 0
    for i in range(len(query_ids)):
        ranked = np.argsort(similarity_matrix[i])[::-1]
        top_k_ids = gallery_ids[ranked[:k]]
        if query_ids[i] in top_k_ids:
            correct += 1
    return correct / len(query_ids) if len(query_ids) else 0.0
