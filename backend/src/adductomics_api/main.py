from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from adductomics_api.config import Settings, get_settings
from adductomics_api.repository import AdductRepository
from adductomics_api.schemas import (
    AnalysisResponse,
    AnalyzeCsvRequest,
    AnalyzeToolCsvRequest,
    AnalyzeTransitionsRequest,
    IngestCsvRequest,
    IngestHmdbRequest,
    IngestLiteratureRequest,
    IngestMassBankRequest,
    IngestMetlinRequest,
    IngestPubChemRequest,
    RStatisticsRequest,
    RStatisticsResponse,
)
from adductomics_api.services.pipeline import AnalysisPipeline
from adductomics_api.services.r_stats import RStatisticsRunner

app = FastAPI(title="DNA Adductomics Platform API", version="0.3.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_pipeline(settings: Settings = Depends(get_settings)) -> AnalysisPipeline:
    repo = AdductRepository(sqlite_path=settings.sqlite_path)
    return AnalysisPipeline(repository=repo, software_version=settings.app_version)


def get_r_stats_runner(settings: Settings = Depends(get_settings)) -> RStatisticsRunner:
    return RStatisticsRunner(
        rscript_binary=settings.rscript_binary,
        script_path=settings.r_module_script_path,
        output_dir=settings.r_output_dir,
    )


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


def _resolve_demo_file(settings: Settings, filename: str) -> str:
    return str(Path(settings.demo_data_dir) / filename)


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


@app.post("/api/v1/ingest/adduct-bank/metlin-csv")
def ingest_metlin_csv(
    payload: IngestMetlinRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> dict:
    try:
        inserted = pipeline.ingest_metlin_csv(
            file_path=payload.file_path,
            source_name=payload.source_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"METLIN schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in METLIN CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": payload.source_name,
    }


@app.post("/api/v1/ingest/adduct-bank/upload-metlin")
def ingest_metlin_upload(
    source_name: str = Form(default="metlin"),
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    upload_path = _save_upload(
        file=file,
        upload_dir=_ensure_upload_dir(settings),
        prefix="metlin_export",
    )
    try:
        inserted = pipeline.ingest_metlin_csv(
            file_path=upload_path,
            source_name=source_name,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"METLIN schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in METLIN CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": source_name,
        "uploaded_file_path": upload_path,
    }


@app.post("/api/v1/ingest/adduct-bank/pubchem-csv")
def ingest_pubchem_csv(
    payload: IngestPubChemRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> dict:
    try:
        inserted = pipeline.ingest_pubchem_csv(
            file_path=payload.file_path,
            source_name=payload.source_name,
            ion_mode=payload.ion_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"PubChem schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in PubChem CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": payload.source_name,
        "ion_mode": payload.ion_mode,
    }


@app.post("/api/v1/ingest/adduct-bank/upload-pubchem")
def ingest_pubchem_upload(
    source_name: str = Form(default="pubchem"),
    ion_mode: str = Form(default="protonated"),
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    ion_mode_value = ion_mode.strip().lower()
    upload_path = _save_upload(file=file, upload_dir=_ensure_upload_dir(settings), prefix="pubchem_export")
    try:
        inserted = pipeline.ingest_pubchem_csv(
            file_path=upload_path,
            source_name=source_name,
            ion_mode=ion_mode_value,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"PubChem schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in PubChem CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": source_name,
        "ion_mode": ion_mode_value,
        "uploaded_file_path": upload_path,
    }


@app.post("/api/v1/ingest/adduct-bank/literature-csv")
def ingest_literature_csv(
    payload: IngestLiteratureRequest, pipeline: AnalysisPipeline = Depends(get_pipeline)
) -> dict:
    try:
        inserted = pipeline.ingest_literature_csv(
            file_path=payload.file_path,
            source_name=payload.source_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Literature schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in literature CSV: {exc}") from exc

    return {
        "ingested_records": inserted,
        "source_name": payload.source_name,
    }


@app.post("/api/v1/ingest/adduct-bank/upload-literature")
def ingest_literature_upload(
    source_name: str = Form(default="literature"),
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> dict:
    upload_path = _save_upload(
        file=file,
        upload_dir=_ensure_upload_dir(settings),
        prefix="literature_export",
    )
    try:
        inserted = pipeline.ingest_literature_csv(
            file_path=upload_path,
            source_name=source_name,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Literature schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in literature CSV: {exc}") from exc

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


@app.post("/api/v1/demo/run", response_model=AnalysisResponse)
def run_demo_analysis(
    sample_id: str = Form(default="DEMO_SAMPLE_001"),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    settings: Settings = Depends(get_settings),
) -> AnalysisResponse:
    try:
        pipeline.ingest_adduct_csv(
            file_path=_resolve_demo_file(settings, "sample_adduct_bank.csv"),
            source_name="demo_generic",
        )
        pipeline.ingest_hmdb_csv(
            file_path=_resolve_demo_file(settings, "sample_hmdb_export.csv"),
            source_name="demo_hmdb",
            ion_mode="protonated",
        )
        pipeline.ingest_massbank_csv(
            file_path=_resolve_demo_file(settings, "sample_massbank_export.csv"),
            source_name="demo_massbank",
        )
        transitions = pipeline.parse_transition_csv(
            file_path=_resolve_demo_file(settings, "sample_mrm_nl.csv"),
            sample_id=sample_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Demo data missing: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Demo data invalid: {exc}") from exc

    return pipeline.analyze_transitions(
        transitions=transitions,
        tolerance_ppm=settings.default_tolerance_ppm,
        neutral_loss_tolerance_da=settings.default_nl_tolerance_da,
        rt_tolerance_min=settings.default_rt_tolerance_min,
        isotope_tolerance=settings.default_isotope_tolerance,
        top_k_per_transition=settings.max_candidates_per_transition,
    )


@app.post("/api/v1/analyze/tool-csv", response_model=AnalysisResponse)
def analyze_tool_csv(
    payload: AnalyzeToolCsvRequest,
    pipeline: AnalysisPipeline = Depends(get_pipeline),
) -> AnalysisResponse:
    try:
        transitions = pipeline.parse_tool_export_csv(
            tool=payload.tool,
            file_path=payload.file_path,
            sample_id=payload.sample_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Tool CSV schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in tool CSV: {exc}") from exc

    return pipeline.analyze_transitions(
        transitions=transitions,
        tolerance_ppm=payload.tolerance_ppm,
        neutral_loss_tolerance_da=payload.neutral_loss_tolerance_da,
        rt_tolerance_min=payload.rt_tolerance_min,
        isotope_tolerance=payload.isotope_tolerance,
        top_k_per_transition=payload.top_k_per_transition,
    )


@app.post("/api/v1/analyze/tool/upload-csv", response_model=AnalysisResponse)
def analyze_tool_upload_csv(
    tool: str = Form(...),
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
    tool_name = tool.strip().lower()
    upload_path = _save_upload(
        file=file,
        upload_dir=_ensure_upload_dir(settings),
        prefix=f"{tool_name}_{sample_id}",
    )
    try:
        transitions = pipeline.parse_tool_export_csv(
            tool=tool_name,  # validated in parser entrypoint
            file_path=upload_path,
            sample_id=sample_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Tool CSV schema missing field: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value in tool CSV: {exc}") from exc

    return pipeline.analyze_transitions(
        transitions=transitions,
        tolerance_ppm=tolerance_ppm,
        neutral_loss_tolerance_da=neutral_loss_tolerance_da,
        rt_tolerance_min=rt_tolerance_min,
        isotope_tolerance=isotope_tolerance,
        top_k_per_transition=top_k_per_transition,
    )


@app.get("/api/v1/stats/r-module/health")
def r_module_health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "rscript_binary": settings.rscript_binary,
        "rscript_available": shutil.which(settings.rscript_binary) is not None,
        "script_path": settings.r_module_script_path,
        "script_exists": Path(settings.r_module_script_path).exists(),
        "output_dir": settings.r_output_dir,
    }


@app.post("/api/v1/stats/r-report", response_model=RStatisticsResponse)
def run_r_statistics_report(
    payload: RStatisticsRequest,
    runner: RStatisticsRunner = Depends(get_r_stats_runner),
) -> RStatisticsResponse:
    return runner.run(payload)


@app.get("/api/v1/adducts")
def list_adducts(
    limit: int = Query(default=50, ge=1, le=1000),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
) -> list[dict]:
    return pipeline.repository.list_adducts(limit=limit)


@app.get("/api/v1/templates/metlin-csv")
def download_metlin_template(settings: Settings = Depends(get_settings)) -> FileResponse:
    template_path = Path(settings.demo_data_dir) / "templates" / "metlin_template.csv"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template file not found: {template_path}")
    return FileResponse(
        path=template_path,
        filename="metlin_template.csv",
        media_type="text/csv",
    )
