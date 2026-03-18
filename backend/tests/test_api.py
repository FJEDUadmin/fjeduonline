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

    massbank_bytes = (data_dir / "sample_massbank_export.csv").read_bytes()
    massbank_upload = client.post(
        "/api/v1/ingest/adduct-bank/upload-massbank",
        data={"source_name": "massbank_uploaded"},
        files={"file": ("sample_massbank_export.csv", BytesIO(massbank_bytes), "text/csv")},
    )
    assert massbank_upload.status_code == 200
    assert massbank_upload.json()["ingested_records"] == 3

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
