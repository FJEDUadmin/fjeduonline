from __future__ import annotations

import csv
import io
from pathlib import Path

CSV_ENCODING_CANDIDATES = [
    "utf-8",
    "utf-8-sig",
    "big5",
    "cp950",
    "cp1252",
    "gb18030",
    "latin-1",
]


def normalize_key(key: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in key.strip().lower())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def prepare_row(row: dict[str, str | None]) -> dict[str, str]:
    prepared: dict[str, str] = {}
    for raw_key, raw_value in row.items():
        if raw_key is None:
            continue
        normalized_key = normalize_key(str(raw_key))
        if normalized_key in prepared:
            continue
        value = "" if raw_value is None else str(raw_value).strip()
        prepared[normalized_key] = value
    return prepared


def get_first(prepared_row: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        value = prepared_row.get(normalize_key(key))
        if value:
            return value
    return None


def read_csv_rows_with_fallback(csv_path: Path) -> list[dict[str, str | None]]:
    raw = csv_path.read_bytes()
    decode_errors: list[str] = []
    for encoding in CSV_ENCODING_CANDIDATES:
        try:
            text = raw.decode(encoding)
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{encoding}: {exc}")

    raise ValueError(
        "Unable to decode CSV file with supported encodings "
        f"{CSV_ENCODING_CANDIDATES}. Decode errors: {decode_errors}"
    )
