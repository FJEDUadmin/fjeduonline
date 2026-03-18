from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query

from adductomics_api.config import Settings, get_settings
from adductomics_api.repository import AdductRepository
from adductomics_api.schemas import (
    AnalysisResponse,
    AnalyzeCsvRequest,
    AnalyzeTransitionsRequest,
    IngestCsvRequest,
)
from adductomics_api.services.pipeline import AnalysisPipeline

app = FastAPI(title="DNA Adductomics Platform API", version="0.1.0")


def get_pipeline(settings: Settings = Depends(get_settings)) -> AnalysisPipeline:
    repo = AdductRepository(sqlite_path=settings.sqlite_path)
    return AnalysisPipeline(repository=repo)


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.post("/api/v1/ingest/adduct-bank/csv")
def ingest_adduct_bank_csv(
    payload: IngestCsvRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> dict:
    try:
        inserted = pipeline.ingest_adduct_csv(
            file_path=payload.file_path,
            source_name=payload.source_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"CSV schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in CSV: {exc}") from exc

    return {"ingested_records": inserted, "source_name": payload.source_name}


@app.post("/api/v1/analyze/mrm-nl", response_model=AnalysisResponse)
def analyze_mrm_nl(
    payload: AnalyzeTransitionsRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> AnalysisResponse:
    if not payload.transitions:
        raise HTTPException(status_code=400, detail="No transitions provided.")

    return pipeline.analyze_transitions(
        transitions=payload.transitions,
        tolerance_ppm=payload.tolerance_ppm,
        neutral_loss_tolerance_da=payload.neutral_loss_tolerance_da,
        top_k_per_transition=payload.top_k_per_transition,
    )


@app.post("/api/v1/analyze/mrm-nl/csv", response_model=AnalysisResponse)
def analyze_mrm_nl_csv(
    payload: AnalyzeCsvRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> AnalysisResponse:
    try:
        transitions = pipeline.parse_transition_csv(payload.file_path, sample_id=payload.sample_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"CSV schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in CSV: {exc}") from exc

    return pipeline.analyze_transitions(
        transitions=transitions,
        tolerance_ppm=payload.tolerance_ppm,
        neutral_loss_tolerance_da=payload.neutral_loss_tolerance_da,
        top_k_per_transition=payload.top_k_per_transition,
    )


@app.get("/api/v1/adducts")
def list_adducts(
    limit: int = Query(default=50, ge=1, le=1000),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
) -> list[dict]:
    return pipeline.repository.list_adducts(limit=limit)
