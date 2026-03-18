from pathlib import Path

from adductomics_api.repository import AdductRepository
from adductomics_api.services.connectors import PROTON_MASS
from adductomics_api.services.identifier import SCORING_VERSION
from adductomics_api.services.pipeline import AnalysisPipeline


def test_pipeline_ingest_and_analyze(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    adduct_csv = Path(__file__).resolve().parents[1] / "data" / "sample_adduct_bank.csv"
    inserted = pipeline.ingest_adduct_csv(str(adduct_csv), source_name="sample_bank")
    assert inserted == 5

    transitions = pipeline.parse_transition_csv(
        str(Path(__file__).resolve().parents[1] / "data" / "sample_mrm_nl.csv"), sample_id="S1"
    )
    result = pipeline.analyze_transitions(
        transitions=transitions,
        tolerance_ppm=15.0,
        neutral_loss_tolerance_da=0.2,
        rt_tolerance_min=0.3,
        isotope_tolerance=0.08,
        top_k_per_transition=3,
    )

    assert result.sample_id == "S1"
    assert result.transitions_analyzed == 3
    assert len(result.candidates) >= 3
    assert result.candidates[0].confidence_score >= result.candidates[-1].confidence_score
    assert any(item.pathway == "Oxidative DNA Damage" for item in result.pathway_scores)
    assert result.metadata.parameters.scoring_version == SCORING_VERSION
    assert result.metadata.parameters.rt_tolerance_min == 0.3
    assert result.metadata.parameters.isotope_tolerance == 0.08
    assert result.candidates[0].component_scores


def test_pipeline_hmdb_ingest(tmp_path: Path) -> None:
    db_path = tmp_path / "test_hmdb.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    hmdb_csv = Path(__file__).resolve().parents[1] / "data" / "sample_hmdb_export.csv"
    inserted = pipeline.ingest_hmdb_csv(
        file_path=str(hmdb_csv),
        source_name="hmdb_test",
        ion_mode="protonated",
    )
    assert inserted == 3

    adducts = repo.list_adducts(limit=10)
    assert len(adducts) == 3
    first = adducts[0]
    assert first["source_name"] == "hmdb_test"
    assert first["evidence_level"] == "predicted"
    assert first["precursor_mz"] > 100
    assert abs(first["precursor_mz"] - (149.0701 + PROTON_MASS)) < 0.01


def test_pipeline_massbank_ingest(tmp_path: Path) -> None:
    db_path = tmp_path / "test_massbank.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    massbank_csv = Path(__file__).resolve().parents[1] / "data" / "sample_massbank_export.csv"
    inserted = pipeline.ingest_massbank_csv(
        file_path=str(massbank_csv),
        source_name="massbank_test",
    )
    assert inserted == 3

    adducts = repo.list_adducts(limit=10)
    assert len(adducts) == 3
    matched = [a for a in adducts if a["adduct_id"] == "MB000001"][0]
    assert matched["expected_rt"] == 4.1
    assert matched["isotope_ratio"] == 0.24
    assert matched["neutral_loss"] > 0
