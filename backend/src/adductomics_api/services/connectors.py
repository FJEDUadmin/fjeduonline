from __future__ import annotations

import csv
from pathlib import Path
from typing import Protocol

from adductomics_api.schemas import AdductRecord

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
      - product_mz, neutral_loss, formula, smiles, pathway, evidence_level
    """

    def __init__(self, file_path: str, source_name: str) -> None:
        self.file_path = file_path
        self.source_name = source_name

    def load_records(self) -> list[AdductRecord]:
        csv_path = Path(self.file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Adduct CSV not found: {self.file_path}")

        records: list[AdductRecord] = []
        with csv_path.open("r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                rec = AdductRecord(
                    adduct_id=row["adduct_id"],
                    source_name=self.source_name,
                    adduct_name=row["adduct_name"],
                    precursor_mz=float(row["precursor_mz"]),
                    product_mz=float(row["product_mz"]) if row.get("product_mz") else None,
                    neutral_loss=float(row["neutral_loss"]) if row.get("neutral_loss") else None,
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

    Expected column aliases:
      - id: accession | hmdb_id
      - name: name | metabolite_name
      - mass: monoisotopic_molecular_weight | exact_mass | monoisotopic_mass
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
    def _get_first(row: dict[str, str], keys: list[str]) -> str | None:
        for key in keys:
            value = row.get(key)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
        return None

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
        with csv_path.open("r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for idx, row in enumerate(reader, start=1):
                hmdb_id = self._get_first(row, ["accession", "hmdb_id"]) or f"HMDB_AUTO_{idx}"
                name = self._get_first(row, ["name", "metabolite_name"])
                if name is None:
                    raise KeyError("name")

                raw_mass = self._get_first(
                    row, ["monoisotopic_molecular_weight", "exact_mass", "monoisotopic_mass"]
                )
                if raw_mass is None:
                    raise KeyError("monoisotopic_molecular_weight")

                neutral_mass = float(raw_mass)
                precursor_mz = neutral_mass if self.ion_mode == "neutral" else neutral_mass + PROTON_MASS

                records.append(
                    AdductRecord(
                        adduct_id=hmdb_id,
                        source_name=self.source_name,
                        adduct_name=name,
                        precursor_mz=precursor_mz,
                        product_mz=None,
                        neutral_loss=None,
                        formula=self._get_first(row, ["chemical_formula", "formula"]),
                        smiles=self._get_first(row, ["smiles"]),
                        pathway=self._normalize_pathway(
                            self._get_first(row, ["pathways", "pathway", "kegg_pathway"])
                        ),
                        evidence_level="predicted",
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
