from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

from analysis_modules import (
    AnalysisResult,
    anova_analysis,
    apply_publication_style,
    calibration_curve,
    descriptive_statistics,
    grouped_bar_error_analysis,
    lod_loq_analysis,
    matrix_effect_recovery_analysis,
    pca_analysis,
    precision_accuracy_analysis,
    two_group_univariate_analysis,
)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def make_unique_columns(columns: list[str]) -> list[str]:
    """Make duplicated column names unique while preserving order."""
    seen: dict[str, int] = {}
    unique_cols: list[str] = []
    for col in columns:
        base = str(col).strip() if str(col).strip() else "unnamed"
        if base not in seen:
            seen[base] = 0
            unique_cols.append(base)
            continue
        seen[base] += 1
        unique_cols.append(f"{base}__dup{seen[base]}")
    return unique_cols


def save_run_artifacts(
    run_dir: Path,
    uploaded_bytes: bytes,
    uploaded_name: str,
    selected_analysis_names: list[str],
    analysis_params: dict[str, dict[str, str | list[str] | None]],
    results: list[AnalysisResult],
) -> tuple[Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "tables").mkdir(exist_ok=True)
    (run_dir / "figures").mkdir(exist_ok=True)

    input_path = run_dir / f"input_{uploaded_name}"
    input_path.write_bytes(uploaded_bytes)

    metadata = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "selected_analyses": selected_analysis_names,
        "analysis_parameters": analysis_params,
        "input_file": input_path.name,
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report_lines: list[str] = [
        f"# Analysis Run Report ({run_dir.name})",
        "",
        f"- Timestamp: {metadata['timestamp']}",
        f"- Input file: `{input_path.name}`",
        f"- Selected analyses: {', '.join(selected_analysis_names)}",
        "",
        "## Analysis Results",
        "",
    ]
    code_lines: list[str] = [
        "# Auto-generated analysis code log",
        f"# run_id: {run_dir.name}",
        f"# timestamp: {metadata['timestamp']}",
        "",
    ]

    for result in results:
        analysis_slug = slugify(result.name)
        report_lines.extend([f"### {result.name}", ""])
        report_lines.append("**Summary**")
        report_lines.append("")
        for key, value in result.summary.items():
            report_lines.append(f"- {key}: {value}")
        report_lines.append("")

        if result.tables:
            report_lines.append("**Saved Tables**")
            report_lines.append("")
            for table_name, table_df in result.tables.items():
                table_file = run_dir / "tables" / f"{analysis_slug}__{slugify(table_name)}.csv"
                table_df.to_csv(table_file, index=False)
                report_lines.append(f"- `{table_file.as_posix()}`")
            report_lines.append("")

        if result.figures:
            report_lines.append("**Saved Figures**")
            report_lines.append("")
            for fig_name, fig_obj in result.figures.items():
                figure_file = run_dir / "figures" / f"{analysis_slug}__{slugify(fig_name)}.png"
                fig_obj.savefig(figure_file, dpi=300, bbox_inches="tight")
                report_lines.append(f"- `{figure_file.as_posix()}`")
            report_lines.append("")

        report_lines.append("**Executed Code Snippet**")
        report_lines.append("")
        report_lines.append("```python")
        report_lines.extend(result.code.splitlines())
        report_lines.append("```")
        report_lines.append("")

        code_lines.append(f"# ---- {result.name} ----")
        code_lines.extend(result.code.splitlines())
        code_lines.append("")

    report_path = run_dir / "run_report.md"
    code_path = run_dir / "run_code.py"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    code_path.write_text("\n".join(code_lines), encoding="utf-8")

    return report_path, code_path


def safe_run(
    analysis_name: str,
    func: Callable[..., AnalysisResult],
    kwargs: dict,
    results: list[AnalysisResult],
    errors: list[str],
) -> None:
    try:
        results.append(func(**kwargs))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{analysis_name}: {exc}")


def main() -> None:
    st.set_page_config(page_title="MS 統計分析系統", layout="wide")
    apply_publication_style()

    st.title("本機線上分析系統（質譜方法開發）")
    st.caption(
        "上傳 CSV 後，勾選你要的統計分析，即可一鍵產出學術期刊風格圖表、統計表，以及每次分析的程式碼紀錄。"
    )

    st.markdown(
        """
### 內建常用分析（質譜方法開發/代謝體）
- **Descriptive statistics + 分布檢查**
- **Calibration curve**（支援 OLS / 1/x / 1/x^2 加權）
- **LOD / LOQ**（以 SD/slope 公式估算）
- **Precision & Accuracy (QC)**
- **Matrix effect / Recovery / Process efficiency**
- **Grouped bar chart + error bars**（可做你提供的那種圖）
- **Two-group t-test + FDR + Volcano plot**
- **One-way ANOVA + FDR**
- **PCA（含 score plot 與 explained variance）**
        """
    )

    uploaded_file = st.file_uploader("上傳 CSV 檔案", type=["csv"])
    if uploaded_file is None:
        st.info("請先上傳 CSV 檔案。")
        return

    uploaded_bytes = uploaded_file.getvalue()
    if not uploaded_bytes:
        st.error("檔案是空的，請重新上傳。")
        return

    try:
        df = pd.read_csv(uploaded_file)
    except Exception:  # noqa: BLE001
        try:
            df = pd.read_csv(uploaded_file, encoding="latin-1")
        except Exception as exc:  # noqa: BLE001
            st.error(f"CSV 讀取失敗：{exc}")
            return

    if df.empty:
        st.error("CSV 沒有資料列。")
        return

    original_cols = [str(c) for c in df.columns]
    unique_cols = make_unique_columns(original_cols)
    if original_cols != unique_cols:
        rename_df = pd.DataFrame({"original_column": original_cols, "renamed_column": unique_cols})
        df.columns = unique_cols
        st.warning("偵測到重複欄名，系統已自動重新命名避免分析錯誤。")
        with st.expander("查看欄名重新命名對照表", expanded=False):
            st.dataframe(rename_df, use_container_width=True, height=220)

    st.success(f"讀取成功：{df.shape[0]} rows × {df.shape[1]} columns")
    with st.expander("資料預覽與欄位資訊", expanded=False):
        st.dataframe(df.head(20), use_container_width=True)
        info_df = pd.DataFrame(
            {"column": df.columns, "dtype": [str(t) for t in df.dtypes], "missing_n": df.isna().sum().values}
        )
        st.dataframe(info_df, use_container_width=True, height=280)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()
    object_cols = [c for c in all_cols if c not in numeric_cols]

    if "run_history" not in st.session_state:
        st.session_state.run_history = []

    st.subheader("分析勾選與參數設定")
    st.markdown("**三步驟：** 1) 上傳 CSV  2) 勾選分析  3) 按「執行已勾選分析」")
    newbie_mode = st.toggle("新手模式（只顯示常用項目）", value=True)
    if newbie_mode:
        use_desc = st.checkbox("Descriptive statistics + 分布檢查", value=True)
        use_grouped_bar = st.checkbox("指定格式圖：分組柱狀圖 + 誤差棒", value=True)
        use_me = st.checkbox("Matrix effect / Recovery", value=False)
        with st.expander("進階分析（可選）", expanded=False):
            use_calib = st.checkbox("Calibration curve", value=False)
            use_lodloq = st.checkbox("LOD / LOQ", value=False)
            use_pa = st.checkbox("Precision & Accuracy (QC)", value=False)
            use_two_group = st.checkbox("Two-group t-test + Volcano", value=False)
            use_anova = st.checkbox("ANOVA + FDR", value=False)
            use_pca = st.checkbox("PCA", value=False)
    else:
        c1, c2 = st.columns(2)
        with c1:
            use_desc = st.checkbox("Descriptive statistics + 分布檢查", value=True)
            use_grouped_bar = st.checkbox("指定格式圖：分組柱狀圖 + 誤差棒", value=False)
            use_calib = st.checkbox("Calibration curve", value=False)
            use_lodloq = st.checkbox("LOD / LOQ", value=False)
            use_pa = st.checkbox("Precision & Accuracy (QC)", value=False)
        with c2:
            use_me = st.checkbox("Matrix effect / Recovery", value=False)
            use_two_group = st.checkbox("Two-group t-test + Volcano", value=False)
            use_anova = st.checkbox("ANOVA + FDR", value=False)
            use_pca = st.checkbox("PCA", value=False)

    params: dict[str, dict[str, str | list[str] | None]] = {}

    if use_desc:
        st.markdown("#### 1) Descriptive statistics")
        if newbie_mode:
            desc_features = numeric_cols[: min(8, len(numeric_cols))]
            st.caption(f"新手模式自動選擇數值欄位：{len(desc_features)} 個")
        else:
            desc_features = st.multiselect(
                "數值欄位",
                options=numeric_cols,
                default=numeric_cols[: min(10, len(numeric_cols))],
                key="desc_features",
            )
        params["descriptive"] = {"numeric_cols": desc_features}

    if use_grouped_bar:
        st.markdown("#### 2) 指定格式圖：分組柱狀圖 + 誤差棒")
        st.caption("用途：生成你提供的那種圖（分組 bar + error bars + 參考線）")
        col1, col2, col3 = st.columns(3)
        with col1:
            gb_category_col = st.selectbox("X 軸分類欄位", options=all_cols, key="gb_category_col")
        with col2:
            gb_group_col = st.selectbox("分組欄位（圖例）", options=all_cols, key="gb_group_col")
        with col3:
            gb_value_col = st.selectbox("數值欄位（Y）", options=all_cols, key="gb_value_col")
        col4, col5, col6 = st.columns(3)
        with col4:
            gb_error_type = st.selectbox("誤差棒類型", options=["sd", "sem", "95ci", "none"], key="gb_error_type")
        with col5:
            gb_title = st.text_input("圖標題", value="Absolute Matrix Effect", key="gb_title")
        with col6:
            gb_y_label = st.text_input("Y 軸標籤", value="Absolute Matrix Factor", key="gb_ylabel")
        col7, col8 = st.columns(2)
        with col7:
            gb_use_ref = st.checkbox("加參考線", value=True, key="gb_use_ref")
        with col8:
            gb_ref = st.number_input("參考線 y 值", value=1.0, step=0.1, format="%.3f", key="gb_ref")
        params["grouped_bar_error"] = {
            "category_col": gb_category_col,
            "group_col": gb_group_col,
            "value_col": gb_value_col,
            "title": gb_title,
            "y_label": gb_y_label,
            "error_type": gb_error_type,
            "reference_line": float(gb_ref) if gb_use_ref else None,
        }

    if use_calib:
        st.markdown("#### 3) Calibration curve")
        col1, col2, col3 = st.columns(3)
        with col1:
            cal_x = st.selectbox("Concentration column", options=all_cols, key="cal_x")
        with col2:
            cal_y = st.selectbox("Response column", options=all_cols, key="cal_y")
        with col3:
            cal_weight = st.selectbox("Weighting", options=["none", "1/x", "1/x^2"], key="cal_w")
        params["calibration"] = {"concentration_col": cal_x, "response_col": cal_y, "weighting": cal_weight}

    if use_lodloq:
        st.markdown("#### 4) LOD / LOQ")
        col1, col2, col3 = st.columns(3)
        with col1:
            lod_x = st.selectbox("Concentration column", options=all_cols, key="lod_x")
        with col2:
            lod_y = st.selectbox("Response column", options=all_cols, key="lod_y")
        with col3:
            blank_col_options = [None] + all_cols
            blank_col = st.selectbox("Blank response column (optional)", options=blank_col_options, key="lod_blank")
        params["lod_loq"] = {
            "concentration_col": lod_x,
            "response_col": lod_y,
            "blank_response_col": blank_col,
        }

    if use_pa:
        st.markdown("#### 5) Precision & Accuracy (QC)")
        col1, col2, col3 = st.columns(3)
        with col1:
            pa_nominal = st.selectbox("Nominal concentration column", options=all_cols, key="pa_nominal")
        with col2:
            pa_measured = st.selectbox("Measured concentration column", options=all_cols, key="pa_measured")
        with col3:
            pa_group_options = [None] + all_cols
            pa_group = st.selectbox("QC batch/group column (optional)", options=pa_group_options, key="pa_group")
        params["precision_accuracy"] = {
            "nominal_col": pa_nominal,
            "measured_col": pa_measured,
            "qc_group_col": pa_group,
        }

    if use_me:
        st.markdown("#### 6) Matrix effect / Recovery")
        st.caption("sample type 欄位需包含：`pre_spike`, `post_spike`, `neat`（大小寫不拘）")
        col1, col2, col3 = st.columns(3)
        with col1:
            me_level = st.selectbox("Level column", options=all_cols, key="me_level")
        with col2:
            me_type = st.selectbox("Sample type column", options=all_cols, key="me_type")
        with col3:
            me_resp = st.selectbox("Response column", options=all_cols, key="me_resp")
        params["matrix_effect"] = {
            "level_col": me_level,
            "sample_type_col": me_type,
            "response_col": me_resp,
        }

    if use_two_group:
        st.markdown("#### 7) Two-group t-test + FDR + Volcano")
        col1, col2, col3 = st.columns(3)
        with col1:
            tg_group_col = st.selectbox("Group column", options=all_cols, key="tg_group_col")
        group_values = sorted(df[tg_group_col].dropna().astype(str).unique().tolist())
        with col2:
            tg_group_a = st.selectbox("Group A", options=group_values, key="tg_group_a")
        with col3:
            tg_group_b = st.selectbox(
                "Group B",
                options=[g for g in group_values if g != tg_group_a] or group_values,
                key="tg_group_b",
            )
        tg_features = st.multiselect(
            "Feature columns",
            options=numeric_cols,
            default=numeric_cols[: min(30, len(numeric_cols))],
            key="tg_features",
        )
        params["two_group"] = {
            "group_col": tg_group_col,
            "group_a": tg_group_a,
            "group_b": tg_group_b,
            "feature_cols": tg_features,
        }

    if use_anova:
        st.markdown("#### 8) ANOVA + FDR")
        col1, col2 = st.columns(2)
        with col1:
            anova_group_col = st.selectbox("Group column", options=all_cols, key="anova_group_col")
        with col2:
            anova_features = st.multiselect(
                "Feature columns",
                options=numeric_cols,
                default=numeric_cols[: min(30, len(numeric_cols))],
                key="anova_features",
            )
        params["anova"] = {"group_col": anova_group_col, "feature_cols": anova_features}

    if use_pca:
        st.markdown("#### 9) PCA")
        col1, col2 = st.columns(2)
        with col1:
            pca_features = st.multiselect(
                "Feature columns",
                options=numeric_cols,
                default=numeric_cols[: min(20, len(numeric_cols))],
                key="pca_features",
            )
        with col2:
            pca_group_options = [None] + object_cols + numeric_cols
            pca_group = st.selectbox("Color by group (optional)", options=pca_group_options, key="pca_group")
        params["pca"] = {"feature_cols": pca_features, "group_col": pca_group}

    run_clicked = st.button("執行已勾選分析", type="primary")
    if not run_clicked:
        st.markdown("---")
        st.caption("勾選分析並按下執行，即會在本機 `analysis_runs/` 自動保存本次程式碼與輸出。")
    else:
        selected_names: list[str] = []
        results: list[AnalysisResult] = []
        errors: list[str] = []

        if use_desc:
            selected_names.append("Descriptive statistics")
            desc_features = params["descriptive"]["numeric_cols"] or []
            if not desc_features:
                errors.append("Descriptive statistics: 請至少選擇一個數值欄位。")
            else:
                safe_run(
                    "Descriptive statistics",
                    descriptive_statistics,
                    {"df": df, "numeric_cols": desc_features},
                    results,
                    errors,
                )

        if use_grouped_bar:
            selected_names.append("Grouped bar + error bars")
            gb_category = str(params["grouped_bar_error"]["category_col"])
            gb_group = str(params["grouped_bar_error"]["group_col"])
            gb_value = str(params["grouped_bar_error"]["value_col"])
            if gb_value in {gb_category, gb_group}:
                errors.append("指定格式圖：數值欄位請選擇和分類/分組不同的欄位。")
            else:
                safe_run(
                    "Grouped bar + error bars",
                    grouped_bar_error_analysis,
                    {
                        "df": df,
                        "category_col": gb_category,
                        "group_col": gb_group,
                        "value_col": gb_value,
                        "title": str(params["grouped_bar_error"]["title"]),
                        "y_label": str(params["grouped_bar_error"]["y_label"]),
                        "error_type": str(params["grouped_bar_error"]["error_type"]),
                        "reference_line": params["grouped_bar_error"]["reference_line"],
                    },
                    results,
                    errors,
                )

        if use_calib:
            selected_names.append("Calibration curve")
            safe_run(
                "Calibration curve",
                calibration_curve,
                {
                    "df": df,
                    "concentration_col": params["calibration"]["concentration_col"],
                    "response_col": params["calibration"]["response_col"],
                    "weighting": params["calibration"]["weighting"],
                },
                results,
                errors,
            )

        if use_lodloq:
            selected_names.append("LOD / LOQ")
            safe_run(
                "LOD / LOQ",
                lod_loq_analysis,
                {
                    "df": df,
                    "concentration_col": params["lod_loq"]["concentration_col"],
                    "response_col": params["lod_loq"]["response_col"],
                    "blank_response_col": params["lod_loq"]["blank_response_col"],
                },
                results,
                errors,
            )

        if use_pa:
            selected_names.append("Precision & Accuracy")
            safe_run(
                "Precision & Accuracy",
                precision_accuracy_analysis,
                {
                    "df": df,
                    "nominal_col": params["precision_accuracy"]["nominal_col"],
                    "measured_col": params["precision_accuracy"]["measured_col"],
                    "qc_group_col": params["precision_accuracy"]["qc_group_col"],
                },
                results,
                errors,
            )

        if use_me:
            selected_names.append("Matrix effect / Recovery")
            me_level = str(params["matrix_effect"]["level_col"])
            me_type = str(params["matrix_effect"]["sample_type_col"])
            me_resp = str(params["matrix_effect"]["response_col"])
            if len({me_level, me_type, me_resp}) < 3:
                errors.append("Matrix effect / Recovery: level / sample type / response 需選擇不同欄位。")
            else:
                safe_run(
                    "Matrix effect / Recovery",
                    matrix_effect_recovery_analysis,
                    {
                        "df": df,
                        "level_col": me_level,
                        "sample_type_col": me_type,
                        "response_col": me_resp,
                    },
                    results,
                    errors,
                )

        if use_two_group:
            selected_names.append("Two-group t-test + Volcano")
            tg_features = params["two_group"]["feature_cols"] or []
            if not tg_features:
                errors.append("Two-group: 請至少選擇一個 feature 欄位。")
            else:
                safe_run(
                    "Two-group t-test + Volcano",
                    two_group_univariate_analysis,
                    {
                        "df": df,
                        "group_col": params["two_group"]["group_col"],
                        "feature_cols": tg_features,
                        "group_a": str(params["two_group"]["group_a"]),
                        "group_b": str(params["two_group"]["group_b"]),
                    },
                    results,
                    errors,
                )

        if use_anova:
            selected_names.append("ANOVA + FDR")
            anova_features = params["anova"]["feature_cols"] or []
            if not anova_features:
                errors.append("ANOVA: 請至少選擇一個 feature 欄位。")
            else:
                safe_run(
                    "ANOVA + FDR",
                    anova_analysis,
                    {
                        "df": df,
                        "group_col": params["anova"]["group_col"],
                        "feature_cols": anova_features,
                    },
                    results,
                    errors,
                )

        if use_pca:
            selected_names.append("PCA")
            pca_features = params["pca"]["feature_cols"] or []
            if not pca_features:
                errors.append("PCA: 請至少選擇一個 feature 欄位。")
            else:
                safe_run(
                    "PCA",
                    pca_analysis,
                    {
                        "df": df,
                        "feature_cols": pca_features,
                        "group_col": params["pca"]["group_col"],
                    },
                    results,
                    errors,
                )

        if not selected_names:
            st.warning("尚未勾選任何分析。")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("analysis_runs") / timestamp
        report_path, code_path = save_run_artifacts(
            run_dir=run_dir,
            uploaded_bytes=uploaded_bytes,
            uploaded_name=uploaded_file.name,
            selected_analysis_names=selected_names,
            analysis_params=params,
            results=results,
        )
        st.session_state.run_history.insert(0, {"run_id": timestamp, "path": run_dir.as_posix()})

        st.markdown("---")
        st.subheader("分析結果")
        if errors:
            st.warning("部分分析未完成：")
            for msg in errors:
                st.write(f"- {msg}")
        if results:
            for result in results:
                with st.expander(result.name, expanded=True):
                    st.write("Summary")
                    st.json(result.summary)
                    for table_name, table_df in result.tables.items():
                        st.markdown(f"**Table: {table_name}**")
                        st.dataframe(table_df, use_container_width=True)
                    for fig_name, fig_obj in result.figures.items():
                        st.markdown(f"**Figure: {fig_name}**")
                        st.pyplot(fig_obj, clear_figure=False, use_container_width=True)
                    st.markdown("**Executed code snippet (auto logged)**")
                    st.code(result.code, language="python")
        else:
            st.error("沒有成功完成的分析結果，請檢查欄位選擇與資料格式。")

        st.success(f"本次分析已儲存到 `{run_dir.as_posix()}`")
        st.write(f"- 報告: `{report_path.as_posix()}`")
        st.write(f"- 程式碼紀錄: `{code_path.as_posix()}`")

    st.markdown("---")
    st.subheader("歷史執行紀錄")
    if st.session_state.run_history:
        history_df = pd.DataFrame(st.session_state.run_history)
        st.dataframe(history_df, use_container_width=True, height=220)
        st.caption("每次分析均會在本機 `analysis_runs/<timestamp>/` 產生可追蹤紀錄。")
    else:
        st.caption("目前尚無執行紀錄。")


if __name__ == "__main__":
    main()
