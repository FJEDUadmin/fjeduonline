from __future__ import annotations

import csv
from pathlib import Path

from adductomics_api.repository import AdductRepository
from adductomics_api.schemas import (
    AnalysisResponse,
    CandidateAdduct,
    MRMTransition,
)
from adductomics_api.services.connectors import CsvAdductConnector
from adductomics_api.services.identifier import score_candidates
from adductomics_api.services.pathway import score_pathways


class AnalysisPipeline:
    def __init__(self, repository: AdductRepository) -> None:
        self.repository = repository

    def ingest_adduct_csv(self, file_path: str, source_name: str) -> int:
        connector = CsvAdductConnector(file_path=file_path, source_name=source_name)
        records = connector.load_records()
        return self.repository.upsert_adducts(records)

    def parse_transition_csv(self, file_path: str, sample_id: str) -> list[MRMTransition]:
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Transition CSV not found: {file_path}")

        transitions: list[MRMTransition] = []
        with csv_path.open("r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for idx, row in enumerate(reader, start=1):
                transitions.append(
                    MRMTransition(
                        transition_id=row.get("transition_id") or f"{sample_id}_T{idx}",
                        sample_id=sample_id,
                        precursor_mz=float(row["precursor_mz"]),
                        product_mz=float(row["product_mz"]),
                        neutral_loss=float(row["neutral_loss"]) if row.get("neutral_loss") else None,
                        retention_time=(
                            float(row["retention_time"]) if row.get("retention_time") else None
                        ),
                        intensity=float(row["intensity"]) if row.get("intensity") else None,
                    )
                )
        return transitions

    def analyze_transitions(
        self,
        transitions: list[MRMTransition],
        tolerance_ppm: float,
        neutral_loss_tolerance_da: float,
        top_k_per_transition: int,
    ) -> AnalysisResponse:
        all_candidates: list[CandidateAdduct] = []
        for transition in transitions:
            rows = self.repository.get_by_precursor_window(transition.precursor_mz, tolerance_ppm)
            scored = score_candidates(
                transition=transition,
                candidate_rows=rows,
                tolerance_ppm=tolerance_ppm,
                nl_tolerance_da=neutral_loss_tolerance_da,
                top_k=top_k_per_transition,
            )
            all_candidates.extend(scored)

        unique_by_key: dict[tuple[str, str], CandidateAdduct] = {}
        for candidate in all_candidates:
            key = (candidate.adduct_id, candidate.source_name)
            prev = unique_by_key.get(key)
            if prev is None or candidate.confidence_score > prev.confidence_score:
                unique_by_key[key] = candidate

        unique_candidates = list(unique_by_key.values())
        unique_candidates.sort(key=lambda c: c.confidence_score, reverse=True)

        pathway_scores = score_pathways(
            candidates=unique_candidates,
            pathway_population=self.repository.pathway_population(),
            total_population=self.repository.total_adduct_count(),
        )

        sample_id = transitions[0].sample_id if transitions else "unknown"
        return AnalysisResponse(
            sample_id=sample_id,
            transitions_analyzed=len(transitions),
            candidates=unique_candidates,
            pathway_scores=pathway_scores,
        )
