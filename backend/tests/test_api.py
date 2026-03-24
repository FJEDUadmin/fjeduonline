from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adductomics_api.config import get_settings
from adductomics_api.services.identifier import SCORING_VERSION
from adductomics_api.main import app


@pytest.fixture(autouse=True)
def _isolate_test_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADDUCT_SQLITE_PATH", str(tmp_path / "api_test.db"))
    monkeypatch.setenv("ADDUCT_UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_dashboard_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "DNA Adductomics Platform" in response.text


def test_demo_run_endpoint() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/demo/run", data={"sample_id": "DEMO_API_S1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_id"] == "DEMO_API_S1"
    assert payload["transitions_analyzed"] == 3
    assert len(payload["candidates"]) >= 1


def test_ingest_and_analyze_endpoints() -> None:
    client = TestClient(app)
    data_dir = Path(__file__).resolve().parents[1] / "data"

    ingest_resp = client.post(
        "/api/v1/ingest/adduct-bank/csv",
        json={
            "file_path": str(data_dir / "sample_adduct_bank.csv"),
            "source_name": "test_bank",
        },
    )
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["ingested_records"] == 5

    analyze_resp = client.post(
        "/api/v1/analyze/mrm-nl/csv",
        json={
            "file_path": str(data_dir / "sample_mrm_nl.csv"),
            "sample_id": "API_S1",
            "tolerance_ppm": 15.0,
            "neutral_loss_tolerance_da": 0.2,
            "top_k_per_transition": 3,
        },
    )
    assert analyze_resp.status_code == 200
    result = analyze_resp.json()
    assert result["sample_id"] == "API_S1"
    assert result["transitions_analyzed"] == 3
    assert len(result["candidates"]) >= 3
    assert result["metadata"]["parameters"]["scoring_version"] == SCORING_VERSION


def test_massbank_file_path_ingest_endpoint() -> None:
    client = TestClient(app)
    data_dir = Path(__file__).resolve().parents[1] / "data"

    response = client.post(
        "/api/v1/ingest/adduct-bank/massbank-csv",
        json={
            "file_path": str(data_dir / "sample_massbank_export.csv"),
            "source_name": "massbank_file_path",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ingested_records"] == 3
    assert payload["source_name"] == "massbank_file_path"


def test_metlin_file_path_ingest_endpoint() -> None:
    client = TestClient(app)
    data_dir = Path(__file__).resolve().parents[1] / "data"

    response = client.post(
        "/api/v1/ingest/adduct-bank/metlin-csv",
        json={
            "file_path": str(data_dir / "sample_metlin_export.csv"),
            "source_name": "metlin_file_path",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ingested_records"] == 2
    assert payload["source_name"] == "metlin_file_path"


def test_pubchem_and_literature_ingest_endpoints() -> None:
    client = TestClient(app)
    data_dir = Path(__file__).resolve().parents[1] / "data"

    pubchem_resp = client.post(
        "/api/v1/ingest/adduct-bank/pubchem-csv",
        json={
            "file_path": str(data_dir / "sample_pubchem_export.csv"),
            "source_name": "pubchem_api",
            "ion_mode": "protonated",
        },
    )
    assert pubchem_resp.status_code == 200
    assert pubchem_resp.json()["ingested_records"] == 2

    lit_resp = client.post(
        "/api/v1/ingest/adduct-bank/literature-csv",
        json={
            "file_path": str(data_dir / "sample_literature_supplement.csv"),
            "source_name": "literature_api",
        },
    )
    assert lit_resp.status_code == 200
    assert lit_resp.json()["ingested_records"] == 2


def test_hmdb_upload_alias_columns_endpoint() -> None:
    client = TestClient(app)
    hmdb_alias_csv = (
        "Accession ID,Common Name,Monoisotopic Molecular Weight,Chemical Formula,Pathways\n"
        "HMDBX0002,Uploaded Alias Compound,199.1111,C7H9N3O3,DNA Damage Response\n"
    ).encode("utf-8")

    response = client.post(
        "/api/v1/ingest/adduct-bank/upload-hmdb",
        data={"source_name": "hmdb_alias_upload", "ion_mode": "protonated"},
        files={"file": ("hmdb_alias.csv", BytesIO(hmdb_alias_csv), "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ingested_records"] == 1
    assert payload["source_name"] == "hmdb_alias_upload"


def test_upload_ingest_and_hmdb_endpoints() -> None:
    client = TestClient(app)
    data_dir = Path(__file__).resolve().parents[1] / "data"

    generic_bytes = (data_dir / "sample_adduct_bank.csv").read_bytes()
    ingest_upload = client.post(
        "/api/v1/ingest/adduct-bank/upload-csv",
        data={"source_name": "uploaded_bank"},
        files={"file": ("sample_adduct_bank.csv", BytesIO(generic_bytes), "text/csv")},
    )
    assert ingest_upload.status_code == 200
    assert ingest_upload.json()["ingested_records"] == 5

    hmdb_bytes = (data_dir / "sample_hmdb_export.csv").read_bytes()
    hmdb_upload = client.post(
        "/api/v1/ingest/adduct-bank/upload-hmdb",
        data={"source_name": "hmdb_uploaded", "ion_mode": "protonated"},
        files={"file": ("sample_hmdb_export.csv", BytesIO(hmdb_bytes), "text/csv")},
    )
    assert hmdb_upload.status_code == 200
    assert hmdb_upload.json()["ingested_records"] == 3

    pubchem_bytes = (data_dir / "sample_pubchem_export.csv").read_bytes()
    pubchem_upload = client.post(
        "/api/v1/ingest/adduct-bank/upload-pubchem",
        data={"source_name": "pubchem_uploaded", "ion_mode": "protonated"},
        files={"file": ("sample_pubchem_export.csv", BytesIO(pubchem_bytes), "text/csv")},
    )
    assert pubchem_upload.status_code == 200
    assert pubchem_upload.json()["ingested_records"] == 2

    literature_bytes = (data_dir / "sample_literature_supplement.csv").read_bytes()
    literature_upload = client.post(
        "/api/v1/ingest/adduct-bank/upload-literature",
        data={"source_name": "literature_uploaded"},
        files={"file": ("sample_literature_supplement.csv", BytesIO(literature_bytes), "text/csv")},
    )
    assert literature_upload.status_code == 200
    assert literature_upload.json()["ingested_records"] == 2

    massbank_bytes = (data_dir / "sample_massbank_export.csv").read_bytes()
    massbank_upload = client.post(
        "/api/v1/ingest/adduct-bank/upload-massbank",
        data={"source_name": "massbank_uploaded"},
        files={"file": ("sample_massbank_export.csv", BytesIO(massbank_bytes), "text/csv")},
    )
    assert massbank_upload.status_code == 200
    assert massbank_upload.json()["ingested_records"] == 3

    metlin_bytes = (data_dir / "sample_metlin_export.csv").read_bytes()
    metlin_upload = client.post(
        "/api/v1/ingest/adduct-bank/upload-metlin",
        data={"source_name": "metlin_uploaded"},
        files={"file": ("sample_metlin_export.csv", BytesIO(metlin_bytes), "text/csv")},
    )
    assert metlin_upload.status_code == 200
    assert metlin_upload.json()["ingested_records"] == 2

    transition_bytes = (data_dir / "sample_mrm_nl.csv").read_bytes()
    analyze_upload = client.post(
        "/api/v1/analyze/mrm-nl/upload-csv",
        data={
            "sample_id": "UPLOAD_S1",
            "tolerance_ppm": "15.0",
            "neutral_loss_tolerance_da": "0.2",
            "rt_tolerance_min": "0.3",
            "isotope_tolerance": "0.08",
            "top_k_per_transition": "3",
        },
        files={"file": ("sample_mrm_nl.csv", BytesIO(transition_bytes), "text/csv")},
    )
    assert analyze_upload.status_code == 200
    analyzed = analyze_upload.json()
    assert analyzed["sample_id"] == "UPLOAD_S1"
    assert analyzed["transitions_analyzed"] == 3
    assert analyzed["metadata"]["parameters"]["scoring_version"] == SCORING_VERSION
    assert analyzed["metadata"]["parameters"]["rt_tolerance_min"] == 0.3


def test_tool_upload_analysis_endpoint() -> None:
    client = TestClient(app)
    data_dir = Path(__file__).resolve().parents[1] / "data"

    ingest_resp = client.post(
        "/api/v1/ingest/adduct-bank/csv",
        json={
            "file_path": str(data_dir / "sample_adduct_bank.csv"),
            "source_name": "tool_analysis_bank",
        },
    )
    assert ingest_resp.status_code == 200

    msdial_bytes = (data_dir / "sample_msdial_export.csv").read_bytes()
    response = client.post(
        "/api/v1/analyze/tool/upload-csv",
        data={"tool": "msdial", "sample_id": "TOOL_S1"},
        files={"file": ("sample_msdial_export.csv", BytesIO(msdial_bytes), "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_id"] == "TOOL_S1"
    assert payload["transitions_analyzed"] >= 1
    assert payload["metadata"]["parameters"]["scoring_version"] == SCORING_VERSION
    assert payload["candidates"][0]["confidence_level"] in {"Level 2A", "Level 2B", "Level 3", "Level 4"}


def test_tool_file_path_analysis_endpoint() -> None:
    client = TestClient(app)
    data_dir = Path(__file__).resolve().parents[1] / "data"

    ingest_resp = client.post(
        "/api/v1/ingest/adduct-bank/csv",
        json={
            "file_path": str(data_dir / "sample_adduct_bank.csv"),
            "source_name": "tool_file_bank",
        },
    )
    assert ingest_resp.status_code == 200

    response = client.post(
        "/api/v1/analyze/tool-csv",
        json={
            "tool": "skyline",
            "file_path": str(data_dir / "sample_skyline_export.csv"),
            "sample_id": "TOOL_PATH_S1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_id"] == "TOOL_PATH_S1"
    assert payload["transitions_analyzed"] == 2


def test_r_module_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/stats/r-module/health")
    assert response.status_code == 200
    payload = response.json()
    assert "rscript_available" in payload
    assert "script_exists" in payload


def test_r_statistics_endpoint_returns_payload_path() -> None:
    client = TestClient(app)
    request_payload = {
        "sample_id": "R_S1",
        "candidates": [
            {
                "adduct_id": "AD001",
                "adduct_name": "8-oxo-dG",
                "source_name": "test",
                "pathway": "Oxidative DNA Damage",
                "ppm_error": 1.2,
                "nl_error": 0.01,
                "rt_error": 0.02,
                "isotope_error": 0.01,
                "confidence_score": 0.91,
                "confidence_level": "Level 2A",
                "evidence_count": 5,
                "component_scores": {"precursor_mz": 0.99},
                "matched_by": ["precursor_mz", "product_mz", "neutral_loss", "retention_time", "isotope_ratio"],
            }
        ],
        "pathway_scores": [
            {
                "pathway": "Oxidative DNA Damage",
                "hits": 1,
                "population_size": 2,
                "enrichment_score": 1.23,
                "p_value": 0.05,
            }
        ],
        "report_title": "Test R Report",
    }
    response = client.post("/api/v1/stats/r-report", json=request_payload)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"completed", "skipped", "failed"}
    assert payload["output_path"] is not None
