from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from adductomics_api.schemas import AdductRecord


class AdductRepository:
    """SQLite-based repository for adduct records and lookups."""

    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def _conn(self) -> Iterable[sqlite3.Connection]:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS adducts (
                    adduct_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    adduct_name TEXT NOT NULL,
                    precursor_mz REAL NOT NULL,
                    product_mz REAL,
                    neutral_loss REAL,
                    formula TEXT,
                    smiles TEXT,
                    pathway TEXT,
                    evidence_level TEXT NOT NULL,
                    PRIMARY KEY (adduct_id, source_name)
                )
                """
            )

    def upsert_adducts(self, records: list[AdductRecord]) -> int:
        if not records:
            return 0
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT INTO adducts (
                    adduct_id, source_name, adduct_name, precursor_mz, product_mz, neutral_loss,
                    formula, smiles, pathway, evidence_level
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(adduct_id, source_name) DO UPDATE SET
                    adduct_name=excluded.adduct_name,
                    precursor_mz=excluded.precursor_mz,
                    product_mz=excluded.product_mz,
                    neutral_loss=excluded.neutral_loss,
                    formula=excluded.formula,
                    smiles=excluded.smiles,
                    pathway=excluded.pathway,
                    evidence_level=excluded.evidence_level
                """,
                [
                    (
                        rec.adduct_id,
                        rec.source_name,
                        rec.adduct_name,
                        rec.precursor_mz,
                        rec.product_mz,
                        rec.neutral_loss,
                        rec.formula,
                        rec.smiles,
                        rec.pathway,
                        rec.evidence_level,
                    )
                    for rec in records
                ],
            )
        return len(records)

    def list_adducts(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT adduct_id, source_name, adduct_name, precursor_mz, product_mz,
                       neutral_loss, formula, smiles, pathway, evidence_level
                FROM adducts
                ORDER BY adduct_name
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_by_precursor_window(self, precursor_mz: float, tolerance_ppm: float) -> list[dict]:
        mz_tol = (precursor_mz * tolerance_ppm) / 1_000_000
        low, high = precursor_mz - mz_tol, precursor_mz + mz_tol
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT adduct_id, source_name, adduct_name, precursor_mz, product_mz,
                       neutral_loss, formula, smiles, pathway, evidence_level
                FROM adducts
                WHERE precursor_mz BETWEEN ? AND ?
                """,
                (low, high),
            ).fetchall()
        return [dict(row) for row in rows]

    def pathway_population(self) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT pathway, COUNT(*) AS cnt
                FROM adducts
                WHERE pathway IS NOT NULL AND pathway != ''
                GROUP BY pathway
                """
            ).fetchall()
        return {row["pathway"]: row["cnt"] for row in rows}

    def total_adduct_count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM adducts").fetchone()
        return int(row["cnt"])
