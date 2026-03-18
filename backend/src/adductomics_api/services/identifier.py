from __future__ import annotations

from dataclasses import dataclass

from adductomics_api.schemas import CandidateAdduct, MRMTransition

SCORING_VERSION = "v2.0"


@dataclass(frozen=True)
class ScoringWeights:
    precursor_mz: float = 0.45
    product_mz: float = 0.20
    neutral_loss: float = 0.15
    retention_time: float = 0.10
    isotope_ratio: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "precursor_mz": self.precursor_mz,
            "product_mz": self.product_mz,
            "neutral_loss": self.neutral_loss,
            "retention_time": self.retention_time,
            "isotope_ratio": self.isotope_ratio,
        }


def ppm_error(observed_mz: float, reference_mz: float) -> float:
    return ((observed_mz - reference_mz) / reference_mz) * 1_000_000


def _bounded_similarity(error_abs: float, tolerance: float) -> float:
    if tolerance <= 0:
        return 0.0
    value = 1.0 - (error_abs / tolerance)
    return max(0.0, min(1.0, value))


def _weighted_average(component_scores: dict[str, float], weights: ScoringWeights) -> float:
    weights_map = weights.as_dict()
    available = {k: v for k, v in component_scores.items() if k in weights_map}
    if not available:
        return 0.0
    weight_sum = sum(weights_map[k] for k in available.keys())
    if weight_sum <= 0:
        return 0.0
    return sum(available[k] * (weights_map[k] / weight_sum) for k in available.keys())


def score_candidates(
    transition: MRMTransition,
    candidate_rows: list[dict],
    tolerance_ppm: float,
    nl_tolerance_da: float,
    rt_tolerance_min: float,
    isotope_tolerance: float,
    top_k: int,
    weights: ScoringWeights | None = None,
) -> list[CandidateAdduct]:
    score_weights = weights or ScoringWeights()
    scored: list[CandidateAdduct] = []
    for row in candidate_rows:
        mz_ppm = ppm_error(transition.precursor_mz, row["precursor_mz"])
        component_scores: dict[str, float] = {
            "precursor_mz": _bounded_similarity(abs(mz_ppm), tolerance_ppm)
        }
        matched_by = ["precursor_mz"]

        nl_error: float | None = None
        if transition.neutral_loss is not None and row.get("neutral_loss") is not None:
            nl_error = transition.neutral_loss - float(row["neutral_loss"])
            component_scores["neutral_loss"] = _bounded_similarity(abs(nl_error), nl_tolerance_da)
            matched_by.append("neutral_loss")

        if row.get("product_mz") is not None:
            prod_ppm = ppm_error(transition.product_mz, float(row["product_mz"]))
            component_scores["product_mz"] = _bounded_similarity(abs(prod_ppm), tolerance_ppm)
            matched_by.append("product_mz")

        rt_error: float | None = None
        if transition.retention_time is not None and row.get("expected_rt") is not None:
            rt_error = transition.retention_time - float(row["expected_rt"])
            component_scores["retention_time"] = _bounded_similarity(abs(rt_error), rt_tolerance_min)
            matched_by.append("retention_time")

        isotope_error: float | None = None
        if transition.isotope_ratio is not None and row.get("isotope_ratio") is not None:
            isotope_error = transition.isotope_ratio - float(row["isotope_ratio"])
            component_scores["isotope_ratio"] = _bounded_similarity(
                abs(isotope_error), isotope_tolerance
            )
            matched_by.append("isotope_ratio")

        confidence = _weighted_average(component_scores=component_scores, weights=score_weights)
        candidate = CandidateAdduct(
            adduct_id=row["adduct_id"],
            adduct_name=row["adduct_name"],
            source_name=row["source_name"],
            pathway=row.get("pathway"),
            ppm_error=mz_ppm,
            nl_error=nl_error,
            rt_error=rt_error,
            isotope_error=isotope_error,
            confidence_score=round(confidence, 5),
            component_scores={k: round(v, 5) for k, v in component_scores.items()},
            matched_by=matched_by,
        )
        scored.append(candidate)

    scored.sort(key=lambda x: x.confidence_score, reverse=True)
    return scored[:top_k]
