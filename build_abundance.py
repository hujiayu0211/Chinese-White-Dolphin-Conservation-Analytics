import argparse
from pathlib import Path
import pandas as pd

TABLE_6B = {
    2003: (188, 18, 84, 56, 30), 2004: (143, 9, 62, 51, 21),
    2005: (128, 7, 58, 42, 21), 2006: (113, 9, 54, 44, 6),
    2007: (130, 10, 60, 54, 6), 2008: (108, 11, 42, 43, 12),
    2009: (100, 5, 40, 43, 12), 2010: (86, 7, 35, 33, 11),
    2011: (88, 11, 39, 28, 10), 2012: (80, 4, 40, 17, 19),
    2013: (73, 3, 36, 23, 11), 2014: (87, 1, 24, 36, 26),
    2015: (65, 0, 10, 31, 24), 2016: (47, 0, 11, 27, 9),
    2017: (47, 0, 21, 16, 10), 2018: (32, 0, 6, 19, 7),
    2019: (52, 0, 4, 29, 19), 2020: (37, 0, 3, 19, 15),
    2021: (40, 0, 4, 24, 12),
}
AREAS = ["COMBINED", "NEL", "NWL", "WL", "SWL"]
BLUE = {("NEL", y) for y in range(2015, 2022)}
RED = {("SWL", y) for y in range(2003, 2010)}
SOURCE_FILE, SOURCE_TABLE = "Final_Report_2021_22.pdf", "Table 6b"
STUDY_MIN, STUDY_MAX = 2012, 2021


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="processed")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    recs = []
    for year, vals in TABLE_6B.items():
        assert vals[0] == sum(vals[1:]), f"Combined != sum of areas in {year}: {vals}"
        for area, v in zip(AREAS, vals):
            recs.append({
                "year": year, "area_code": area, "abundance": v,
                "in_study_window": STUDY_MIN <= year <= STUDY_MAX,
                "low_reliability_no_sighting": (area, year) in BLUE,
                "biennial_derived": (area, year) in RED,
                "source_file": SOURCE_FILE, "source_table": SOURCE_TABLE,
            })
    long = pd.DataFrame(recs)
    long.to_csv(out / "cwd_abundance_2003_2021_long.csv", index=False, encoding="utf-8-sig")
    (long.pivot(index="year", columns="area_code", values="abundance")[AREAS]
        .to_csv(out / "cwd_abundance_2003_2021_wide.csv", encoding="utf-8-sig"))
    print(f"abundance: {long.year.min()}-{long.year.max()}, all Combined==sum OK; "
          f"study window {STUDY_MIN}-{STUDY_MAX}; source {SOURCE_FILE} {SOURCE_TABLE}")


if __name__ == "__main__":
    main()
