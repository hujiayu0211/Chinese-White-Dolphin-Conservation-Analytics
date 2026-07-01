import argparse
import glob
import re
from pathlib import Path
import pandas as pd

ZONE_TO_AREAS = {
    "North Western": ["NWL", "WL"],
    "Western Buffer": ["NEL"],
    "Southern": ["SWL"],
    "Deep Bay": ["DB"],
}

SOUTHERN_SWL_STATIONS = ["SM13", "SM17", "SM20"]

PARAMS = {
    "temperature": "Temperature (°C)",
    "salinity": "Salinity (psu)",
    "dissolved_oxygen_mg_l": "Dissolved Oxygen (mg/L)",
    "turbidity": "Turbidity (NTU)",
    "suspended_solids": "Suspended Solids (mg/L)",
    "chlorophyll_a": "Chlorophyll-a (μg/L)",
    "ammonia_nitrogen": "Ammonia Nitrogen (mg/L)",
    "total_inorganic_nitrogen": "Total Inorganic Nitrogen (mg/L)",
}

SURFACE_TOKENS = ("surface",)


def to_numeric_keep_limits(series):
    def conv(v):
        if pd.isna(v):
            return None
        m = re.search(r"[-+]?\d*\.?\d+", str(v).strip())
        return float(m.group(0)) if m else None
    return series.map(conv)


def assign_monitoring_period(dates):
    dt = pd.to_datetime(dates, errors="coerce")
    start = dt.dt.year.where(dt.dt.month >= 4, dt.dt.year - 1)
    end2 = (start + 1).astype("Int64").astype(str).str[-2:]
    return start.astype("Int64").astype(str) + "-" + end2


def load_all(input_dir):
    files = sorted(glob.glob(str(input_dir / "marine-historical-*.csv")))
    if not files:
        raise FileNotFoundError(f"No marine-historical-*.csv in {input_dir}")
    frames = []
    for f in files:
        d = pd.read_csv(f)
        d["source_file"] = Path(f).name
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="marine_water_quality_data")
    ap.add_argument("--output-dir", default="processed")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    raw = load_all(Path(args.input_dir))
    print(f"Loaded {len(raw)} rows from {raw['source_file'].nunique()} files")

    df = raw[raw["Depth"].astype(str).str.lower().apply(
        lambda v: any(t in v for t in SURFACE_TOKENS))].copy()
    print(f"Surface rows: {len(df)}")

    df["monitoring_period"] = assign_monitoring_period(df["Dates"])
    df["monitoring_start_year"] = df["monitoring_period"].str[:4].astype("Int64")

    for name, col in PARAMS.items():
        df[name] = to_numeric_keep_limits(df[col])
    value_cols = list(PARAMS.keys())

    keep_zones = list(ZONE_TO_AREAS.keys())
    zdf = df[df["Water Control Zone"].isin(keep_zones)]
    zone_period = (
        zdf.groupby(["monitoring_period", "monitoring_start_year", "Water Control Zone"], as_index=False)
        .agg(n_samples=("Station", "size"), **{c: (c, "mean") for c in value_cols})
        .sort_values(["monitoring_start_year", "Water Control Zone"])
    )
    zone_period.to_csv(out / "water_quality_by_zone_period.csv", index=False, encoding="utf-8-sig")

    parts = []
    for zone, areas in ZONE_TO_AREAS.items():
        sub = df[df["Water Control Zone"] == zone]
        if zone == "Southern" and SOUTHERN_SWL_STATIONS:
            sub = sub[sub["Station"].isin(SOUTHERN_SWL_STATIONS)]
        for area in areas:
            s = sub.copy()
            s["area_code"] = area
            parts.append(s)
    mapped = pd.concat(parts, ignore_index=True)

    area_period = (
        mapped.groupby(["monitoring_period", "monitoring_start_year", "area_code"], as_index=False)
        .agg(n_samples=("Station", "size"), **{c: (c, "mean") for c in value_cols})
        .sort_values(["monitoring_start_year", "area_code"])
        .reset_index(drop=True)
    )
    area_period.to_csv(out / "water_quality_by_area_period.csv", index=False, encoding="utf-8-sig")

    long_cols = ["source_file", "Water Control Zone", "Station", "Dates",
                 "monitoring_period", "monitoring_start_year"] + value_cols
    df[long_cols].to_csv(out / "epd_water_quality_surface_long.csv", index=False, encoding="utf-8-sig")

    print(f"zone x period rows: {len(zone_period)}  ->  water_quality_by_zone_period.csv")
    print(f"area x period rows: {len(area_period)}  ->  water_quality_by_area_period.csv")
    return zone_period, area_period


if __name__ == "__main__":
    main()
