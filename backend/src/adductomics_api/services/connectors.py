from __future__ import annotations

from pathlib import Path
from typing import Protocol

from adductomics_api.schemas import AdductRecord
from adductomics_api.services.csv_utils import get_first, prepare_row, read_csv_rows_with_fallback

PROTON_MASS = 1.007276466812


class AdductBankConnector(Protocol):
    def load_records(self) -> list[AdductRecord]:
        """Load and normalize records from one adduct data source."""


class CsvAdductConnector:
    """
    Generic CSV connector.

    Required columns:
      - adduct_id
      - adduct_name
      - precursor_mz
    Optional columns:
      - product_mz, neutral_loss, expected_rt, isotope_ratio, formula, smiles, pathway, evidence_level
    """

    def __init__(self, file_path: str, source_name: str) -> None:
        self.file_path = file_path
        self.source_name = source_name

    def load_records(self) -> list[AdductRecord]:
        csv_path = Path(self.file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Adduct CSV not found: {self.file_path}")

        records: list[AdductRecord] = []
        for row in read_csv_rows_with_fallback(csv_path):
            rec = AdductRecord(
                adduct_id=row["adduct_id"],
                source_name=self.source_name,
                adduct_name=row["adduct_name"],
                precursor_mz=float(row["precursor_mz"]),
                product_mz=float(row["product_mz"]) if row.get("product_mz") else None,
                neutral_loss=float(row["neutral_loss"]) if row.get("neutral_loss") else None,
                expected_rt=float(row["expected_rt"]) if row.get("expected_rt") else None,
                isotope_ratio=float(row["isotope_ratio"]) if row.get("isotope_ratio") else None,
                formula=row.get("formula") or None,
                smiles=row.get("smiles") or None,
                pathway=row.get("pathway") or None,
                evidence_level=row.get("evidence_level") or "reported",
            )
            records.append(rec)
        return records


class HmdbCsvConnector:
    """
    HMDB export connector (CSV).

    Headers are matched case-insensitively and allow separators like space/hyphen/dot.

    Expected column aliases:
      - id: accession | hmdb_id | accession_id
      - name: name | metabolite_name | common_name | chemical_name | compound_name
      - mass: monoisotopic_molecular_weight | exact_mass | monoisotopic_mass | molecular_weight
      - formula: chemical_formula (optional)
      - smiles: smiles (optional)
      - pathway: pathways | pathway | kegg_pathway (optional)
    """

    def __init__(self, file_path: str, source_name: str, ion_mode: str = "protonated") -> None:
        self.file_path = file_path
        self.source_name = source_name
        if ion_mode not in {"neutral", "protonated"}:
            raise ValueError("ion_mode must be 'neutral' or 'protonated'")
        self.ion_mode = ion_mode

    @staticmethod
    def _normalize_pathway(raw: str | None) -> str | None:
        if raw is None:
            return None
        for sep in [";", "|", ","]:
            if sep in raw:
                token = raw.split(sep)[0].strip()
                return token or None
        return raw.strip() or None

    def load_records(self) -> list[AdductRecord]:
        csv_path = Path(self.file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"HMDB CSV not found: {self.file_path}")

        records: list[AdductRecord] = []
        for idx, row in enumerate(read_csv_rows_with_fallback(csv_path), start=1):
            prepared_row = prepare_row(row)
            hmdb_id = get_first(prepared_row, ["accession", "hmdb_id", "accession_id"]) or f"HMDB_AUTO_{idx}"
            name = get_first(
                prepared_row,
                [
                    "name",
                    "metabolite_name",
                    "common_name",
                    "chemical_name",
                    "compound_name",
                    "iupac_name",
                ],
            )
            if name is None:
                raise KeyError("name")

            raw_mass = get_first(
                prepared_row,
                [
                    "monoisotopic_molecular_weight",
                    "exact_mass",
                    "monoisotopic_mass",
                    "molecular_weight",
                    "neutral_mass",
                ],
            )
            if raw_mass is None:
                raise KeyError("monoisotopic_molecular_weight")

            neutral_mass = float(raw_mass)
            precursor_mz = neutral_mass if self.ion_mode == "neutral" else neutral_mass + PROTON_MASS
            hmdb_isotope = get_first(
                prepared_row, ["isotope_ratio", "isotope_pattern_ratio", "isotope"]
            )
            hmdb_rt = get_first(prepared_row, ["retention_time", "rt"])

            records.append(
                AdductRecord(
                    adduct_id=hmdb_id,
                    source_name=self.source_name,
                    adduct_name=name,
                    precursor_mz=precursor_mz,
                    product_mz=None,
                    neutral_loss=None,
                    expected_rt=float(hmdb_rt) if hmdb_rt is not None else None,
                    isotope_ratio=float(hmdb_isotope) if hmdb_isotope is not None else None,
                    formula=get_first(prepared_row, ["chemical_formula", "formula", "molecular_formula"]),
                    smiles=get_first(prepared_row, ["smiles", "smiles_string"]),
                    pathway=self._normalize_pathway(
                        get_first(
                            prepared_row,
                            ["pathways", "pathway", "kegg_pathway", "smpdb_pathway", "biocyc_pathway"],
                        )
                    ),
                    evidence_level="predicted",
                )
            )
        return records


class MassBankCsvConnector:
    """
    MassBank export connector (CSV).

    Headers are matched case-insensitively and allow separators like space/hyphen/dot.

    Expected column aliases:
      - id: accession | record_id | mb_id
      - name: compound_name | name
      - precursor_mz: precursor_mz | mz | exact_mass
      - product_mz: product_mz | fragment_mz (optional)
      - pathway: pathway | pathways | class (optional)
      - expected_rt: retention_time | rt (optional)
      - isotope_ratio: isotope_ratio (optional)
      - formula: formula | molecular_formula (optional)
      - smiles: smiles (optional)
    """

    def __init__(self, file_path: str, source_name: str) -> None:
        self.file_path = file_path
        self.source_name = source_name

    @staticmethod
    def _normalize_pathway(raw: str | None) -> str | None:
        if raw is None:
            return None
        for sep in [";", "|", ","]:
            if sep in raw:
                token = raw.split(sep)[0].strip()
                return token or None
        return raw.strip() or None

    def load_records(self) -> list[AdductRecord]:
        csv_path = Path(self.file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"MassBank CSV not found: {self.file_path}")

        records: list[AdductRecord] = []
        for idx, row in enumerate(read_csv_rows_with_fallback(csv_path), start=1):
            prepared_row = prepare_row(row)
            massbank_id = (
                get_first(prepared_row, ["accession", "record_id", "mb_id", "massbank_id"])
                or f"MB_AUTO_{idx}"
            )
            name = get_first(prepared_row, ["compound_name", "name", "chemical_name", "common_name"])
            if name is None:
                raise KeyError("compound_name")

            raw_precursor_mz = get_first(prepared_row, ["precursor_mz", "mz", "exact_mass", "mass"])
            if raw_precursor_mz is None:
                raise KeyError("precursor_mz")

            precursor_mz = float(raw_precursor_mz)
            raw_product_mz = get_first(prepared_row, ["product_mz", "fragment_mz"])
            product_mz = float(raw_product_mz) if raw_product_mz else None
            neutral_loss = precursor_mz - product_mz if product_mz else None
            raw_rt = get_first(prepared_row, ["retention_time", "rt"])
            raw_isotope = get_first(prepared_row, ["isotope_ratio", "isotope_pattern_ratio", "isotope"])

            records.append(
                AdductRecord(
                    adduct_id=massbank_id,
                    source_name=self.source_name,
                    adduct_name=name,
                    precursor_mz=precursor_mz,
                    product_mz=product_mz,
                    neutral_loss=neutral_loss if neutral_loss and neutral_loss > 0 else None,
                    expected_rt=(float(raw_rt) if raw_rt else None),
                    isotope_ratio=(float(raw_isotope) if raw_isotope else None),
                    formula=get_first(prepared_row, ["formula", "molecular_formula"]),
                    smiles=get_first(prepared_row, ["smiles", "smiles_string"]),
                    pathway=self._normalize_pathway(
                        get_first(prepared_row, ["pathway", "pathways", "class", "kegg_pathway"])
                    ),
                    evidence_level="reported",
                )
            )
        return records


class ConnectorRegistry:
    """Simple registry to keep each data-bank adapter pluggable."""

    def __init__(self) -> None:
        self._connectors: dict[str, AdductBankConnector] = {}

    def register(self, name: str, connector: AdductBankConnector) -> None:
        self._connectors[name] = connector

    def load(self, name: str) -> list[AdductRecord]:
        if name not in self._connectors:
            raise KeyError(f"Connector '{name}' is not registered")
        return self._connectors[name].load_records()
