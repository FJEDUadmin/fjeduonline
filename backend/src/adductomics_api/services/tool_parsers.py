from __future__ import annotations

from pathlib import Path
from typing import Literal

from adductomics_api.schemas import MRMTransition
from adductomics_api.services.csv_utils import get_first, prepare_row, read_csv_rows_with_fallback

ToolParserType = Literal["msdial", "mzmine", "skyline"]


def _to_transition(
    row: dict[str, str],
    sample_id: str,
    idx: int,
    transition_id_keys: list[str],
    precursor_keys: list[str],
    product_keys: list[str],
    nl_keys: list[str],
    rt_keys: list[str],
    isotope_keys: list[str],
    intensity_keys: list[str],
) -> MRMTransition:
    transition_id = get_first(row, transition_id_keys) or f"{sample_id}_T{idx}"
    precursor_raw = get_first(row, precursor_keys)
    if precursor_raw is None:
        raise KeyError("precursor_mz")
    precursor_mz = float(precursor_raw)

    product_raw = get_first(row, product_keys)
    nl_raw = get_first(row, nl_keys)
    if product_raw is not None:
        product_mz = float(product_raw)
    elif nl_raw is not None:
        product_mz = precursor_mz - float(nl_raw)
    else:
        # Fallback for feature-table tools without explicit product ions.
        product_mz = precursor_mz

    if product_mz <= 0:
        raise ValueError(f"Invalid product_mz <= 0 for transition '{transition_id}'")

    neutral_loss = float(nl_raw) if nl_raw is not None else (precursor_mz - product_mz if precursor_mz > product_mz else None)
    rt_raw = get_first(row, rt_keys)
    isotope_raw = get_first(row, isotope_keys)
    intensity_raw = get_first(row, intensity_keys)

    return MRMTransition(
        transition_id=transition_id,
        sample_id=sample_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        neutral_loss=neutral_loss if neutral_loss and neutral_loss > 0 else None,
        retention_time=float(rt_raw) if rt_raw else None,
        isotope_ratio=float(isotope_raw) if isotope_raw else None,
        intensity=float(intensity_raw) if intensity_raw else None,
    )


def parse_msdial_csv(file_path: str, sample_id: str) -> list[MRMTransition]:
    csv_path = Path(file_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"MS-DIAL CSV not found: {file_path}")

    transitions: list[MRMTransition] = []
    for idx, raw_row in enumerate(read_csv_rows_with_fallback(csv_path), start=1):
        row = prepare_row(raw_row)
        transitions.append(
            _to_transition(
                row=row,
                sample_id=sample_id,
                idx=idx,
                transition_id_keys=["id", "alignment_id", "peak_id", "name"],
                precursor_keys=[
                    "precursor_m_z",
                    "precursor_mz",
                    "average_m_z",
                    "mz",
                    "alignment_m_z",
                    "quant_mass",
                ],
                product_keys=["product_m_z", "product_mz", "fragment_m_z", "fragment_mz"],
                nl_keys=["neutral_loss", "nl"],
                rt_keys=["retention_time", "rt", "average_rt"],
                isotope_keys=["isotope_ratio", "isotope_pattern_ratio"],
                intensity_keys=["height", "area", "peak_area", "intensity"],
            )
        )
    return transitions


def parse_mzmine_csv(file_path: str, sample_id: str) -> list[MRMTransition]:
    csv_path = Path(file_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"MZmine CSV not found: {file_path}")

    transitions: list[MRMTransition] = []
    for idx, raw_row in enumerate(read_csv_rows_with_fallback(csv_path), start=1):
        row = prepare_row(raw_row)
        transitions.append(
            _to_transition(
                row=row,
                sample_id=sample_id,
                idx=idx,
                transition_id_keys=["row_id", "id", "feature_id", "name"],
                precursor_keys=["row_m_z", "mz", "precursor_mz", "average_mz"],
                product_keys=["product_m_z", "fragment_m_z"],
                nl_keys=["neutral_loss", "nl"],
                rt_keys=["row_retention_time", "retention_time", "rt"],
                isotope_keys=["isotope_ratio", "isotope_pattern_ratio"],
                intensity_keys=["height", "area", "peak_area", "intensity", "max_height"],
            )
        )
    return transitions


def parse_skyline_csv(file_path: str, sample_id: str) -> list[MRMTransition]:
    csv_path = Path(file_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Skyline CSV not found: {file_path}")

    transitions: list[MRMTransition] = []
    for idx, raw_row in enumerate(read_csv_rows_with_fallback(csv_path), start=1):
        row = prepare_row(raw_row)
        transitions.append(
            _to_transition(
                row=row,
                sample_id=sample_id,
                idx=idx,
                transition_id_keys=["transition_name", "transition_id", "molecule_name", "name"],
                precursor_keys=["precursor_mz", "precursor_m_z", "q1"],
                product_keys=["product_mz", "product_m_z", "q3"],
                nl_keys=["neutral_loss", "nl"],
                rt_keys=["retention_time", "rt", "explicit_retention_time"],
                isotope_keys=["isotope_ratio", "isotope_dotp", "dotp"],
                intensity_keys=["area", "total_area", "peak_area", "height"],
            )
        )
    return transitions


def parse_tool_csv(tool: ToolParserType, file_path: str, sample_id: str) -> list[MRMTransition]:
    if tool == "msdial":
        return parse_msdial_csv(file_path=file_path, sample_id=sample_id)
    if tool == "mzmine":
        return parse_mzmine_csv(file_path=file_path, sample_id=sample_id)
    if tool == "skyline":
        return parse_skyline_csv(file_path=file_path, sample_id=sample_id)
    raise ValueError(f"Unsupported tool parser: {tool}")
