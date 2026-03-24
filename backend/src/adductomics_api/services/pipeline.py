from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from adductomics_api.repository import AdductRepository
from adductomics_api.schemas import (
    AnalysisMetadata,
    AnalysisParameters,
    AnalysisResponse,
    CandidateAdduct,
    MRMTransition,
)
from adductomics_api.services.connectors import (
    CsvAdductConnector,
    HmdbCsvConnector,
    LiteratureCsvConnector,
    MassBankCsvConnector,
    MetlinCsvConnector,
    PubChemCsvConnector,
)
from adductomics_api.services.csv_utils import get_first, prepare_row, read_csv_rows_with_fallback
from adductomics_api.services.identifier import CONFIDENCE_FRAMEWORK, SCORING_VERSION, score_candidates
from adductomics_api.services.pathway import score_pathways
from adductomics_api.services.tool_parsers import ToolParserType, parse_tool_csv


class AnalysisPipeline:
    def __init__(self, repository: AdductRepository, software_version: str = "0.3.0") -> None:
        self.repository = repository
        self.software_version = software_version

    def ingest_adduct_csv(self, file_path: str, source_name: str) -> int:
        connector = CsvAdductConnector(file_path=file_path, source_name=source_name)
        records = connector.load_records()
        return self.repository.upsert_adducts(records)

    def ingest_hmdb_csv(self, file_path: str, source_name: str, ion_mode: str = "protonated") -> int:
        connector = HmdbCsvConnector(
            file_path=file_path,
            source_name=source_name,
            ion_mode=ion_mode,
        )
        records = connector.load_records()
        return self.repository.upsert_adducts(records)

    def ingest_massbank_csv(self, file_path: str, source_name: str) -> int:
        connector = MassBankCsvConnector(file_path=file_path, source_name=source_name)
        records = connector.load_records()
        return self.repository.upsert_adducts(records)

    def ingest_metlin_csv(self, file_path: str, source_name: str) -> int:
        connector = MetlinCsvConnector(file_path=file_path, source_name=source_name)
        records = connector.load_records()
        return self.repository.upsert_adducts(records)

    def ingest_pubchem_csv(self, file_path: str, source_name: str, ion_mode: str = "protonated") -> int:
        connector = PubChemCsvConnector(
            file_path=file_path,
            source_name=source_name,
            ion_mode=ion_mode,
        )
        records = connector.load_records()
        return self.repository.upsert_adducts(records)

    def ingest_literature_csv(self, file_path: str, source_name: str) -> int:
        connector = LiteratureCsvConnector(file_path=file_path, source_name=source_name)
        records = connector.load_records()
        return self.repository.upsert_adducts(records)

    def parse_transition_csv(self, file_path: str, sample_id: str) -> list[MRMTransition]:
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Transition CSV not found: {file_path}")

        transitions: list[MRMTransition] = []
        for idx, raw_row in enumerate(read_csv_rows_with_fallback(csv_path), start=1):
            row = prepare_row(raw_row)
            precursor_raw = get_first(row, ["precursor_mz", "precursor_m_z", "mz", "q1"])
            product_raw = get_first(row, ["product_mz", "product_m_z", "fragment_mz", "q3"])
            if precursor_raw is None:
                raise KeyError("precursor_mz")
            precursor_mz = float(precursor_raw)
            if product_raw is None:
                raise KeyError("product_mz")
            product_mz = float(product_raw)
            neutral_loss_raw = get_first(row, ["neutral_loss", "nl"])
            neutral_loss = (
                float(neutral_loss_raw)
                if neutral_loss_raw
                else (precursor_mz - product_mz if precursor_mz > product_mz else None)
            )
            rt_raw = get_first(row, ["retention_time", "rt"])
            isotope_raw = get_first(row, ["isotope_ratio"])
            intensity_raw = get_first(row, ["intensity", "area", "height"])
            transitions.append(
                MRMTransition(
                    transition_id=get_first(row, ["transition_id", "id", "transition_name"]) or f"{sample_id}_T{idx}",
                    sample_id=sample_id,
                    precursor_mz=precursor_mz,
                    product_mz=product_mz,
                    neutral_loss=neutral_loss,
                    retention_time=float(rt_raw) if rt_raw else None,
                    isotope_ratio=float(isotope_raw) if isotope_raw else None,
                    intensity=float(intensity_raw) if intensity_raw else None,
                )
            )
        return transitions

    def parse_tool_export_csv(
        self,
        tool: ToolParserType,
        file_path: str,
        sample_id: str,
    ) -> list[MRMTransition]:
        return parse_tool_csv(tool=tool, file_path=file_path, sample_id=sample_id)

    def analyze_transitions(
        self,
        transitions: list[MRMTransition],
        tolerance_ppm: float,
        neutral_loss_tolerance_da: float,
        rt_tolerance_min: float,
        isotope_tolerance: float,
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
                rt_tolerance_min=rt_tolerance_min,
                isotope_tolerance=isotope_tolerance,
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
        metadata = AnalysisMetadata(
            run_id=f"run_{uuid4().hex[:12]}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            software_version=self.software_version,
            parameters=AnalysisParameters(
                tolerance_ppm=tolerance_ppm,
                neutral_loss_tolerance_da=neutral_loss_tolerance_da,
                rt_tolerance_min=rt_tolerance_min,
                isotope_tolerance=isotope_tolerance,
                top_k_per_transition=top_k_per_transition,
                scoring_version=SCORING_VERSION,
                confidence_framework=CONFIDENCE_FRAMEWORK,
            ),
        )
        return AnalysisResponse(
            sample_id=sample_id,
            transitions_analyzed=len(transitions),
            candidates=unique_candidates,
            pathway_scores=pathway_scores,
            metadata=metadata,
        )
