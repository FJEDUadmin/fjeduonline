from pathlib import Path

from adductomics_api.repository import AdductRepository
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
        top_k_per_transition=3,
    )

    assert result.sample_id == "S1"
    assert result.transitions_analyzed == 3
    assert len(result.candidates) >= 3
    assert result.candidates[0].confidence_score >= result.candidates[-1].confidence_score
    assert any(item.pathway == "Oxidative DNA Damage" for item in result.pathway_scores)
