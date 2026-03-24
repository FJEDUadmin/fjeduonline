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
    assert result.metadata.parameters.confidence_framework == "adductomics_lcms_confidence_v1"
    assert result.candidates[0].component_scores
    assert result.candidates[0].confidence_level in {"Level 2A", "Level 2B", "Level 3", "Level 4"}
    assert result.candidates[0].evidence_count >= 1


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


def test_pipeline_metlin_ingest(tmp_path: Path) -> None:
    db_path = tmp_path / "test_metlin.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    metlin_csv = Path(__file__).resolve().parents[1] / "data" / "sample_metlin_export.csv"
    inserted = pipeline.ingest_metlin_csv(
        file_path=str(metlin_csv),
        source_name="metlin_test",
    )
    assert inserted == 2

    adducts = repo.list_adducts(limit=10)
    assert len(adducts) == 2
    assert all(a["source_name"] == "metlin_test" for a in adducts)
    assert any(a["adduct_id"] == "METLIN:000001" for a in adducts)


def test_pipeline_pubchem_ingest(tmp_path: Path) -> None:
    db_path = tmp_path / "test_pubchem.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    pubchem_csv = Path(__file__).resolve().parents[1] / "data" / "sample_pubchem_export.csv"
    inserted = pipeline.ingest_pubchem_csv(
        file_path=str(pubchem_csv),
        source_name="pubchem_test",
        ion_mode="protonated",
    )
    assert inserted == 2

    adducts = repo.list_adducts(limit=10)
    assert len(adducts) == 2
    assert adducts[0]["source_name"] == "pubchem_test"
    assert any(a["adduct_id"] == "12345" for a in adducts)


def test_pipeline_literature_ingest(tmp_path: Path) -> None:
    db_path = tmp_path / "test_literature.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    literature_csv = Path(__file__).resolve().parents[1] / "data" / "sample_literature_supplement.csv"
    inserted = pipeline.ingest_literature_csv(
        file_path=str(literature_csv),
        source_name="literature_test",
    )
    assert inserted == 2

    adducts = repo.list_adducts(limit=10)
    assert len(adducts) == 2
    assert all(a["source_name"] == "literature_test" for a in adducts)


def test_pipeline_hmdb_case_insensitive_alias_ingest(tmp_path: Path) -> None:
    db_path = tmp_path / "test_hmdb_alias.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    hmdb_alias_csv = tmp_path / "hmdb_alias.csv"
    hmdb_alias_csv.write_text(
        (
            "Accession ID,Common Name,Monoisotopic Molecular Weight,Chemical Formula,Pathways,Retention Time\n"
            "HMDBX0001,Alias Compound,200.1000,C8H12N2O4,DNA Repair;Oxidative stress,3.3\n"
        ),
        encoding="utf-8",
    )

    inserted = pipeline.ingest_hmdb_csv(
        file_path=str(hmdb_alias_csv),
        source_name="hmdb_alias_test",
        ion_mode="protonated",
    )
    assert inserted == 1

    adducts = repo.list_adducts(limit=5)
    assert len(adducts) == 1
    assert adducts[0]["adduct_name"] == "Alias Compound"
    assert adducts[0]["pathway"] == "DNA Repair"
    assert abs(adducts[0]["expected_rt"] - 3.3) < 1e-6


def test_pipeline_hmdb_non_utf8_cp1252_ingest(tmp_path: Path) -> None:
    db_path = tmp_path / "test_hmdb_cp1252.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    hmdb_cp1252_csv = tmp_path / "hmdb_cp1252.csv"
    hmdb_cp1252_csv.write_bytes(
        (
            "Accession,Common Name,Monoisotopic Molecular Weight,Chemical Formula,Pathways\n"
            "HMDBX0003,Compound \xa3,210.2000,C9H10N2O4,DNA Damage Response\n"
        ).encode("cp1252")
    )

    inserted = pipeline.ingest_hmdb_csv(
        file_path=str(hmdb_cp1252_csv),
        source_name="hmdb_cp1252_test",
        ion_mode="protonated",
    )
    assert inserted == 1

    adducts = repo.list_adducts(limit=5)
    assert len(adducts) == 1
    assert "Compound" in adducts[0]["adduct_name"]


def test_pipeline_tool_parsers(tmp_path: Path) -> None:
    db_path = tmp_path / "test_tool_parsers.db"
    repo = AdductRepository(str(db_path))
    pipeline = AnalysisPipeline(repository=repo)

    adduct_csv = Path(__file__).resolve().parents[1] / "data" / "sample_adduct_bank.csv"
    pipeline.ingest_adduct_csv(str(adduct_csv), source_name="sample_bank")

    data_dir = Path(__file__).resolve().parents[1] / "data"
    for tool, fname in [
        ("msdial", "sample_msdial_export.csv"),
        ("mzmine", "sample_mzmine_export.csv"),
        ("skyline", "sample_skyline_export.csv"),
    ]:
        transitions = pipeline.parse_tool_export_csv(
            tool=tool,  # type: ignore[arg-type]
            file_path=str(data_dir / fname),
            sample_id=f"{tool}_S1",
        )
        assert len(transitions) >= 2
