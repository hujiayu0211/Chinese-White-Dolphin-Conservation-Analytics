import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import patsy
from statsmodels.discrete.discrete_model import NegativeBinomial
from statsmodels.stats.outliers_influence import variance_inflation_factor

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"figure.dpi": 150, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})

CORE = ["NEL", "NWL", "WL", "SWL"]
WQ_ALL = ["temperature", "salinity", "dissolved_oxygen_mg_l", "turbidity",
          "suspended_solids", "chlorophyll_a", "ammonia_nitrogen"]


def vif_table(X):
    Xc = sm.add_constant(X, has_constant="add")
    rows = []
    for i, name in enumerate(Xc.columns):
        if name == "const":
            continue
        rows.append((name, variance_inflation_factor(Xc.values, i)))
    return pd.DataFrame(rows, columns=["variable", "VIF"]).sort_values("VIF", ascending=False)


def zscore(df, cols):
    out = df.copy()
    for c in cols:
        out[c + "_z"] = (out[c] - out[c].mean()) / out[c].std()
    return out


def nb_fit(df, formula):
    y, X = patsy.dmatrices("on_effort_sightings ~ " + formula, df, return_type="dataframe")
    res = NegativeBinomial(y, X, offset=df["log_effort"].values).fit(disp=0, maxiter=300)
    return res, X


def irr(res):
    p = res.params.drop(labels=[c for c in res.params.index if c == "alpha"], errors="ignore")
    ci = res.conf_int().loc[p.index]
    return pd.DataFrame({"IRR": np.exp(p), "lo": np.exp(ci[0]), "hi": np.exp(ci[1]),
                         "p": res.pvalues.loc[p.index]}).round(4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="processed/cwd_master_panel.csv")
    ap.add_argument("--output-dir", default="result_figure")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    m = pd.read_csv(args.panel)
    df = m[m.area_code.isin(CORE)].dropna(subset=WQ_ALL + ["survey_effort_km"]).copy()
    df = df[df.survey_effort_km > 0]
    df["year_c"] = df["monitoring_start_year"] - df["monitoring_start_year"].min()
    df["log_effort"] = np.log(df["survey_effort_km"])
    df["area_code"] = pd.Categorical(df["area_code"], categories=CORE)
    df = zscore(df, WQ_ALL)
    zcols = [c + "_z" for c in WQ_ALL]

    L = ["# Water-quality NB model + VIF diagnostics\n",
         f"Core areas {CORE}, {len(df)} rows. WQ standardised (per 1 SD). "
         "total_inorganic_nitrogen dropped a priori (r=-0.92 with salinity).\n"]

    v1 = vif_table(df[zcols])
    L += ["## VIF among water-quality variables only\n", v1.to_markdown(index=False) + "\n"]

    Xfull = patsy.dmatrix("C(area_code) + year_c + " + " + ".join(zcols),
                          df, return_type="dataframe")
    v2 = vif_table(Xfull.drop(columns=[c for c in Xfull.columns if c.lower() == "intercept"]))
    L += ["## VIF with area fixed effects + year added\n",
          "High VIF on salinity here is the area/plume confound: within the four "
          "areas salinity is almost constant, so it is largely a linear combination "
          "of the area dummies.\n", v2.to_markdown(index=False) + "\n"]

    keep = v1[v1.VIF <= 5]["variable"].tolist()
    if not keep:
        keep = ["salinity_z", "turbidity_z", "dissolved_oxygen_mg_l_z", "temperature_z"]
    L += [f"## Parsimonious WQ set kept (VIF<=5): {keep}\n"]

    res0, _ = nb_fit(df, "C(area_code) + year_c")
    res1, _ = nb_fit(df, "C(area_code) + year_c + any_reclamation")
    res2, _ = nb_fit(df, "C(area_code) + year_c + any_reclamation + " + " + ".join(keep))

    L += ["## NB model comparison (response = on-effort sightings, offset log effort)\n"]
    L += [f"- M0 area+year: year IRR = {np.exp(res0.params['year_c']):.3f}, "
          f"pseudo-R2 = {res0.prsquared:.3f}\n"
          f"- M1 +reclamation: year IRR = {np.exp(res1.params['year_c']):.3f}, "
          f"pseudo-R2 = {res1.prsquared:.3f}\n"
          f"- M2 +water quality: year IRR = {np.exp(res2.params['year_c']):.3f}, "
          f"pseudo-R2 = {res2.prsquared:.3f}\n"]
    L += ["\n### M2 full table (IRR per 1 SD for WQ)\n", irr(res2).to_markdown() + "\n"]

    L += ["## Reading the water-quality coefficients\n",
          "WQ enters as a control: the IRRs are per-1-SD within-panel change after "
          "area and year are accounted for. Because salinity barely varies within an "
          "area over time (see VIF), its coefficient is weakly identified and should "
          "not be read as a causal salinity effect on dolphins. The key check is "
          "whether the year trend is robust to adding WQ: compare M0/M1/M2 above.\n"]

    (out / "model_wq_results.md").write_text("\n".join(L), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(8, 0.5 * len(v2) + 1.5))
    vsort = v2.sort_values("VIF").copy()
    cap = 25.0
    vsort["plot"] = vsort["VIF"].clip(upper=cap)
    colors = ["#C44E52" if v > 5 else "#4C72B0" for v in vsort["VIF"]]
    ax.barh(vsort["variable"], vsort["plot"], color=colors)
    for y, (v, p) in enumerate(zip(vsort["VIF"], vsort["plot"])):
        ax.text(p + 0.3, y, f"{v:.1f}" + (" (capped)" if v > cap else ""),
                va="center", fontsize=8)
    ax.axvline(5, color="grey", ls="--", lw=1)
    ax.set_xlim(0, cap + 5)
    ax.set_xlabel("VIF (red = >5; bars capped at 25 for display)")
    ax.set_title("VIF with area fixed effects + year + water quality")
    plt.tight_layout()
    fig.savefig(out / "fig_vif.png", bbox_inches="tight")
    plt.close(fig)

    print("Wrote model_wq_results.md and fig_vif.png\n")
    print("VIF (WQ only):")
    print(v1.to_string(index=False))
    print("\nYear IRR  M0/M1/M2:",
          round(np.exp(res0.params['year_c']), 3),
          round(np.exp(res1.params['year_c']), 3),
          round(np.exp(res2.params['year_c']), 3))
    print("\nM2 WQ IRRs:")
    print(irr(res2).loc[keep].to_string())


if __name__ == "__main__":
    main()
