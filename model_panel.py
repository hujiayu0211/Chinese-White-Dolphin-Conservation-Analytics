import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import patsy
from statsmodels.discrete.discrete_model import NegativeBinomial

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"figure.dpi": 150, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})
PALETTE = {"NEL": "#C44E52", "NWL": "#4C72B0", "WL": "#55A868", "SWL": "#DD8452"}
CORE = ["NEL", "NWL", "WL", "SWL"]


def load(path):
    df = pd.read_csv(path)
    df = df[df["area_code"].isin(CORE)].copy()
    df = df[df["survey_effort_km"] > 0].copy()
    df["year_c"] = df["monitoring_start_year"] - df["monitoring_start_year"].min()
    df["log_effort"] = np.log(df["survey_effort_km"])
    df["area_code"] = pd.Categorical(df["area_code"], categories=CORE)
    return df


def overdispersion(df):
    pois = smf.glm("on_effort_sightings ~ C(area_code) + year_c + any_reclamation",
                   data=df, family=sm.families.Poisson(),
                   offset=df["log_effort"]).fit()
    pearson = pois.pearson_chi2 / pois.df_resid
    return pois, pearson


def nb_glm(df, formula):
    y, X = patsy.dmatrices("on_effort_sightings ~ " + formula, df, return_type="dataframe")
    mod = NegativeBinomial(y, X, offset=df["log_effort"].values)
    res = mod.fit(disp=0, maxiter=200)
    return res, X


def irr_table(res, X):
    params = res.params.drop(labels=[c for c in res.params.index if c == "alpha"], errors="ignore")
    ci = res.conf_int().loc[params.index]
    out = pd.DataFrame({
        "coef": params,
        "IRR": np.exp(params),
        "IRR_lo": np.exp(ci[0]),
        "IRR_hi": np.exp(ci[1]),
        "p": res.pvalues.loc[params.index],
    })
    return out.round(4)


def fig_encounter(df, out):
    fig, ax = plt.subplots(figsize=(10, 6))
    for area in CORE:
        g = df[df.area_code == area].sort_values("monitoring_start_year")
        ax.plot(g["monitoring_start_year"], g["encounter_rate_per_100_km"],
                marker="o", label=area, color=PALETTE[area], linewidth=2)
    ax.set_title("On-effort encounter rate falls; NE Lantau collapses to zero")
    ax.set_xlabel("Monitoring period (start year)")
    ax.set_ylabel("On-effort sightings per 100 km")
    ax.legend(title="Area", frameon=True)
    ax.axvspan(2016, 2020, color="grey", alpha=0.12)
    ax.text(2018, ax.get_ylim()[1] * 0.95, "3RS reclamation", ha="center", fontsize=9, color="grey")
    fig.text(0.01, 0.01, "Source: AFCD marine-mammal monitoring reports 2012-13 to 2021-22 (on-effort, effort-controlled).", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_encounter_rate_trend.png", bbox_inches="tight")
    plt.close(fig)


def fig_abundance(df, out):
    fig, ax = plt.subplots(figsize=(10, 6))
    for area in CORE:
        g = df[df.area_code == area].sort_values("monitoring_start_year")
        ax.plot(g["monitoring_start_year"], g["annual_abundance"],
                marker="s", label=area, color=PALETTE[area], linewidth=2)
    ax.set_title("Annual abundance by area, 2012-2021 (line-transect distance sampling)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Estimated abundance")
    ax.legend(title="Area", frameon=True)
    fig.text(0.01, 0.01, "Source: AFCD 2021-22 report, Table 6b. NE Lantau zeros from 2015 indicate effective local absence.", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_abundance_trend.png", bbox_inches="tight")
    plt.close(fig)


def fig_irr(irr, out):
    show = irr.drop(index=[i for i in irr.index if i == "Intercept"], errors="ignore")
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(show) + 2))
    y = np.arange(len(show))
    ax.errorbar(show["IRR"], y,
                xerr=[show["IRR"] - show["IRR_lo"], show["IRR_hi"] - show["IRR"]],
                fmt="o", color="#4C72B0", capsize=4)
    ax.axvline(1.0, color="grey", linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(show.index)
    ax.set_xlabel("Incidence rate ratio (IRR), 95% CI")
    ax.set_title("Negative Binomial GLM: incidence rate ratios")
    fig.text(0.01, 0.01, "IRR < 1 = lower sighting rate. Reference area = NEL. Effort offset applied.", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_nb_irr.png", bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="processed/cwd_master_panel.csv")
    ap.add_argument("--output-dir", default="result_figure")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = load(args.panel)
    lines = ["# CWD habitat-use model results\n",
             f"Panel: {len(df)} rows (core areas {CORE}, 10 monitoring periods). "
             "Response = on-effort sightings, offset = log(survey effort km).\n"]

    pois, pearson = overdispersion(df)
    lines.append("## Overdispersion check\n")
    lines.append(f"Poisson Pearson chi2 / df = **{pearson:.2f}** "
                 f"({'over-dispersed -> Negative Binomial justified' if pearson > 1.5 else 'mild'}).\n")

    res, X = nb_glm(df, "C(area_code) + year_c + any_reclamation")
    irr = irr_table(res, X)
    lines.append("## Negative Binomial GLM (main)\n")
    lines.append("`sightings ~ area + year + any_reclamation`, offset log(effort). "
                 f"alpha (dispersion) = {res.params.get('alpha', float('nan')):.3f}; "
                 f"pseudo R2 = {res.prsquared:.3f}.\n")
    lines.append(irr.to_markdown() + "\n")

    df["year_c2"] = df["year_c"] ** 2
    res2, _ = nb_glm(df, "C(area_code) + year_c + year_c2 + any_reclamation")
    lines.append("## Non-linearity check (quadratic year)\n")
    lines.append(f"year_c2 coef = {res2.params['year_c2']:.4f} "
                 f"(p = {res2.pvalues['year_c2']:.3f}); "
                 f"{'curvature present (decline then partial recovery)' if res2.pvalues['year_c2'] < 0.1 else 'little curvature'}.\n")

    res3, _ = nb_glm(df[df.area_code != "NEL"], "C(area_code) + year_c + any_reclamation")
    lines.append("## Robustness: West-Lantau core only (NEL excluded)\n")
    lines.append(f"any_reclamation IRR = {np.exp(res3.params['any_reclamation']):.3f} "
                 f"(p = {res3.pvalues['any_reclamation']:.3f}); "
                 f"year IRR = {np.exp(res3.params['year_c']):.3f}.\n")

    lines.append("## NB-GAM (smooth year) - low power, descriptive only\n")
    try:
        from statsmodels.gam.api import GLMGam, BSplines
        alpha_hat = float(res.params.get("alpha", 1.0))
        bs = BSplines(df["year_c"].values, df=[5], degree=[3])
        gam = GLMGam.from_formula("on_effort_sightings ~ C(area_code) + any_reclamation",
                                  data=df, smoother=bs,
                                  family=sm.families.NegativeBinomial(alpha=alpha_hat),
                                  offset=df["log_effort"].values).fit()
        lines.append(f"Fitted GLMGam with a degree-3 B-spline on year (df=5), NB family "
                     f"(alpha={alpha_hat:.3f}). AIC = {gam.aic:.1f}. "
                     "With only 10 distinct years and 4 areas, treat the smooth as "
                     "illustrative; the coordinate-level GAM on the 2,209 sightings is "
                     "where a spatial GAM is properly powered.\n")
    except Exception as exc:
        lines.append(f"GAM skipped ({exc}).\n")

    fig_encounter(df, out)
    fig_abundance(df, out)
    fig_irr(irr, out)
    lines.append("## Figures\n")
    lines.append("- `fig_encounter_rate_trend.png` - on-effort encounter rate by area\n"
                 "- `fig_abundance_trend.png` - annual abundance by area\n"
                 "- `fig_nb_irr.png` - NB GLM incidence rate ratios\n")

    (out / "model_results.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote model_results.md and 3 figures")
    print(f"\nOverdispersion Pearson/df = {pearson:.2f}")
    print("\nMain NB GLM IRR table:")
    print(irr.to_string())


if __name__ == "__main__":
    main()
