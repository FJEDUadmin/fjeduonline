from typing import Literal

from pydantic import BaseModel, Field


class AdductRecord(BaseModel):
    adduct_id: str = Field(..., description="Unique adduct identifier in source dataset")
    source_name: str = Field(..., description="Data bank or source label")
    adduct_name: str
    precursor_mz: float = Field(..., gt=0)
    product_mz: float | None = Field(default=None, gt=0)
    neutral_loss: float | None = Field(default=None, gt=0)
    expected_rt: float | None = Field(default=None, gt=0, description="Expected retention time in minutes")
    isotope_ratio: float | None = Field(
        default=None, ge=0, description="Expected isotope ratio proxy for matching"
    )
    formula: str | None = None
    smiles: str | None = None
    pathway: str | None = Field(default=None, description="Canonical or inferred pathway")
    evidence_level: Literal["curated", "reported", "predicted"] = "reported"


class MRMTransition(BaseModel):
    transition_id: str
    sample_id: str
    precursor_mz: float = Field(..., gt=0)
    product_mz: float = Field(..., gt=0)
    neutral_loss: float | None = Field(default=None, gt=0)
    retention_time: float | None = Field(default=None, gt=0)
    isotope_ratio: float | None = Field(default=None, ge=0)
    intensity: float | None = Field(default=None, ge=0)


class CandidateAdduct(BaseModel):
    adduct_id: str
    adduct_name: str
    source_name: str
    pathway: str | None = None
    ppm_error: float
    nl_error: float | None = None
    rt_error: float | None = None
    isotope_error: float | None = None
    confidence_score: float = Field(..., ge=0, le=1)
    confidence_level: Literal["Level 2A", "Level 2B", "Level 3", "Level 4"]
    evidence_count: int = Field(..., ge=1)
    component_scores: dict[str, float] = Field(default_factory=dict)
    matched_by: list[str] = Field(default_factory=list)


class PathwayScore(BaseModel):
    pathway: str
    hits: int = Field(..., ge=0)
    population_size: int = Field(..., ge=0)
    enrichment_score: float = Field(..., ge=0)
    p_value: float = Field(..., ge=0, le=1)


class IngestCsvRequest(BaseModel):
    file_path: str = Field(..., description="Server-local file path of adduct CSV")
    source_name: str = Field(default="custom_csv")


class IngestHmdbRequest(BaseModel):
    file_path: str = Field(..., description="Server-local HMDB export CSV path")
    source_name: str = Field(default="hmdb")
    ion_mode: Literal["neutral", "protonated"] = "protonated"


class IngestMassBankRequest(BaseModel):
    file_path: str = Field(..., description="Server-local MassBank export CSV path")
    source_name: str = Field(default="massbank")


class IngestMetlinRequest(BaseModel):
    file_path: str = Field(..., description="Server-local METLIN export CSV path")
    source_name: str = Field(default="metlin")


class IngestPubChemRequest(BaseModel):
    file_path: str = Field(..., description="Server-local PubChem export CSV path")
    source_name: str = Field(default="pubchem")
    ion_mode: Literal["neutral", "protonated"] = "protonated"


class IngestLiteratureRequest(BaseModel):
    file_path: str = Field(..., description="Server-local literature supplementary CSV path")
    source_name: str = Field(default="literature")


class AnalyzeToolCsvRequest(BaseModel):
    tool: Literal["msdial", "mzmine", "skyline"]
    file_path: str = Field(..., description="Server-local CSV path exported by the selected tool")
    sample_id: str
    tolerance_ppm: float = Field(default=10.0, gt=0)
    neutral_loss_tolerance_da: float = Field(default=0.5, gt=0)
    rt_tolerance_min: float = Field(default=0.5, gt=0)
    isotope_tolerance: float = Field(default=0.15, gt=0)
    top_k_per_transition: int = Field(default=5, gt=0, le=50)


class AnalyzeTransitionsRequest(BaseModel):
    transitions: list[MRMTransition]
    tolerance_ppm: float = Field(default=10.0, gt=0)
    neutral_loss_tolerance_da: float = Field(default=0.5, gt=0)
    rt_tolerance_min: float = Field(default=0.5, gt=0)
    isotope_tolerance: float = Field(default=0.15, gt=0)
    top_k_per_transition: int = Field(default=5, gt=0, le=50)


class AnalyzeCsvRequest(BaseModel):
    file_path: str = Field(..., description="Server-local CSV path for MRM/NL transitions")
    sample_id: str
    tolerance_ppm: float = Field(default=10.0, gt=0)
    neutral_loss_tolerance_da: float = Field(default=0.5, gt=0)
    rt_tolerance_min: float = Field(default=0.5, gt=0)
    isotope_tolerance: float = Field(default=0.15, gt=0)
    top_k_per_transition: int = Field(default=5, gt=0, le=50)


class AnalysisParameters(BaseModel):
    tolerance_ppm: float
    neutral_loss_tolerance_da: float
    rt_tolerance_min: float
    isotope_tolerance: float
    top_k_per_transition: int
    scoring_version: str
    confidence_framework: str


class AnalysisMetadata(BaseModel):
    run_id: str
    generated_at: str
    software_version: str
    parameters: AnalysisParameters


class AnalysisResponse(BaseModel):
    sample_id: str
    transitions_analyzed: int
    candidates: list[CandidateAdduct]
    pathway_scores: list[PathwayScore]
    metadata: AnalysisMetadata


class RStatisticsRequest(BaseModel):
    sample_id: str
    candidates: list[CandidateAdduct]
    pathway_scores: list[PathwayScore]
    report_title: str = "DNA Adductomics Statistical Summary"


class RStatisticsResponse(BaseModel):
    status: Literal["completed", "skipped", "failed"]
    message: str
    output_path: str | None = None
    script_path: str | None = None
