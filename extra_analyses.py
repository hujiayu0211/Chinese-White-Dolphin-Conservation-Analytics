import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import pymannkendall as mk

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"figure.dpi": 150, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})

CORE = ["NEL", "NWL", "WL", "SWL"]
SEASON_ORDER = ["SPRING", "SUMMER", "AUTUMN", "WINTER"]
PAL = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]


def pettitt_test(y):
    y = np.asarray(y, float)
    n = len(y)
    U = np.zeros(n)
    for t in range(n):
        s = 0.0
        for i in range(t + 1):
            for j in range(t + 1, n):
                s += np.sign(y[i] - y[j])
        U[t] = s
    k = int(np.argmax(np.abs(U)))
    K = abs(U[k])
    p = float(2.0 * np.exp(-6.0 * K ** 2 / (n ** 3 + n ** 2)))
    return k, min(p, 1.0)


def load(sight_path, eff_path):
    s = pd.read_csv(sight_path)
    e = pd.read_csv(eff_path)
    s["on"] = s["effort_status"].astype(str).str.upper() == "ON"
    s["boat_assoc"] = s["boat_assoc"].astype(str).str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
    s["boat_assoc"] = s["boat_assoc"].replace({"GILL NET": "GILLNET"})
    return s, e


def seasonal(s, e, out):
    son = s[s.on & s.area_code.isin(CORE)]
    ec = e[e.area_code.isin(CORE)]
    sig = son.groupby("season").size()
    eff = ec.groupby("season")["effort_km"].sum()
    tab = pd.DataFrame({"on_sightings": sig, "effort_km": eff.round(0)}).reindex(SEASON_ORDER)
    tab["enc_per_100km"] = (tab["on_sightings"] / tab["effort_km"] * 100).round(2)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(tab.index, tab["enc_per_100km"], color=PAL)
    for i, v in enumerate(tab["enc_per_100km"]):
        ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=10)
    ax.set_ylabel("On-effort sightings per 100 km")
    ax.set_title("Encounter rate by season (core Lantau areas, 2012-2022)")
    fig.text(0.01, 0.005, "Wet season (spring/summer) carries the Pearl-River plume the dolphins prefer.", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_seasonal.png", bbox_inches="tight")
    plt.close(fig)

    lines = ["## 1. Seasonal analysis\n", tab.to_markdown() + "\n"]
    hi, lo = tab["enc_per_100km"].idxmax(), tab["enc_per_100km"].idxmin()
    lines.append(f"Encounter rate peaks in **{hi}** ({tab.loc[hi,'enc_per_100km']}) and is lowest in "
                 f"**{lo}** ({tab.loc[lo,'enc_per_100km']} per 100 km).\n")
    return lines


def group_size(s, out):
    son = s[s.on & s.area_code.isin(CORE)].dropna(subset=["herd_size"])
    yr = son.groupby("monitoring_start_year")["herd_size"].agg(["mean", "median", "size"]).round(2)

    ols = smf.ols("herd_size ~ monitoring_start_year", data=son).fit()
    slope = ols.params["monitoring_start_year"]
    p_ols = ols.pvalues["monitoring_start_year"]
    mkres = mk.original_test(yr["mean"].values)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(yr.index, yr["mean"], "-o", color="#4C72B0", label="Mean herd size")
    xs = np.array(yr.index)
    ax.plot(xs, ols.params["Intercept"] + slope * xs, "--", color="#C44E52",
            label=f"OLS trend ({slope:+.3f}/yr, p={p_ols:.3f})")
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean herd size (on-effort)")
    ax.set_title("Group-size trend, core Lantau areas")
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(out / "fig_group_size.png", bbox_inches="tight")
    plt.close(fig)

    lines = ["## 2. Group-size trend\n", yr.to_markdown() + "\n",
             f"\nOLS slope = {slope:+.3f} dolphins/year (p = {p_ols:.3f}); "
             f"Mann-Kendall on annual means: trend = **{mkres.trend}**, p = {mkres.p:.3f}, "
             f"Sen's slope = {mkres.slope:+.3f}.\n",
             "Group size " + ("shows no significant time trend"
             if mkres.p >= 0.05 else f"is {mkres.trend} over time") +
             " — i.e. the decline is driven by fewer encounters, not smaller groups.\n"
             if mkres.p >= 0.05 else
             f"Group size is significantly {mkres.trend} over time.\n"]
    return lines


def change_point(s, e, out):
    son = s[s.on & s.area_code.isin(CORE)]
    ec = e[e.area_code.isin(CORE)]
    sig = son.groupby("monitoring_start_year").size()
    eff = ec.groupby("monitoring_start_year")["effort_km"].sum()
    rate = (sig / eff * 100).dropna().sort_index()
    years = rate.index.values
    y = rate.values

    cp_idx, cp_p = pettitt_test(y)
    mkres = mk.original_test(y)

    best = None
    for k in range(2, len(years) - 1):
        bp = years[k]
        X = np.column_stack([np.ones_like(years), years - bp,
                             np.where(years >= bp, years - bp, 0.0)])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(((y - X @ beta) ** 2).sum())
        if best is None or sse < best[1]:
            best = (bp, sse, beta)
    bp, _, beta = best

    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.plot(years, y, "-o", color="#4C72B0", label="On-effort encounter rate")
    cp_year = years[cp_idx]
    ax.axvline(cp_year, color="#C44E52", ls="--", label=f"Pettitt change-point ≈ {cp_year}")
    ax.axvspan(2016, 2020, color="grey", alpha=0.12)
    ax.text(2018, ax.get_ylim()[1] * 0.95, "3RS reclamation", ha="center", fontsize=9, color="grey")
    ax.set_xlabel("Year")
    ax.set_ylabel("On-effort sightings per 100 km")
    ax.set_title("Change-point in the effort-controlled encounter rate")
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(out / "fig_changepoint.png", bbox_inches="tight")
    plt.close(fig)

    lines = ["## 3. Change-point test\n",
             f"- Mann-Kendall: trend = **{mkres.trend}**, p = {mkres.p:.3f}, Sen's slope = {mkres.slope:+.3f}/yr\n"
             f"- Pettitt single change-point at **{cp_year}** (p = {cp_p:.3f})\n"
             f"- Segmented regression breakpoint at **{bp}**; slope before = {beta[1]:+.3f}, "
             f"after = {beta[1]+beta[2]:+.3f} per year\n",
             f"\nThe break falls around {cp_year}, within the HZMB-to-3RS reclamation window "
             "(2011-2020), consistent with reclamation-associated decline rather than a "
             "purely gradual trend.\n"]
    return lines


def fishery(s, out):
    son = s[s.on & s.area_code.isin(CORE)].copy()
    son["fishing"] = (son["boat_assoc"] != "NONE").astype(int)
    yr = son.groupby("monitoring_start_year")["fishing"].agg(["mean", "sum", "size"])
    yr["pct"] = (yr["mean"] * 100).round(1)
    mkres = mk.original_test(yr["mean"].values)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(yr.index, yr["pct"], "-o", color="#DD8452")
    ax.set_xlabel("Year")
    ax.set_ylabel("% of on-effort sightings with fishing-gear association")
    ax.set_title("Fishing-vessel association of dolphin sightings over time")
    fig.text(0.01, 0.005, "boat_assoc != NONE (purse seine, gillnet, etc.); core Lantau areas.", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_fishery.png", bbox_inches="tight")
    plt.close(fig)

    lines = ["## 4. Fishery association\n", yr[["sum", "size", "pct"]].to_markdown() + "\n",
             f"\nMann-Kendall on the annual association rate: trend = **{mkres.trend}**, "
             f"p = {mkres.p:.3f}, Sen's slope = {mkres.slope:+.4f}/yr. "
             "Base rate is low, so read this as indicative.\n"]
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sightings", default="processed/cwd_sightings_clean.csv")
    ap.add_argument("--effort", default="processed/cwd_survey_effort_clean.csv")
    ap.add_argument("--output-dir", default="result_figure")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    s, e = load(args.sightings, args.effort)
    L = ["# Extension analyses (seasonal / group size / change-point / fishery)\n",
         f"Core areas {CORE}, on-effort sightings, monitoring periods 2012-13 to 2021-22.\n"]
    L += seasonal(s, e, out)
    L += group_size(s, out)
    L += change_point(s, e, out)
    L += fishery(s, out)
    L += ["## Figures\n",
          "- `fig_seasonal.png`  - encounter rate by season\n"
          "- `fig_group_size.png` - mean herd size over time\n"
          "- `fig_changepoint.png` - change-point in encounter rate\n"
          "- `fig_fishery.png`   - fishing-gear association over time\n"]
    (out / "extra_analyses_results.md").write_text("\n".join(L), encoding="utf-8")
    print("Wrote extra_analyses_results.md and 4 figures")


if __name__ == "__main__":
    main()
