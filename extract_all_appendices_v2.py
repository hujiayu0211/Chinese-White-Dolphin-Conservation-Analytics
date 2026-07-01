from pathlib import Path
import argparse
import re
import fitz
import pandas as pd

DATE_RE = re.compile(r"^\d{1,2}(?:-[A-Za-z]{3}-\d{2,4}|/\d{1,2}/\d{2,4})$")

AREA_ALIASES = {
    "SW LAMTAU": "SW LANTAU",
    "NW LAUTAU": "NW LANTAU",
}

AREA_CODE_MAP = {
    "DEEP BAY": "DB",
    "NW LANTAU": "NWL",
    "NE LANTAU": "NEL",
    "W LANTAU": "WL",
    "SW LANTAU": "SWL",
    "SE LANTAU": "SEL",
    "E LANTAU": "EL",
    "LAMMA": "LM",
    "PO TOI": "PT",
    "NINEPINS": "NP",
    "SAI KUNG": "SK",
}

SURVEY_COLUMNS = [
    "date_raw", "area", "beaufort", "effort_km", "season", "vessel", "primary_secondary",
]

SIGHTING_COLUMNS = [
    "date_raw", "stage_no", "time_raw", "herd_size", "area", "beaufort", "psd_raw",
    "effort_status", "source_type", "northing", "easting", "season", "boat_assoc",
    "primary_secondary",
]


def normalize_text(value):
    return " ".join(value.lower().split())


def clean_cell(value):
    if value is None:
        return None
    value = str(value).replace("\u00a0", " ").strip()
    return re.sub(r"\s+", " ", value)


def infer_period_from_filename(pdf_path):
    match = re.search(r"(20\d{2})[-_](\d{2})", pdf_path.stem)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return pdf_path.stem


def infer_start_year(period):
    match = re.search(r"20\d{2}", str(period))
    return int(match.group(0)) if match else None


def find_appendix_pages(pdf_path):
    doc = fitz.open(pdf_path)
    page_hits = {"survey_start": [], "sighting_start": [], "porpoise_start": []}
    survey_re = re.compile(r"appendix i\. (?:hkcrp-afcd )?survey effort database")
    sighting_re = re.compile(r"appendix ii\. (?:hkcrp-afcd )?chinese white dolphin sighting database")
    porpoise_re = re.compile(r"appendix iii\. (?:hkcrp-afcd )?finless porpoise sighting database")
    for index in range(len(doc)):
        text = normalize_text(doc[index].get_text())
        if survey_re.search(text):
            page_hits["survey_start"].append(index)
        if sighting_re.search(text):
            page_hits["sighting_start"].append(index)
        if porpoise_re.search(text):
            page_hits["porpoise_start"].append(index)
    survey_start = page_hits["survey_start"][-1] if page_hits["survey_start"] else None
    sighting_start = page_hits["sighting_start"][-1] if page_hits["sighting_start"] else None
    porpoise_start = page_hits["porpoise_start"][-1] if page_hits["porpoise_start"] else None
    survey_end = sighting_start - 1 if survey_start is not None and sighting_start is not None else None
    sighting_end = porpoise_start - 1 if sighting_start is not None and porpoise_start is not None else None
    return {
        "survey_start": survey_start, "survey_end": survey_end,
        "sighting_start": sighting_start, "sighting_end": sighting_end,
        "porpoise_start": porpoise_start, "page_count": len(doc),
    }


def get_data_tokens(doc, page_index):
    lines = [clean_cell(line) for line in doc[page_index].get_text().splitlines()]
    lines = [line for line in lines if line]
    header_positions = [i for i, line in enumerate(lines) if line and line.upper() == "P/S"]
    start = header_positions[-1] + 1 if header_positions else 0
    return lines[start:]


def parse_survey_records(doc, start_page, end_page):
    tokens = []
    for page_index in range(start_page, end_page + 1):
        tokens.extend(get_data_tokens(doc, page_index))
    raw_records = []
    current = []
    for token in tokens:
        if DATE_RE.match(token):
            if current:
                raw_records.append(current)
            current = [token]
        elif current:
            current.append(token)
    if current:
        raw_records.append(current)
    records = []
    bad_records = []
    for record in raw_records:
        if len(record) >= 7:
            records.append([record[0], record[1], record[2], record[3], record[4], record[5], record[-1]])
        else:
            bad_records.append({"tokens": record})
    return records, bad_records


def split_sighting_records(doc, start_page, end_page):
    tokens = []
    for page_index in range(start_page, end_page + 1):
        tokens.extend(get_data_tokens(doc, page_index))
    records = []
    current = []
    for token in tokens:
        if DATE_RE.match(token):
            if current:
                records.append(current)
            current = [token]
        elif current:
            current.append(token)
    if current:
        records.append(current)
    return records


def parse_one_sighting_record(record):
    try:
        effort_index = next(i for i, value in enumerate(record) if str(value).upper() in {"ON", "OFF"})
    except StopIteration:
        return None, "missing_effort_status"
    left = record[:effort_index]
    right = record[effort_index + 1:]
    effort_status = record[effort_index]
    if len(left) < 6:
        return None, "too_few_fields_before_effort_status"
    if len(right) < 5:
        return None, "too_few_fields_after_effort_status"
    date_raw = left[0]
    stage_no = left[1] if len(left) > 1 else None
    time_raw = left[2] if len(left) > 2 else None
    herd_size = left[3] if len(left) > 3 else None
    area = left[4] if len(left) > 4 else None
    if len(left) >= 7:
        beaufort = left[5]
        psd_raw = left[6]
    else:
        beaufort = None
        psd_raw = left[5]
    source_type = right[0]
    northing = right[1]
    easting = right[2]
    season = right[3]
    boat_assoc = right[4]
    primary_secondary = right[5] if len(right) >= 6 else None
    parsed = [
        date_raw, stage_no, time_raw, herd_size, area, beaufort, psd_raw,
        effort_status, source_type, northing, easting, season, boat_assoc,
        primary_secondary,
    ]
    return parsed, None


def parse_sighting_records(doc, start_page, end_page):
    raw_records = split_sighting_records(doc, start_page, end_page)
    records = []
    bad_records = []
    for record in raw_records:
        parsed, error = parse_one_sighting_record(record)
        if parsed is None:
            bad_records.append({"error": error, "tokens": record})
        else:
            records.append(parsed)
    return records, bad_records


def parse_date_series(values):
    text_values = values.astype(str).str.strip()
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    formats = ["%d-%b-%y", "%d-%b-%Y", "%d/%m/%y", "%d/%m/%Y"]
    for date_format in formats:
        missing = parsed.isna()
        if not missing.any():
            break
        parsed.loc[missing] = pd.to_datetime(text_values.loc[missing], format=date_format, errors="coerce")
    return parsed


def add_common_fields(df, period, source_file):
    df = df.copy()
    df["date"] = parse_date_series(df["date_raw"])
    df["calendar_year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["monitoring_period"] = period
    df["monitoring_start_year"] = infer_start_year(period)
    df["source_file"] = source_file
    if "area" in df.columns:
        df["area"] = df["area"].astype(str).str.strip().str.upper()
        df["area"] = df["area"].replace(AREA_ALIASES)
        df["area_code"] = df["area"].map(AREA_CODE_MAP).fillna(df["area"])
    return df


def standardize_survey(df, period, source_file):
    df = add_common_fields(df, period, source_file)
    for column in ["beaufort", "effort_km"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def standardize_sightings(df, period, source_file):
    df = add_common_fields(df, period, source_file)
    for column in ["stage_no", "herd_size", "beaufort", "northing", "easting"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["psd"] = pd.to_numeric(df["psd_raw"], errors="coerce")
    df["boat_assoc"] = (
        df["boat_assoc"].astype(str).str.upper().str.replace("-", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True).str.strip()
    )
    return df


def extract_one_pdf(pdf_path):
    period = infer_period_from_filename(pdf_path)
    pages = find_appendix_pages(pdf_path)
    doc = fitz.open(pdf_path)
    survey_start = pages["survey_start"]
    survey_end = pages["survey_end"]
    sighting_start = pages["sighting_start"]
    sighting_end = pages["sighting_end"]
    result = {
        "source_file": pdf_path.name,
        "monitoring_period": period,
        "page_count": pages["page_count"],
        "survey_start_page": survey_start + 1 if survey_start is not None else None,
        "survey_end_page": survey_end + 1 if survey_end is not None else None,
        "sighting_start_page": sighting_start + 1 if sighting_start is not None else None,
        "sighting_end_page": sighting_end + 1 if sighting_end is not None else None,
        "status": "ok",
        "error": None,
    }
    try:
        if survey_start is None or survey_end is None:
            raise RuntimeError("Survey appendix pages could not be detected.")
        if sighting_start is None or sighting_end is None:
            raise RuntimeError("Sighting appendix pages could not be detected.")
        survey_records, bad_survey = parse_survey_records(doc, survey_start, survey_end)
        sighting_records, bad_sightings = parse_sighting_records(doc, sighting_start, sighting_end)
        survey_df = pd.DataFrame(survey_records, columns=SURVEY_COLUMNS)
        sighting_df = pd.DataFrame(sighting_records, columns=SIGHTING_COLUMNS)
        survey_df = standardize_survey(survey_df, period, pdf_path.name)
        sighting_df = standardize_sightings(sighting_df, period, pdf_path.name)
        result.update({
            "survey_rows": len(survey_df),
            "sighting_rows": len(sighting_df),
            "bad_survey_rows": len(bad_survey),
            "bad_sighting_rows": len(bad_sightings),
            "missing_survey_dates": int(survey_df["date"].isna().sum()),
            "missing_sighting_dates": int(sighting_df["date"].isna().sum()),
            "missing_sighting_coordinates": int(sighting_df[["northing", "easting"]].isna().any(axis=1).sum()),
        })
        return survey_df, sighting_df, result, bad_survey, bad_sightings
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        return pd.DataFrame(), pd.DataFrame(), result, [], []


def build_area_period_model_data(survey_df, sighting_df):
    key = ["monitoring_period", "monitoring_start_year", "area", "area_code"]
    effort = (
        survey_df.dropna(subset=["monitoring_period", "area_code"])
        .groupby(key, as_index=False)
        .agg(
            survey_effort_km=("effort_km", "sum"),
            survey_segments=("effort_km", "size"),
            survey_days=("date", "nunique"),
            mean_beaufort=("beaufort", "mean"),
        )
    )
    sight = sighting_df.dropna(subset=["monitoring_period", "area_code"]).copy()
    sight["_status"] = sight["effort_status"].astype(str).str.upper()
    sight_on = sight[sight["_status"] == "ON"]
    all_counts = (
        sight.groupby(key, as_index=False)
        .agg(
            sighting_count_all=("date", "size"),
            off_effort_sightings=("_status", lambda x: int((x == "OFF").sum())),
            fishing_boat_assoc=("boat_assoc", lambda x: int((x.astype(str).str.upper() != "NONE").sum())),
        )
    )
    on_counts = (
        sight_on.groupby(key, as_index=False)
        .agg(
            on_effort_sightings=("date", "size"),
            on_dolphin_count=("herd_size", "sum"),
            on_mean_herd_size=("herd_size", "mean"),
        )
    )
    model_df = effort.merge(all_counts, on=key, how="left").merge(on_counts, on=key, how="left")
    fill_zero_columns = [
        "sighting_count_all", "off_effort_sightings", "fishing_boat_assoc",
        "on_effort_sightings", "on_dolphin_count",
    ]
    for column in fill_zero_columns:
        model_df[column] = model_df[column].fillna(0)
    model_df["on_mean_herd_size"] = model_df["on_mean_herd_size"].fillna(0)
    model_df["encounter_rate_per_100_km"] = (
        model_df["on_effort_sightings"] / model_df["survey_effort_km"] * 100
    )
    model_df["dolphin_rate_per_100_km"] = (
        model_df["on_dolphin_count"] / model_df["survey_effort_km"] * 100
    )
    return model_df.sort_values(["monitoring_start_year", "area_code"]).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=str, default="raw_pdfs")
    parser.add_argument("--output-dir", type=str, default="processed")
    parser.add_argument("--pattern", type=str, default="*.pdf")
    parser.add_argument("--exclude", type=str, nargs="*", default=[])
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(input_dir.glob(args.pattern))
    if args.exclude:
        pdf_paths = [p for p in pdf_paths if not any(x in p.name for x in args.exclude)]
        print(f"Excluding {args.exclude} -> {len(pdf_paths)} PDFs remain")
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in {input_dir} with pattern {args.pattern}")

    all_survey = []
    all_sightings = []
    quality_rows = []
    bad_rows = []

    for pdf_path in pdf_paths:
        survey_df, sighting_df, quality, bad_survey, bad_sightings = extract_one_pdf(pdf_path)
        quality_rows.append(quality)
        if not survey_df.empty:
            all_survey.append(survey_df)
        if not sighting_df.empty:
            all_sightings.append(sighting_df)
        for item in bad_survey:
            bad_rows.append({"source_file": pdf_path.name, "table": "survey", **item})
        for item in bad_sightings:
            bad_rows.append({"source_file": pdf_path.name, "table": "sighting", **item})
        print(f"{pdf_path.name}: {quality['status']}, survey={quality.get('survey_rows', 0)}, sightings={quality.get('sighting_rows', 0)}")

    quality_df = pd.DataFrame(quality_rows)
    quality_df.to_csv(output_dir / "extraction_quality_summary.csv", index=False, encoding="utf-8-sig")
    quality_df.to_csv(output_dir / "appendix_page_detection.csv", index=False, encoding="utf-8-sig")

    if bad_rows:
        pd.DataFrame(bad_rows).to_csv(output_dir / "bad_records_for_review.csv", index=False, encoding="utf-8-sig")

    if all_survey:
        survey_all = pd.concat(all_survey, ignore_index=True)
        survey_all.to_csv(output_dir / "cwd_survey_effort_clean.csv", index=False, encoding="utf-8-sig")
    else:
        survey_all = pd.DataFrame()

    if all_sightings:
        sightings_all = pd.concat(all_sightings, ignore_index=True)
        sightings_all.to_csv(output_dir / "cwd_sightings_clean.csv", index=False, encoding="utf-8-sig")
    else:
        sightings_all = pd.DataFrame()

    if not survey_all.empty and not sightings_all.empty:
        model_df = build_area_period_model_data(survey_all, sightings_all)
        model_df.to_csv(output_dir / "cwd_area_period_model_data.csv", index=False, encoding="utf-8-sig")

    print(f"Output directory: {output_dir}")
    print(f"PDF files processed: {len(pdf_paths)}")
    print(f"Survey rows: {len(survey_all)}")
    print(f"Sighting rows: {len(sightings_all)}")


if __name__ == "__main__":
    main()
