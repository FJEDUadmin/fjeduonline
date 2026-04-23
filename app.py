from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

from ai_prompt_analysis import run_prompt_analysis
from analysis_modules import AnalysisResult, apply_publication_style


def slugify(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


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


def main() -> None:
    st.set_page_config(page_title="MS 統計分析系統", layout="wide")
    apply_publication_style()

    st.title("CSV + GPT 自動統計分析頁面")
    st.caption("上傳 CSV，輸入白話分析目標，系統會自動產生分析程式碼、統計表與視覺化圖片。")

    with st.sidebar:
        st.subheader("GPT 連動設定")
        default_api_key = os.getenv("OPENAI_API_KEY", "")
        api_key = st.text_input("API Key", value=default_api_key, type="password", help="可填 OpenAI 或相容服務金鑰")
        model_name = st.text_input("模型名稱", value="gpt-4o-mini", help="可改成你 GPT Pro 可用模型")
        base_url = st.text_input("Base URL（可選）", value=os.getenv("OPENAI_BASE_URL", ""))
        st.caption("如果你用 OpenAI 官方服務，可將 Base URL 留空。")

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

    if "run_history" not in st.session_state:
        st.session_state.run_history = []

    st.subheader("請用白話輸入你的分析目標")
    user_goal = st.text_area(
        "分析目標提示詞",
        height=180,
        placeholder=(
            "例如：請比較三組樣品在各 transition 的 absolute matrix effect，"
            "畫分組柱狀圖加 SD 誤差棒，並加 y=1 參考線，最後列出每組平均值。"
        ),
    )

    run_clicked = st.button("用 GPT 自動分析並產出圖表", type="primary")
    if not run_clicked:
        st.markdown("---")
        st.caption("只要上傳 CSV + 輸入目標，即可由 GPT 自動完成分析。")
    else:
        selected_names = ["AI prompt analysis"]
        results: list[AnalysisResult] = []
        errors: list[str] = []

        try:
            ai_output = run_prompt_analysis(
                df=df,
                user_goal=user_goal,
                api_key=api_key,
                model=model_name,
                base_url=base_url or None,
            )
            results.append(ai_output.result)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"AI 分析失敗：{exc}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path("analysis_runs") / timestamp
        report_path, code_path = save_run_artifacts(
            run_dir=run_dir,
            uploaded_bytes=uploaded_bytes,
            uploaded_name=uploaded_file.name,
            selected_analysis_names=selected_names,
            analysis_params={
                "ai_prompt": {
                    "goal": user_goal,
                    "model": model_name,
                    "base_url": base_url or None,
                }
            },
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
                    if "ai_summary" in result.tables:
                        ai_summary_df = result.tables["ai_summary"]
                        if "summary" in ai_summary_df.columns and not ai_summary_df.empty:
                            st.markdown("**GPT 生成的分析摘要（白話）**")
                            st.write(str(ai_summary_df.iloc[0]["summary"]))
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
