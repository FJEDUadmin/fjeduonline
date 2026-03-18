from pathlib import Path

from fastapi.testclient import TestClient

from adductomics_api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


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
