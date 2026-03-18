from __future__ import annotations

import csv
from pathlib import Path
from typing import Protocol

from adductomics_api.schemas import AdductRecord


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
