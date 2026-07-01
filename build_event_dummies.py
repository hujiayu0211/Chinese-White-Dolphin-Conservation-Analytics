import argparse
from pathlib import Path
import pandas as pd

EVENTS = {
    "hzmb_construction": dict(areas=["NEL"], start=2011, end=2017),
    "hzmb_post_open":    dict(areas=["NEL", "NWL"], start=2018, end=None),
    "rs3_reclamation":   dict(areas=["NEL", "NWL"], start=2016, end=2020),
    "mp_brothers":       dict(areas=["NEL"], start=2016, end=None),
    "mp_sw_lantau":      dict(areas=["SWL"], start=2020, end=None),
    "mp_south_lantau":   dict(areas=["SWL"], start=2022, end=None),
}

COMPOSITES = {
    "any_reclamation": ["hzmb_construction", "rs3_reclamation"],
    "any_marine_park": ["mp_brothers", "mp_sw_lantau", "mp_south_lantau"],
}


def build_event_dummies(panel):
    keys = panel[["monitoring_period", "monitoring_start_year", "area_code"]].drop_duplicates().copy()
    msy = keys["monitoring_start_year"]
    for name, spec in EVENTS.items():
        end = spec["end"] if spec["end"] is not None else 10 ** 9
        active = keys["area_code"].isin(spec["areas"]) & msy.between(spec["start"], end)
        keys[name] = active.astype(int)
    for name, parts in COMPOSITES.items():
        keys[name] = keys[parts].max(axis=1)
    return keys.sort_values(["monitoring_start_year", "area_code"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-data", default="processed/cwd_area_period_model_data.csv")
    ap.add_argument("--abundance", default="processed/cwd_abundance_2003_2021_long.csv")
    ap.add_argument("--water-quality", default="processed/water_quality_by_area_period.csv")
    ap.add_argument("--output-dir", default="processed")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(args.model_data)

    dummies = build_event_dummies(panel)
    dummies.to_csv(out / "event_dummies_by_area_period.csv", index=False, encoding="utf-8-sig")
    print(f"event dummies: {dummies.shape} -> event_dummies_by_area_period.csv")

    master = panel.merge(
        dummies.drop(columns=["monitoring_start_year"]),
        on=["monitoring_period", "area_code"], how="left",
    )

    abund = pd.read_csv(args.abundance)
    abund = abund[abund["area_code"].isin(["NEL", "NWL", "WL", "SWL"])][
        ["year", "area_code", "abundance", "low_reliability_no_sighting"]
    ].rename(columns={
        "year": "monitoring_start_year",
        "abundance": "annual_abundance",
        "low_reliability_no_sighting": "abundance_low_reliability",
    })
    master = master.merge(abund, on=["monitoring_start_year", "area_code"], how="left")

    if args.water_quality:
        wq = pd.read_csv(args.water_quality)
        wq_cols = [c for c in wq.columns if c not in ("monitoring_start_year", "n_samples")]
        master = master.merge(wq[wq_cols].rename(columns={"n_samples": "wq_n_samples"}),
                              on=["monitoring_period", "area_code"], how="left")

    master = master.sort_values(["monitoring_start_year", "area_code"]).reset_index(drop=True)
    master.to_csv(out / "cwd_master_panel.csv", index=False, encoding="utf-8-sig")
    print(f"master panel: {master.shape} -> cwd_master_panel.csv")
    print("  water quality merged" if args.water_quality else "  (water quality not merged)")
    return dummies, master


if __name__ == "__main__":
    main()
