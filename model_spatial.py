import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"figure.dpi": 150, "axes.titleweight": "bold"})

from pygam import PoissonGAM, te

BLOCKS = {
    "2012-2015 (early / HZMB)": (2012, 2015),
    "2016-2019 (3RS reclamation)": (2016, 2019),
    "2020-2022 (post)": (2020, 2022),
}
AREA_LABELS = {"NWL": "NW Lantau", "WL": "W Lantau", "SWL": "SW Lantau",
               "NEL": "NE Lantau", "DB": "Deep Bay"}
EXTENT = (798000, 820000, 800000, 829000)
GRID_N = 160


def load(path):
    s = pd.read_csv(path).dropna(subset=["northing", "easting"])
    s = s[s["effort_status"].astype(str).str.upper() == "ON"].copy()
    s["msy"] = s["monitoring_start_year"]
    return s


def block_of(year):
    for name, (a, b) in BLOCKS.items():
        if a <= year <= b:
            return name
    return None


def kde_grid(E, N, extent, n):
    xs = np.linspace(extent[0], extent[1], n)
    ys = np.linspace(extent[2], extent[3], n)
    XX, YY = np.meshgrid(xs, ys)
    kde = gaussian_kde(np.vstack([E, N]))
    ZZ = kde(np.vstack([XX.ravel(), YY.ravel()])).reshape(XX.shape)
    ZZ = ZZ / ZZ.sum()
    return xs, ys, XX, YY, ZZ


def hpd_levels(ZZ, fractions=(0.5, 0.95)):
    flat = np.sort(ZZ.ravel())[::-1]
    csum = np.cumsum(flat)
    levels = []
    for f in fractions:
        idx = np.searchsorted(csum, f)
        levels.append(flat[min(idx, len(flat) - 1)])
    return levels


def core_area_km2(xs, ys, ZZ, level50):
    cell = ((xs[1] - xs[0]) * (ys[1] - ys[0])) / 1e6
    return float((ZZ >= level50).sum() * cell)


def fig_kde_blocks(s, out):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5), sharex=True, sharey=True)
    area_cent = s.groupby("area_code")[["easting", "northing"]].mean()
    for ax, (name, (a, b)) in zip(axes, BLOCKS.items()):
        d = s[(s.msy >= a) & (s.msy <= b)]
        xs, ys, XX, YY, ZZ = kde_grid(d.easting.values, d.northing.values, EXTENT, GRID_N)
        ax.pcolormesh(XX / 1000, YY / 1000, ZZ, cmap="magma", shading="auto")
        l50, l95 = hpd_levels(ZZ, (0.5, 0.95))
        ax.contour(XX / 1000, YY / 1000, ZZ, levels=[l95], colors="white", linewidths=1.0, linestyles="--")
        ax.contour(XX / 1000, YY / 1000, ZZ, levels=[l50], colors="cyan", linewidths=1.5)
        for code, lab in AREA_LABELS.items():
            if code in area_cent.index:
                ax.text(area_cent.loc[code, "easting"] / 1000, area_cent.loc[code, "northing"] / 1000,
                        lab, fontsize=8, color="white", ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.35, ec="none"))
        ax.set_title(f"{name}\n(n={len(d)} on-effort)", fontsize=11)
        ax.set_xlabel("Easting (km, HK1980)")
    axes[0].set_ylabel("Northing (km, HK1980)")
    fig.suptitle("Dolphin utilization distribution by period — cyan = 50% core, white dashed = 95% range",
                 fontsize=13, y=1.02)
    fig.text(0.01, 0.005, "On-effort sightings; each panel normalised to a probability density. Source: AFCD monitoring reports 2012-13 to 2021-22.", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_kde_blocks.png", bbox_inches="tight")
    plt.close(fig)


def fig_core_migration(s, out):
    fig, ax = plt.subplots(figsize=(8.5, 8))
    cols = ["#4C72B0", "#DD8452", "#C44E52"]
    for (name, (a, b)), c in zip(BLOCKS.items(), cols):
        d = s[(s.msy >= a) & (s.msy <= b)]
        xs, ys, XX, YY, ZZ = kde_grid(d.easting.values, d.northing.values, EXTENT, GRID_N)
        l50, _ = hpd_levels(ZZ, (0.5, 0.95))
        ax.contour(XX / 1000, YY / 1000, ZZ, levels=[l50], colors=[c], linewidths=2)
        ax.plot([], [], color=c, lw=2, label=f"50% core {name}")
    cent = s.groupby("msy")[["easting", "northing"]].mean().sort_index()
    ax.plot(cent.easting / 1000, cent.northing / 1000, "-o", color="black", lw=1.2, ms=4, zorder=5)
    for yr, row in cent.iterrows():
        ax.annotate(str(yr)[2:], (row.easting / 1000, row.northing / 1000), fontsize=7, color="black")
    ax.set_xlabel("Easting (km, HK1980)")
    ax.set_ylabel("Northing (km, HK1980)")
    ax.set_title("Core-habitat (50% KUD) contours and annual sighting-centroid trajectory")
    ax.legend(loc="upper right", fontsize=8)
    fig.text(0.01, 0.005, "Black track = mean on-effort sighting location per monitoring period (labelled by start year).", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_core_migration.png", bbox_inches="tight")
    plt.close(fig)


def gam_surface(d, extent, grid_n, cell_km=1.5):
    step = cell_km * 1000
    e_edges = np.arange(extent[0], extent[1] + step, step)
    n_edges = np.arange(extent[2], extent[3] + step, step)
    H, _, _ = np.histogram2d(d.easting, d.northing, bins=[e_edges, n_edges])
    ec = (e_edges[:-1] + e_edges[1:]) / 2
    nc = (n_edges[:-1] + n_edges[1:]) / 2
    EC, NC = np.meshgrid(ec, nc, indexing="ij")
    Xtr = np.column_stack([EC.ravel(), NC.ravel()])
    ytr = H.ravel()
    gam = PoissonGAM(te(0, 1, n_splines=8), fit_intercept=True).fit(Xtr, ytr)
    xs = np.linspace(extent[0], extent[1], grid_n)
    ys = np.linspace(extent[2], extent[3], grid_n)
    XX, YY = np.meshgrid(xs, ys)
    pred = gam.predict(np.column_stack([XX.ravel(), YY.ravel()])).reshape(XX.shape)
    pred = np.clip(pred, 0, None)
    pred = pred / pred.sum()
    return XX, YY, pred


def fig_gam_surfaces(s, out):
    early = s[(s.msy >= 2012) & (s.msy <= 2015)]
    late = s[(s.msy >= 2020) & (s.msy <= 2022)]
    XX, YY, Pe = gam_surface(early, EXTENT, GRID_N)
    _, _, Pl = gam_surface(late, EXTENT, GRID_N)
    diff = Pl - Pe
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5), sharex=True, sharey=True)
    vmax = max(Pe.max(), Pl.max())
    for ax, Z, t in zip(axes[:2], [Pe, Pl], ["Early 2012-2015", "Late 2020-2022"]):
        ax.pcolormesh(XX / 1000, YY / 1000, Z, cmap="magma", vmin=0, vmax=vmax, shading="auto")
        ax.set_title(f"GAM relative intensity — {t}")
        ax.set_xlabel("Easting (km)")
    m = np.abs(diff).max()
    pcm = axes[2].pcolormesh(XX / 1000, YY / 1000, diff, cmap="RdBu_r", vmin=-m, vmax=m, shading="auto")
    axes[2].set_title("Difference (late − early)\nred = gained, blue = lost")
    axes[2].set_xlabel("Easting (km)")
    fig.colorbar(pcm, ax=axes[2], fraction=0.046)
    axes[0].set_ylabel("Northing (km)")
    fig.suptitle("Spatial GAM (Poisson tensor smooth) relative-intensity surfaces; each block normalised", y=1.02, fontsize=13)
    fig.text(0.01, 0.005, "Relative intensity (no per-cell effort offset available); normalised per block to isolate spatial redistribution.", fontsize=8, color="grey")
    plt.tight_layout()
    fig.savefig(out / "fig_gam_surfaces.png", bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sightings", default="processed/cwd_sightings_clean.csv")
    ap.add_argument("--output-dir", default="result_figure")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    s = load(args.sightings)

    fig_kde_blocks(s, out)
    fig_core_migration(s, out)
    fig_gam_surfaces(s, out)

    L = ["# Spatial habitat-use results\n",
         f"On-effort georeferenced sightings: n = {len(s)}. Surfaces are relative "
         "utilization (effort recorded by area, not grid), each block normalised.\n"]

    cent = s.groupby("msy")[["easting", "northing"]].mean().round(0)
    cent.columns = ["E", "N"]
    net_e = cent.E.iloc[-1] - cent.E.iloc[0]
    net_n = cent.N.iloc[-1] - cent.N.iloc[0]
    dist = np.hypot(net_e, net_n) / 1000
    L += ["## Annual sighting centroid (HK1980 m)\n", cent.to_markdown() + "\n",
          f"\nNet centroid shift {cent.index[0]}→{cent.index[-1]}: "
          f"ΔE={net_e:.0f} m, ΔN={net_n:.0f} m (≈ {dist:.1f} km; "
          f"{'westward ' if net_e < 0 else 'eastward '}{'+ southward' if net_n < 0 else '+ northward'}).\n"]

    L += ["## 50% core-area size per block (km²)\n"]
    rows = []
    for name, (a, b) in BLOCKS.items():
        d = s[(s.msy >= a) & (s.msy <= b)]
        xs, ys, XX, YY, ZZ = kde_grid(d.easting.values, d.northing.values, EXTENT, GRID_N)
        l50, _ = hpd_levels(ZZ, (0.5, 0.95))
        rows.append((name, len(d), round(core_area_km2(xs, ys, ZZ, l50), 1)))
    L += [pd.DataFrame(rows, columns=["block", "n_sightings", "core_50pct_km2"]).to_markdown(index=False) + "\n"]

    L += ["## Share of on-effort sightings by area (%), by block\n"]
    s["block"] = s.msy.map(block_of)
    share = (pd.crosstab(s["block"], s["area_code"], normalize="index") * 100).round(1)
    keep = [c for c in ["NEL", "NWL", "WL", "SWL", "DB"] if c in share.columns]
    L += [share[keep].to_markdown() + "\n"]

    L += ["## Figures\n",
          "- `fig_kde_blocks.png` — utilization heatmaps per block (50%/95% contours)\n"
          "- `fig_core_migration.png` — 50% core contours of all blocks + centroid track\n"
          "- `fig_gam_surfaces.png` — spatial GAM intensity: early, late, difference\n"]

    (out / "model_spatial_results.md").write_text("\n".join(L), encoding="utf-8")
    print("Wrote model_spatial_results.md and 3 figures")
    print(cent.to_string())
    print(f"\nNet centroid shift ≈ {dist:.1f} km")


if __name__ == "__main__":
    main()
