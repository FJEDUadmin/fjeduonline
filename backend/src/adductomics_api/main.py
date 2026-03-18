from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from adductomics_api.config import Settings, get_settings
from adductomics_api.repository import AdductRepository
from adductomics_api.schemas import (
    AnalysisResponse,
    AnalyzeCsvRequest,
    AnalyzeTransitionsRequest,
    IngestCsvRequest,
    IngestHmdbRequest,
    IngestMassBankRequest,
)
from adductomics_api.services.pipeline import AnalysisPipeline

app = FastAPI(title="DNA Adductomics Platform API", version="0.2.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_pipeline(settings: Settings = Depends(get_settings)) -> AnalysisPipeline:
    repo = AdductRepository(sqlite_path=settings.sqlite_path)
    return AnalysisPipeline(repository=repo, software_version=settings.app_version)


def _ensure_upload_dir(settings: Settings) -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_upload(file: UploadFile, upload_dir: Path, prefix: str) -> str:
    suffix = Path(file.filename or "upload.csv").suffix or ".csv"
    fname = f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}{suffix}"
    out_path = upload_dir / fname
    with out_path.open("wb") as fp:
        fp.write(file.file.read())
    return str(out_path)


@app.get("/")
def dashboard() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard static files are missing.")
    return FileResponse(index_path)


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


@app.post("/api/v1/ingest/adduct-bank/upload-csv")
def ingest_adduct_bank_upload_csv(
    source_name: str = Form(default="custom_upload"),
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    upload_path = _save_upload(file=file, upload_dir=_ensure_upload_dir(settings), prefix="adduct_bank")
    try:
        inserted = pipeline.ingest_adduct_csv(file_path=upload_path, source_name=source_name)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"CSV schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in CSV: {exc}") from exc
    return {
        "ingested_records": inserted,
        "source_name": source_name,
        "uploaded_file_path": upload_path,
    }


@app.post("/api/v1/ingest/adduct-bank/hmdb-csv")
def ingest_hmdb_csv(
    payload: IngestHmdbRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> dict:
    try:
        inserted = pipeline.ingest_hmdb_csv(
            file_path=payload.file_path,
            source_name=payload.source_name,
            ion_mode=payload.ion_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"HMDB schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in HMDB CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": payload.source_name,
        "ion_mode": payload.ion_mode,
    }


@app.post("/api/v1/ingest/adduct-bank/upload-hmdb")
def ingest_hmdb_upload(
    source_name: str = Form(default="hmdb"),
    ion_mode: str = Form(default="protonated"),
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    upload_path = _save_upload(file=file, upload_dir=_ensure_upload_dir(settings), prefix="hmdb_export")
    try:
        inserted = pipeline.ingest_hmdb_csv(
            file_path=upload_path,
            source_name=source_name,
            ion_mode=ion_mode,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"HMDB schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in HMDB CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": source_name,
        "ion_mode": ion_mode,
        "uploaded_file_path": upload_path,
    }


@app.post("/api/v1/ingest/adduct-bank/massbank-csv")
def ingest_massbank_csv(
    payload: IngestMassBankRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> dict:
    try:
        inserted = pipeline.ingest_massbank_csv(
            file_path=payload.file_path,
            source_name=payload.source_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"MassBank schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in MassBank CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": payload.source_name,
    }


@app.post("/api/v1/ingest/adduct-bank/upload-massbank")
def ingest_massbank_upload(
    source_name: str = Form(default="massbank"),
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    upload_path = _save_upload(
        file=file,
        upload_dir=_ensure_upload_dir(settings),
        prefix="massbank_export",
    )
    try:
        inserted = pipeline.ingest_massbank_csv(
            file_path=upload_path,
            source_name=source_name,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"MassBank schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in MassBank CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": source_name,
        "uploaded_file_path": upload_path,
    }


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
        rt_tolerance_min=payload.rt_tolerance_min,
        isotope_tolerance=payload.isotope_tolerance,
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
        rt_tolerance_min=payload.rt_tolerance_min,
        isotope_tolerance=payload.isotope_tolerance,
        top_k_per_transition=payload.top_k_per_transition,
    )


@app.post("/api/v1/analyze/mrm-nl/upload-csv", response_model=AnalysisResponse)
def analyze_mrm_nl_upload_csv(
    sample_id: str = Form(...),
    tolerance_ppm: float = Form(default=10.0),
    neutral_loss_tolerance_da: float = Form(default=0.5),
    rt_tolerance_min: float = Form(default=0.5),
    isotope_tolerance: float = Form(default=0.15),
    top_k_per_transition: int = Form(default=5),
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> AnalysisResponse:
    upload_path = _save_upload(
        file=file,
        upload_dir=_ensure_upload_dir(settings),
        prefix=f"transitions_{sample_id}",
    )
    try:
        transitions = pipeline.parse_transition_csv(upload_path, sample_id=sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"CSV schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in CSV: {exc}") from exc

    return pipeline.analyze_transitions(
        transitions=transitions,
        tolerance_ppm=tolerance_ppm,
        neutral_loss_tolerance_da=neutral_loss_tolerance_da,
        rt_tolerance_min=rt_tolerance_min,
        isotope_tolerance=isotope_tolerance,
        top_k_per_transition=top_k_per_transition,
    )


@app.get("/api/v1/adducts")
def list_adducts(
    limit: int = Query(default=50, ge=1, le=1000),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
) -> list[dict]:
    return pipeline.repository.list_adducts(limit=limit)
