from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from matplotlib.figure import Figure
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests


@dataclass
class AnalysisResult:
    name: str
    tables: dict[str, pd.DataFrame]
    figures: dict[str, Figure]
    summary: dict[str, Any]
    code: str


def apply_publication_style() -> None:
    """Apply an academic publication-ready plotting theme."""
    sns.set_theme(style="whitegrid", context="talk", palette="colorblind")
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "grid.alpha": 0.3,
            "lines.linewidth": 2,
        }
    )


def descriptive_statistics(df: pd.DataFrame, numeric_cols: list[str]) -> AnalysisResult:
    data = df[numeric_cols].copy()
    describe_df = data.describe().T
    describe_df["missing_n"] = data.isna().sum()
    describe_df["missing_pct"] = (data.isna().mean() * 100).round(2)

    normality_records: list[dict[str, Any]] = []
    for col in numeric_cols:
        series = data[col].dropna()
        if len(series) < 3:
            normality_records.append({"feature": col, "shapiro_p": np.nan, "normality": "insufficient_n"})
            continue
        sampled = series.sample(min(5000, len(series)), random_state=42)
        _, p_value = stats.shapiro(sampled)
        normality_records.append(
            {"feature": col, "shapiro_p": p_value, "normality": "normal_like" if p_value > 0.05 else "non_normal"}
        )

    normality_df = pd.DataFrame(normality_records)

    plot_cols = numeric_cols[: min(4, len(numeric_cols))]
    fig, axes = plt.subplots(len(plot_cols), 2, figsize=(12, 4 * len(plot_cols)))
    if len(plot_cols) == 1:
        axes = np.array([axes])

    for row_idx, col in enumerate(plot_cols):
        sns.histplot(data[col].dropna(), kde=True, ax=axes[row_idx, 0], color="#4C72B0")
        axes[row_idx, 0].set_title(f"Histogram + KDE: {col}")
        sns.boxplot(x=data[col], ax=axes[row_idx, 1], color="#55A868")
        axes[row_idx, 1].set_title(f"Boxplot: {col}")
    fig.tight_layout()

    code = (
        "desc = df[cols].describe().T\n"
        "desc['missing_n'] = df[cols].isna().sum()\n"
        "desc['missing_pct'] = df[cols].isna().mean() * 100\n"
        "# Optional normality test\n"
        "from scipy import stats\n"
        "for col in cols:\n"
        "    stats.shapiro(df[col].dropna().sample(min(5000, df[col].dropna().shape[0]), random_state=42))\n"
    )

    return AnalysisResult(
        name="Descriptive Statistics & Distribution Check",
        tables={"descriptive_stats": describe_df, "normality_test": normality_df},
        figures={"distribution_overview": fig},
        summary={
            "n_rows": int(df.shape[0]),
            "n_features": int(len(numeric_cols)),
            "non_normal_features": int((normality_df["normality"] == "non_normal").sum()),
        },
        code=code,
    )


def calibration_curve(
    df: pd.DataFrame, concentration_col: str, response_col: str, weighting: str = "none"
) -> AnalysisResult:
    fit_df = df[[concentration_col, response_col]].dropna().copy()
    x = fit_df[concentration_col].astype(float).values
    y = fit_df[response_col].astype(float).values

    exog = sm.add_constant(x)
    if weighting == "1/x":
        weights = 1.0 / np.clip(np.abs(x), 1e-12, None)
        model = sm.WLS(y, exog, weights=weights).fit()
    elif weighting == "1/x^2":
        weights = 1.0 / np.clip(np.abs(x) ** 2, 1e-12, None)
        model = sm.WLS(y, exog, weights=weights).fit()
    else:
        model = sm.OLS(y, exog).fit()

    intercept, slope = model.params[0], model.params[1]
    y_hat = model.predict(exog)
    sse = float(np.sum((y - y_hat) ** 2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - sse / sst if sst > 0 else np.nan

    back_calculated = (y - intercept) / slope
    re_pct = (back_calculated - x) / x * 100
    re_pct = np.where(np.isfinite(re_pct), re_pct, np.nan)

    points_df = pd.DataFrame(
        {
            "concentration": x,
            "response": y,
            "predicted_response": y_hat,
            "back_calculated_concentration": back_calculated,
            "relative_error_pct": re_pct,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.scatterplot(x=x, y=y, ax=axes[0], s=70, edgecolor="black")
    x_line = np.linspace(np.min(x), np.max(x), 200)
    y_line = intercept + slope * x_line
    axes[0].plot(x_line, y_line, color="#C44E52", label=f"Fit: y={intercept:.3g}+{slope:.3g}x")
    axes[0].set_title(f"Calibration Curve ({weighting})")
    axes[0].set_xlabel(concentration_col)
    axes[0].set_ylabel(response_col)
    axes[0].legend()

    residuals = y - y_hat
    sns.scatterplot(x=y_hat, y=residuals, ax=axes[1], s=60, edgecolor="black")
    axes[1].axhline(0, linestyle="--", color="black")
    axes[1].set_title("Residual Plot")
    axes[1].set_xlabel("Fitted Response")
    axes[1].set_ylabel("Residual")
    fig.tight_layout()

    summary = {
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r2),
        "n_points": int(len(fit_df)),
    }

    code = (
        f"x = df['{concentration_col}'].astype(float).to_numpy()\n"
        f"y = df['{response_col}'].astype(float).to_numpy()\n"
        f"X = sm.add_constant(x)\n"
        f"model = sm.OLS(y, X).fit()  # weighting='{weighting}' can be switched to WLS\n"
        "intercept, slope = model.params\n"
        "r2 = 1 - ((y - model.predict(X)) ** 2).sum() / ((y - y.mean()) ** 2).sum()\n"
    )

    return AnalysisResult(
        name="Calibration Curve",
        tables={"calibration_points": points_df, "model_coefficients": pd.DataFrame([summary])},
        figures={"calibration_and_residuals": fig},
        summary=summary,
        code=code,
    )


def lod_loq_analysis(
    df: pd.DataFrame, concentration_col: str, response_col: str, blank_response_col: str | None = None
) -> AnalysisResult:
    fit_df = df[[concentration_col, response_col]].dropna().copy()
    x = fit_df[concentration_col].astype(float).values
    y = fit_df[response_col].astype(float).values

    slope, intercept = np.polyfit(x, y, deg=1)

    if blank_response_col:
        blank_series = df[blank_response_col].dropna().astype(float)
    else:
        blank_series = fit_df.loc[np.isclose(fit_df[concentration_col].astype(float), 0.0), response_col].dropna().astype(float)
    if blank_series.empty:
        raise ValueError("Cannot estimate blank SD. Provide blank response column or rows with concentration = 0.")

    sd_blank = float(blank_series.std(ddof=1))
    lod = 3.3 * sd_blank / abs(slope)
    loq = 10 * sd_blank / abs(slope)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(x=x, y=y, ax=ax, s=70, edgecolor="black")
    x_line = np.linspace(np.min(x), max(np.max(x), loq * 1.2), 200)
    y_line = intercept + slope * x_line
    ax.plot(x_line, y_line, color="#C44E52", label="Linear fit")
    ax.axvline(lod, color="#4C72B0", linestyle="--", label=f"LOD={lod:.3g}")
    ax.axvline(loq, color="#55A868", linestyle="--", label=f"LOQ={loq:.3g}")
    ax.set_title("LOD / LOQ Estimation")
    ax.set_xlabel(concentration_col)
    ax.set_ylabel(response_col)
    ax.legend()
    fig.tight_layout()

    metrics = pd.DataFrame(
        [
            {
                "slope": slope,
                "intercept": intercept,
                "sd_blank": sd_blank,
                "lod": lod,
                "loq": loq,
            }
        ]
    )

    code = (
        f"slope, intercept = np.polyfit(df['{concentration_col}'], df['{response_col}'], 1)\n"
        f"sd_blank = df['{blank_response_col}'].dropna().std(ddof=1) if '{blank_response_col}' else "
        f"df[df['{concentration_col}']==0]['{response_col}'].std(ddof=1)\n"
        "lod = 3.3 * sd_blank / abs(slope)\n"
        "loq = 10 * sd_blank / abs(slope)\n"
    )

    return AnalysisResult(
        name="LOD/LOQ Estimation",
        tables={"lod_loq_metrics": metrics},
        figures={"lod_loq_plot": fig},
        summary={"lod": float(lod), "loq": float(loq), "sd_blank": float(sd_blank)},
        code=code,
    )


def precision_accuracy_analysis(
    df: pd.DataFrame, nominal_col: str, measured_col: str, qc_group_col: str | None = None
) -> AnalysisResult:
    cols = [nominal_col, measured_col]
    if qc_group_col:
        cols.append(qc_group_col)
    work = df[cols].dropna().copy()

    if qc_group_col:
        grouped = work.groupby([qc_group_col, nominal_col], dropna=False)
    else:
        grouped = work.groupby(nominal_col, dropna=False)

    out = grouped[measured_col].agg(["count", "mean", "std"]).reset_index()
    out["cv_pct"] = out["std"] / out["mean"] * 100
    out["relative_error_pct"] = (out["mean"] - out[nominal_col]) / out[nominal_col] * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.scatterplot(data=out, x=nominal_col, y="mean", ax=axes[0], s=80, edgecolor="black")
    min_val = float(out[nominal_col].min())
    max_val = float(out[nominal_col].max())
    line = np.linspace(min_val, max_val, 200)
    axes[0].plot(line, line, color="black", linestyle="--", label="Identity line")
    axes[0].set_title("Accuracy: Measured Mean vs Nominal")
    axes[0].set_ylabel("Measured mean")
    axes[0].legend()

    plot_df = out.copy()
    x_idx = np.arange(plot_df.shape[0])
    axes[1].bar(x_idx - 0.2, plot_df["cv_pct"], width=0.4, label="CV%")
    axes[1].bar(x_idx + 0.2, plot_df["relative_error_pct"], width=0.4, label="RE%")
    axes[1].axhline(15, color="#C44E52", linestyle="--", linewidth=1)
    axes[1].axhline(-15, color="#C44E52", linestyle="--", linewidth=1)
    axes[1].set_xticks(x_idx)
    axes[1].set_xticklabels([f"{v:g}" for v in plot_df[nominal_col]], rotation=45, ha="right")
    axes[1].set_title("Precision (CV%) and Accuracy (RE%)")
    axes[1].set_xlabel("Nominal concentration level")
    axes[1].legend()
    fig.tight_layout()

    summary = {
        "mean_cv_pct": float(np.nanmean(out["cv_pct"])),
        "max_cv_pct": float(np.nanmax(out["cv_pct"])),
        "mean_abs_re_pct": float(np.nanmean(np.abs(out["relative_error_pct"]))),
    }

    code = (
        f"summary = df.groupby('{nominal_col}')['{measured_col}'].agg(['count','mean','std'])\n"
        "summary['cv_pct'] = summary['std'] / summary['mean'] * 100\n"
        f"summary['relative_error_pct'] = (summary['mean'] - summary.index) / summary.index * 100\n"
    )

    return AnalysisResult(
        name="Precision & Accuracy (QC)",
        tables={"precision_accuracy_table": out},
        figures={"precision_accuracy_plot": fig},
        summary=summary,
        code=code,
    )


def matrix_effect_recovery_analysis(
    df: pd.DataFrame, level_col: str, sample_type_col: str, response_col: str
) -> AnalysisResult:
    work = df[[level_col, sample_type_col, response_col]].dropna().copy()
    work[sample_type_col] = work[sample_type_col].astype(str).str.lower().str.strip()

    grouped = work.groupby([level_col, sample_type_col])[response_col].mean().unstack()
    required = {"pre_spike", "post_spike", "neat"}
    missing = required - set(grouped.columns)
    if missing:
        raise ValueError(
            "Missing sample types for matrix/recovery analysis. "
            f"Required labels: {sorted(required)}; missing: {sorted(missing)}."
        )

    result_df = grouped.copy()
    result_df["recovery_pct"] = result_df["pre_spike"] / result_df["post_spike"] * 100
    result_df["matrix_effect_factor_pct"] = result_df["post_spike"] / result_df["neat"] * 100
    result_df["matrix_effect_suppression_pct"] = (1 - (result_df["post_spike"] / result_df["neat"])) * 100
    result_df["process_efficiency_pct"] = result_df["pre_spike"] / result_df["neat"] * 100
    result_df = result_df.reset_index()

    fig, ax = plt.subplots(figsize=(10, 6))
    melted = result_df.melt(
        id_vars=[level_col],
        value_vars=["recovery_pct", "matrix_effect_factor_pct", "process_efficiency_pct"],
        var_name="metric",
        value_name="value",
    )
    sns.barplot(data=melted, x=level_col, y="value", hue="metric", ax=ax)
    ax.axhline(100, color="black", linestyle="--", linewidth=1)
    ax.set_ylabel("%")
    ax.set_title("Recovery / Matrix Effect / Process Efficiency")
    ax.legend(title="Metric")
    fig.tight_layout()

    summary = {
        "mean_recovery_pct": float(result_df["recovery_pct"].mean()),
        "mean_matrix_effect_factor_pct": float(result_df["matrix_effect_factor_pct"].mean()),
        "mean_process_efficiency_pct": float(result_df["process_efficiency_pct"].mean()),
    }

    code = (
        f"pivot = df.groupby(['{level_col}','{sample_type_col}'])['{response_col}'].mean().unstack()\n"
        "pivot['recovery_pct'] = pivot['pre_spike'] / pivot['post_spike'] * 100\n"
        "pivot['matrix_effect_factor_pct'] = pivot['post_spike'] / pivot['neat'] * 100\n"
        "pivot['process_efficiency_pct'] = pivot['pre_spike'] / pivot['neat'] * 100\n"
    )

    return AnalysisResult(
        name="Matrix Effect / Recovery / Process Efficiency",
        tables={"matrix_recovery_metrics": result_df},
        figures={"matrix_recovery_barplot": fig},
        summary=summary,
        code=code,
    )


def two_group_univariate_analysis(
    df: pd.DataFrame, group_col: str, feature_cols: list[str], group_a: str, group_b: str
) -> AnalysisResult:
    work = df[[group_col] + feature_cols].dropna(subset=[group_col]).copy()
    work = work[work[group_col].isin([group_a, group_b])]
    if work[group_col].nunique() != 2:
        raise ValueError("Selected groups are not both present in the data.")

    records: list[dict[str, Any]] = []
    for feat in feature_cols:
        sub = work[[group_col, feat]].dropna()
        a_values = sub.loc[sub[group_col] == group_a, feat].astype(float).values
        b_values = sub.loc[sub[group_col] == group_b, feat].astype(float).values
        if len(a_values) < 2 or len(b_values) < 2:
            continue
        stat, p_value = stats.ttest_ind(a_values, b_values, equal_var=False, nan_policy="omit")
        mean_a = float(np.mean(a_values))
        mean_b = float(np.mean(b_values))
        log2_fc = float(np.log2((mean_b + 1e-12) / (mean_a + 1e-12)))
        records.append(
            {
                "feature": feat,
                "mean_group_a": mean_a,
                "mean_group_b": mean_b,
                "log2_fc_b_over_a": log2_fc,
                "t_stat": float(stat),
                "p_value": float(p_value),
            }
        )

    results = pd.DataFrame(records).sort_values("p_value")
    if results.empty:
        raise ValueError("No valid features for two-group test (need >=2 values per group).")

    _, p_adj, _, _ = multipletests(results["p_value"], method="fdr_bh")
    results["fdr_bh"] = p_adj
    results["neg_log10_fdr"] = -np.log10(np.clip(results["fdr_bh"], 1e-300, 1))
    results["significant"] = (results["fdr_bh"] < 0.05) & (np.abs(results["log2_fc_b_over_a"]) >= 1)

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.scatterplot(
        data=results,
        x="log2_fc_b_over_a",
        y="neg_log10_fdr",
        hue="significant",
        palette={True: "#C44E52", False: "#4C72B0"},
        edgecolor="black",
        s=70,
        ax=ax,
    )
    ax.axvline(1, linestyle="--", color="gray", linewidth=1)
    ax.axvline(-1, linestyle="--", color="gray", linewidth=1)
    ax.axhline(-np.log10(0.05), linestyle="--", color="gray", linewidth=1)
    ax.set_title(f"Volcano Plot: {group_b} vs {group_a}")
    ax.set_xlabel("log2 Fold Change")
    ax.set_ylabel("-log10(FDR)")
    fig.tight_layout()

    top_hits = results.nsmallest(20, "fdr_bh").copy()
    summary = {
        "n_features_tested": int(results.shape[0]),
        "n_significant_fdr_0_05": int((results["fdr_bh"] < 0.05).sum()),
        "n_significant_with_fc": int(results["significant"].sum()),
    }

    code = (
        f"for feat in feature_cols:\n"
        f"    a = df[df['{group_col}']=='{group_a}'][feat].dropna()\n"
        f"    b = df[df['{group_col}']=='{group_b}'][feat].dropna()\n"
        "    stat, p = stats.ttest_ind(a, b, equal_var=False)\n"
        "    log2_fc = np.log2((b.mean()+1e-12)/(a.mean()+1e-12))\n"
        "from statsmodels.stats.multitest import multipletests\n"
        "p_adj = multipletests(p_values, method='fdr_bh')[1]\n"
    )

    return AnalysisResult(
        name="Two-group Univariate Test (t-test + FDR + Volcano)",
        tables={"univariate_results": results, "top_hits": top_hits},
        figures={"volcano_plot": fig},
        summary=summary,
        code=code,
    )


def anova_analysis(df: pd.DataFrame, group_col: str, feature_cols: list[str]) -> AnalysisResult:
    work = df[[group_col] + feature_cols].dropna(subset=[group_col]).copy()
    groups = sorted(work[group_col].dropna().astype(str).unique())
    if len(groups) < 3:
        raise ValueError("ANOVA requires at least 3 groups.")

    records: list[dict[str, Any]] = []
    for feat in feature_cols:
        sub = work[[group_col, feat]].dropna()
        arrays = [sub.loc[sub[group_col].astype(str) == g, feat].astype(float).values for g in groups]
        arrays = [arr for arr in arrays if len(arr) >= 2]
        if len(arrays) < 3:
            continue
        stat, p_value = stats.f_oneway(*arrays)
        records.append({"feature": feat, "f_stat": float(stat), "p_value": float(p_value)})

    results = pd.DataFrame(records).sort_values("p_value")
    if results.empty:
        raise ValueError("No valid features for ANOVA (need >=2 values in >=3 groups).")

    _, p_adj, _, _ = multipletests(results["p_value"], method="fdr_bh")
    results["fdr_bh"] = p_adj
    results["neg_log10_fdr"] = -np.log10(np.clip(results["fdr_bh"], 1e-300, 1))

    top = results.nsmallest(20, "fdr_bh").sort_values("neg_log10_fdr", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.barplot(data=top, x="neg_log10_fdr", y="feature", color="#4C72B0", ax=ax)
    ax.axvline(-np.log10(0.05), linestyle="--", color="red", linewidth=1)
    ax.set_title("Top ANOVA Hits")
    ax.set_xlabel("-log10(FDR)")
    ax.set_ylabel("Feature")
    fig.tight_layout()

    summary = {
        "n_features_tested": int(results.shape[0]),
        "n_significant_fdr_0_05": int((results["fdr_bh"] < 0.05).sum()),
    }

    code = (
        f"for feat in feature_cols:\n"
        f"    arrays = [df[df['{group_col}']==g][feat].dropna() for g in df['{group_col}'].dropna().unique()]\n"
        "    stat, p = stats.f_oneway(*arrays)\n"
        "p_adj = multipletests(p_values, method='fdr_bh')[1]\n"
    )

    return AnalysisResult(
        name="One-way ANOVA (FDR)",
        tables={"anova_results": results, "top_hits": top},
        figures={"anova_top_hits": fig},
        summary=summary,
        code=code,
    )


def pca_analysis(df: pd.DataFrame, feature_cols: list[str], group_col: str | None = None) -> AnalysisResult:
    work = df[feature_cols].dropna().copy()
    if work.shape[0] < 3:
        raise ValueError("PCA requires at least 3 complete rows.")

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(work.values.astype(float))
    pca = PCA(n_components=2)
    scores = pca.fit_transform(x_scaled)

    score_df = pd.DataFrame({"PC1": scores[:, 0], "PC2": scores[:, 1]}, index=work.index)
    if group_col and group_col in df.columns:
        score_df[group_col] = df.loc[score_df.index, group_col].astype(str).values

    fig1, ax1 = plt.subplots(figsize=(8, 7))
    if group_col and group_col in score_df.columns:
        sns.scatterplot(data=score_df, x="PC1", y="PC2", hue=group_col, s=70, edgecolor="black", ax=ax1)
    else:
        sns.scatterplot(data=score_df, x="PC1", y="PC2", s=70, edgecolor="black", color="#4C72B0", ax=ax1)
    ax1.set_title("PCA Score Plot")
    ax1.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}%)")
    ax1.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}%)")
    fig1.tight_layout()

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ratios = pca.explained_variance_ratio_ * 100
    ax2.bar(["PC1", "PC2"], ratios, color=["#4C72B0", "#55A868"])
    ax2.set_ylim(0, max(ratios) * 1.2)
    ax2.set_ylabel("Explained variance (%)")
    ax2.set_title("PCA Explained Variance")
    fig2.tight_layout()

    summary = {
        "pc1_explained_variance_pct": float(ratios[0]),
        "pc2_explained_variance_pct": float(ratios[1]),
        "total_explained_variance_pct": float(np.sum(ratios)),
    }

    code = (
        "from sklearn.preprocessing import StandardScaler\n"
        "from sklearn.decomposition import PCA\n"
        "x = StandardScaler().fit_transform(df[feature_cols].dropna())\n"
        "pca = PCA(n_components=2)\n"
        "scores = pca.fit_transform(x)\n"
    )

    return AnalysisResult(
        name="Principal Component Analysis (PCA)",
        tables={"pca_scores": score_df},
        figures={"pca_scores_plot": fig1, "pca_variance_plot": fig2},
        summary=summary,
        code=code,
    )
