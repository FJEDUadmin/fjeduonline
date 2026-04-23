from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from matplotlib.figure import Figure
from openai import OpenAI
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from analysis_modules import AnalysisResult


SYSTEM_PROMPT = """
你是資深生物統計與資料視覺化工程師，擅長質譜資料分析。
你會根據使用者目標，產生可執行的 Python 程式碼。

重要規則：
1) 只針對提供的 DataFrame `df` 分析。
2) 請不要寫任何 import。
3) 程式碼執行後，必須定義以下變數：
   - analysis_summary: str（中文重點結論，含主要統計發現）
   - analysis_tables: dict[str, pandas.DataFrame]
   - analysis_figures: dict[str, matplotlib.figure.Figure]
   - analysis_warnings: list[str]（可為空）
4) 圖表要有期刊風格：標題、軸標籤、圖例清楚。
5) 若資料不足，請在 analysis_warnings 說明，不要直接崩潰。
6) 回覆格式必須為：
   - 先一小段中文說明（3~6行）
   - 接著只放一個 ```python ... ``` 程式碼區塊
""".strip()


SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "Exception": Exception,
    "ValueError": ValueError,
    "RuntimeError": RuntimeError,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
}


@dataclass
class PromptAnalysisOutput:
    result: AnalysisResult
    model_message: str
    generated_code: str


def _df_profile(df: pd.DataFrame, max_cols: int = 80, max_rows: int = 8) -> dict[str, Any]:
    cols = []
    for col in df.columns[:max_cols]:
        series = df[col]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        cols.append(
            {
                "name": str(col),
                "dtype": str(series.dtype),
                "missing_n": int(series.isna().sum()),
                "n_unique": int(series.nunique(dropna=True)),
            }
        )

    preview = df.head(max_rows).copy()
    preview = preview.replace({np.nan: None})
    return {
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "columns": cols,
        "preview_rows": preview.to_dict(orient="records"),
    }


def _extract_python_block(text: str) -> str:
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("模型回覆中找不到 ```python``` 程式碼區塊。")
    return match.group(1).strip()


def _normalize_tables(raw_tables: Any) -> dict[str, pd.DataFrame]:
    if not isinstance(raw_tables, dict):
        return {}

    normalized: dict[str, pd.DataFrame] = {}
    for key, value in raw_tables.items():
        table_name = str(key)
        if isinstance(value, pd.DataFrame):
            normalized[table_name] = value
        elif isinstance(value, pd.Series):
            normalized[table_name] = value.to_frame()
        else:
            try:
                normalized[table_name] = pd.DataFrame(value)
            except Exception:  # noqa: BLE001
                continue
    return normalized


def _normalize_figures(raw_figures: Any) -> dict[str, Figure]:
    if not isinstance(raw_figures, dict):
        return {}

    normalized: dict[str, Figure] = {}
    for key, value in raw_figures.items():
        if isinstance(value, Figure):
            normalized[str(key)] = value
    return normalized


def _execute_generated_code(df: pd.DataFrame, code: str) -> tuple[str, dict[str, pd.DataFrame], dict[str, Figure], list[str]]:
    exec_globals: dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "stats": stats,
        "sm": sm,
        "sns": sns,
        "plt": plt,
        "PCA": PCA,
        "StandardScaler": StandardScaler,
    }
    exec_locals: dict[str, Any] = {}
    exec(code, exec_globals, exec_locals)  # noqa: S102

    scope: dict[str, Any] = {}
    scope.update(exec_globals)
    scope.update(exec_locals)

    summary = scope.get("analysis_summary", "")
    if not isinstance(summary, str):
        summary = str(summary)
    if not summary.strip():
        summary = "模型未提供摘要，請檢查提示詞與資料欄位設定。"

    tables = _normalize_tables(scope.get("analysis_tables", {}))
    figures = _normalize_figures(scope.get("analysis_figures", {}))

    warnings_raw = scope.get("analysis_warnings", [])
    if isinstance(warnings_raw, list):
        warnings_out = [str(w) for w in warnings_raw]
    else:
        warnings_out = [str(warnings_raw)] if warnings_raw else []

    # If model forgot to return figures, fallback to currently open figures.
    if not figures and plt.get_fignums():
        for idx, fig_num in enumerate(plt.get_fignums(), start=1):
            figures[f"figure_{idx}"] = plt.figure(fig_num)

    return summary, tables, figures, warnings_out


def run_prompt_analysis(
    df: pd.DataFrame,
    user_goal: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> PromptAnalysisOutput:
    if not user_goal.strip():
        raise ValueError("請輸入你的分析目標提示詞。")
    if not api_key.strip():
        raise ValueError("請提供 API Key（可在側欄輸入或設環境變數 OPENAI_API_KEY）。")

    client_kwargs: dict[str, Any] = {"api_key": api_key.strip()}
    if base_url and base_url.strip():
        client_kwargs["base_url"] = base_url.strip()
    client = OpenAI(**client_kwargs)

    payload = {
        "user_goal": user_goal,
        "data_profile": _df_profile(df),
    }
    user_message = (
        "請根據以下 JSON 產生分析：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    completion = client.chat.completions.create(
        model=model.strip(),
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    message = completion.choices[0].message.content or ""
    code = _extract_python_block(message)

    summary, tables, figures, warnings_out = _execute_generated_code(df=df, code=code)
    result = AnalysisResult(
        name="AI Prompt-driven Statistical Analysis",
        tables=tables,
        figures=figures,
        summary={
            "n_rows": int(df.shape[0]),
            "n_columns": int(df.shape[1]),
            "n_tables": int(len(tables)),
            "n_figures": int(len(figures)),
            "warnings_count": int(len(warnings_out)),
            "warnings": warnings_out,
            "goal": user_goal,
        },
        code=code,
    )

    # Prefix summary into the first table area via metadata-like table for visibility in report.
    if "ai_summary" not in result.tables:
        result.tables["ai_summary"] = pd.DataFrame({"summary": [summary]})

    return PromptAnalysisOutput(
        result=result,
        model_message=message,
        generated_code=code,
    )
