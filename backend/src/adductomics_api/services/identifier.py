from __future__ import annotations

from adductomics_api.schemas import CandidateAdduct, MRMTransition


def ppm_error(observed_mz: float, reference_mz: float) -> float:
    return ((observed_mz - reference_mz) / reference_mz) * 1_000_000


def _bounded_similarity(error_abs: float, tolerance: float) -> float:
    if tolerance <= 0:
        return 0.0
    value = 1.0 - (error_abs / tolerance)
    return max(0.0, min(1.0, value))


def score_candidates(
    transition: MRMTransition,
    candidate_rows: list[dict],
    tolerance_ppm: float,
    nl_tolerance_da: float,
    top_k: int,
) -> list[CandidateAdduct]:
    scored: list[CandidateAdduct] = []
    for row in candidate_rows:
        mz_ppm = ppm_error(transition.precursor_mz, row["precursor_mz"])
        mz_score = _bounded_similarity(abs(mz_ppm), tolerance_ppm)
        matched_by = ["precursor_mz"]

        nl_error: float | None = None
        if transition.neutral_loss is not None and row.get("neutral_loss") is not None:
            nl_error = transition.neutral_loss - float(row["neutral_loss"])
            nl_score = _bounded_similarity(abs(nl_error), nl_tolerance_da)
            matched_by.append("neutral_loss")
        else:
            nl_score = 0.4

        if row.get("product_mz") is not None:
            prod_ppm = ppm_error(transition.product_mz, float(row["product_mz"]))
            prod_score = _bounded_similarity(abs(prod_ppm), tolerance_ppm)
            matched_by.append("product_mz")
        else:
            prod_score = 0.3

        confidence = 0.55 * mz_score + 0.20 * nl_score + 0.25 * prod_score
        candidate = CandidateAdduct(
            adduct_id=row["adduct_id"],
            adduct_name=row["adduct_name"],
            source_name=row["source_name"],
            pathway=row.get("pathway"),
            ppm_error=mz_ppm,
            nl_error=nl_error,
            confidence_score=round(confidence, 5),
            matched_by=matched_by,
        )
        scored.append(candidate)

    scored.sort(key=lambda x: x.confidence_score, reverse=True)
    return scored[:top_k]
