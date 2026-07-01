# Hong Kong Chinese White Dolphin — Habitat-Use Pipeline (2012–2022)

A reproducible pipeline that turns the Agriculture, Fisheries and Conservation
Department (AFCD) marine-mammal monitoring reports and the Environmental
Protection Department (EPD) marine water-quality archive into a clean,
model-ready panel — and runs the full analysis (effort-controlled trend model,
water-quality VIF diagnostics, spatial habitat-shift maps, and supplementary
tests) for studying changes in Chinese White Dolphin (*Sousa chinensis*) habitat
use in the western waters of Hong Kong.

> Prepared for **Environmental Awareness (2022/23, Semester 2)** as a coursework
> resubmission. The study window is the 10 AFCD monitoring periods **2012-13 to
> 2021-22** (the 2022-23 report is intentionally not used, matching the data
> available in that timeframe).

## Research question

Did the frequency, abundance, and spatial distribution of Chinese White Dolphins
change across 2012–2022, and is that change associated with major human activity
(large-scale reclamation) and environmental conditions? Every data source is
aligned on a common **area × monitoring-period** key so the analysis can control
for survey effort.

## Study design at a glance

- **Unit of analysis:** survey area × monitoring period.
- **Time:** AFCD monitoring periods run April–March; the study covers the 10
  periods 2012-13 to 2021-22. Calendar-year aggregation is deliberately avoided
  (it splits boundary years into partial cells).
- **Core dolphin areas:** North-West Lantau (NWL), West Lantau (WL), South-West
  Lantau (SWL); North-East Lantau (NEL) is included to document its collapse.
  Outer areas (Lamma, Po Toi, etc.) are kept in the raw tables but not modelled.

## Repository structure

```
.
├── README.md
├── LICENSE
├── extract_all_appendices_v2.py     # PDF → survey effort + sighting tables
├── build_abundance.py               # AFCD 2021-22 Table 6b → annual abundance (2003-2021)
├── aggregate_epd_water_quality.py   # EPD CSVs → area × period water quality
├── build_event_dummies.py           # reclamation / marine-park dummies + master panel (+ water quality)
├── model_panel.py                   # effort-controlled Negative-Binomial trend model + figures
├── model_panel_wq.py                # water-quality NB model + VIF diagnostics
├── model_spatial.py                 # KUD / spatial GAM habitat-shift maps
├── extra_analyses.py                # seasonal / group-size / change-point / fishery
├── raw_pdfs/                        # AFCD report PDFs (Final_Report_2012_13.pdf … 2021_22.pdf)
├── marine_water_quality_data/       # EPD marine-historical-YYYY-en.csv files
├── processed/                       # ALL generated CSVs (created on run)
└── result_figure/                   # ALL figures (fig_*.png) and result markdown (created on run)
```

`raw_pdfs/` and `marine_water_quality_data/` are inputs you provide. `processed/`
and `result_figure/` are created automatically.

## Quick start

```bash
pip install pymupdf pandas statsmodels patsy matplotlib tabulate pygam scipy pymannkendall

# put the input files in place:
#   raw_pdfs/                    -> the 10 AFCD report PDFs (2012-13 … 2021-22)
#   marine_water_quality_data/   -> the EPD marine-historical-*.csv files (2012–2022)

# run in order from the project root (no arguments needed):
python extract_all_appendices_v2.py     # raw_pdfs            -> processed/
python build_abundance.py               #                     -> processed/
python aggregate_epd_water_quality.py   # marine_water_...    -> processed/
python build_event_dummies.py           # processed/          -> processed/ (master panel, water quality merged)
python model_panel.py                   # processed/          -> result_figure/
python model_panel_wq.py                # processed/          -> result_figure/
python model_spatial.py                 # processed/          -> result_figure/
python extra_analyses.py                # processed/          -> result_figure/
```

Every script defaults to these folders, so no command-line arguments are needed
as long as the two input folders sit next to the scripts. Each script also
accepts `--input-dir` / `--output-dir` (etc.) if you want different paths.

## Data sources

| Source | What it provides | Coverage used |
|---|---|---|
| AFCD, *Monitoring of Marine Mammals in Hong Kong Waters*, annual reports — Appendix I (Survey Effort Database) and Appendix II (CWD Sighting Database) | Per-transect survey effort and per-sighting records (date, area, group size, coordinates, on/off-effort, fishing-gear association, season) | Reports 2012-13 to 2021-22 (10 reports) |
| AFCD 2021-22 report, **Table 6b** — Annual abundance estimates by survey area (line-transect distance sampling) | Annual abundance per area (NEL/NWL/WL/SWL + combined) | 2003–2021 (study window flagged 2012–2021) |
| EPD **Historical Marine Water Quality Data** (data.gov.hk) | Monthly station-level water quality (temperature, salinity, DO, turbidity, suspended solids, chlorophyll-a, nutrients) | Calendar files 2012–2022 |
| Government / official project sources | Reclamation and marine-park event dates (see *Event dates*) | — |

> The raw AFCD PDFs and EPD CSVs are public but are **not redistributed** here.
> Download them from the official sources and place them in `raw_pdfs/` and
> `marine_water_quality_data/`. EPD historical CSVs follow the URL pattern
> `https://cd.epic.epd.gov.hk/marinepsi/en/marinehistorical/marine-historical-{YEAR}-en.csv`.

## Pipeline

**1. `extract_all_appendices_v2.py`** — parses Appendix I and Appendix II from
each AFCD PDF (PyMuPDF), standardises, and concatenates across years.
Outputs `cwd_survey_effort_clean.csv`, `cwd_sightings_clean.csv`,
`cwd_area_period_model_data.csv`, plus an extraction-quality summary. Reads
`raw_pdfs/`, writes `processed/`.

**1b. `build_abundance.py`** — writes the annual abundance table (2003-2021) from
the AFCD 2021-22 report Table 6b, with `Combined == sum(areas)` checks and
blue/red source flags. Writes `processed/`.

**2. `aggregate_epd_water_quality.py`** — keeps surface-water samples, assigns
each to a monitoring period, maps EPD Water Control Zones to dolphin areas
(Southern zone restricted to the SW-Lantau / Soko stations), and aggregates to
area × period means. Reads `marine_water_quality_data/`, writes
`water_quality_by_area_period.csv` (+ zone audit + tidy long) to `processed/`.

**3. `build_event_dummies.py`** — builds 0/1 reclamation and marine-park dummies
by area × period and merges effort/encounter rate + annual abundance + event
dummies + water quality into `cwd_master_panel.csv`. Reads and writes
`processed/`. Water quality is merged by default.

**4. Models (read `processed/`, write `result_figure/`)**
- `model_panel.py` — Poisson overdispersion check → Negative-Binomial GLM
  (area FE + year trend + reclamation dummy) → quadratic-year and NEL-excluded
  robustness → NB-GAM. Figures: encounter-rate trend, abundance trend, IRR forest.
- `model_panel_wq.py` — adds standardised water-quality covariates with VIF
  diagnostics (exposes the salinity ↔ area confound). Figure: VIF chart.
- `model_spatial.py` — kernel utilization distributions (50%/95%), core-area
  migration contours, centroid trajectory, and a Poisson tensor-smooth spatial
  GAM. Figures: KDE blocks, core migration, GAM surfaces.
- `extra_analyses.py` — seasonal encounter rate, group-size trend, Pettitt /
  Mann-Kendall / segmented change-point, and fishing-gear association.

## Output datasets

### `cwd_master_panel.csv` (98 rows = 10 periods × area)
The main analysis table. Key columns: `monitoring_period`,
`monitoring_start_year`, `area`, `area_code`, `survey_effort_km`, `survey_days`,
`on_effort_sightings` (model response), `on_dolphin_count`, `on_mean_herd_size`,
`encounter_rate_per_100_km`, the event dummies
(`hzmb_construction`, `hzmb_post_open`, `rs3_reclamation`, `mp_brothers`,
`mp_sw_lantau`, `mp_south_lantau`), the composites (`any_reclamation`,
`any_marine_park`), `annual_abundance`, and the eight water-quality columns.
Recommended response: `on_effort_sightings` with `offset(log(survey_effort_km))`.

### `cwd_abundance_2003_2021_long.csv`
Annual abundance by area (long) with `low_reliability_no_sighting` (AFCD "blue"
cells: no/one on-effort sighting, i.e. effective local absence) and
`biennial_derived` (AFCD "red" cells, all pre-2010).

### `water_quality_by_area_period.csv`
Eight ecologically relevant parameters per area × period, plus an `n_samples`
coverage column.

## Key processing decisions and data-quality fixes

- **Monitoring-period, not calendar-year, aggregation** keeps every cell a full
  April–March survey year.
- **On-effort filtering:** encounter rate uses on-effort sightings only, matching
  the systematic survey effort in the offset; off-effort counts are kept separately.
- **Abundance from Table 6b:** read from the 2021-22 long-term trend table; each
  year's combined value was checked to equal the sum of the four areas.
- **Source typos normalised:** `SW LAMTAU` (2013-14) and `NW LAUTAU` (2012-13) are
  verbatim misprints in the PDFs, mapped to the correct area codes.
- **Two appendix layouts handled:** older reports omit the "HKCRP-AFCD" prefix,
  and the 2012-13 survey appendix has 9 columns (extra PHASE/TYPE) vs 7 later.
- **Detection limits preserved:** EPD values such as `<0.005` are kept as the
  numeric limit, not coerced to missing.
- **Surface water only** for the water-quality aggregation.

## Validation performed

- **Row-count regression:** after refactoring the parser, all ten reports
  reproduced identical row counts.
- **Independent record count:** the 2013-14 sighting appendix yields 317 records
  by an independent date-line count, matching the parser.
- **Against the report narrative:** the 2012-13 report states 251 on-effort
  sightings; extraction reproduces 251.
- **Against known ecology:** NE Lantau collapses to zero from 2015 (matching
  AFCD's published finding); coordinates fall within the HK1980 grid; salinity
  follows the expected Pearl-River plume gradient.

Totals for the 10-period window: **2,209 sightings**, **7,023 survey-effort
records**, master panel **98 rows**.

## Known limitations and caveats

- **Abundance ends in 2021** (2021-22 report). Do not impute a 2022 value; add the
  2022-23 report for a real 2022 figure.
- **Water-quality / habitat confound:** dolphins prefer the low-salinity, turbid
  plume water, so salinity/turbidity partly proxy *why dolphins are there* rather
  than human pressure. Treat water quality as a control / robustness variable only
  (salinity's VIF rises to ~19 once area fixed effects are added).
- **Coarse water-quality geography:** EPD zones do not match dolphin areas. The
  North-Western zone feeds both NWL and WL; the Southern zone is restricted to the
  SW-Lantau / Soko stations (`SOUTHERN_SWL_STATIONS`) to avoid dilution.
- **Event-study power:** NEL is effectively a single treated unit and the
  marine-park dummies turn on late. Use the dummies as a descriptive event-study
  alongside the effort-controlled trend, not as strict causal identification.
- **Spatial surfaces are relative intensity:** survey effort is recorded by area,
  not by grid cell, so each block is normalised to isolate spatial redistribution.

## Event dates (with sources)

| Event | Date | Area(s) | Source |
|---|---|---|---|
| HZMB construction began | 15 Dec 2009 | NEL (HKBCF island NE of HKIA) | HZMB / government records |
| HZMB opened to traffic | 24 Oct 2018 | NEL/NWL | Government records |
| 3RS reclamation began | 1 Aug 2016 | NEL/NWL (north of HKIA) | Airport Authority Hong Kong |
| 3RS land formation completed | ~2020 | NEL/NWL | Airport Authority Hong Kong |
| The Brothers Marine Park designated | Dec 2016 | NEL | AFCD (HZMB compensation) |
| Southwest Lantau Marine Park effective | 1 Apr 2020 | SWL | AFCD / HK Government Gazette |
| South Lantau Marine Park designated | Jun 2022 | SWL (Soko) | AFCD / HK Government Gazette |

> Causal timeline: NEL dolphins collapse to zero by 2015, **during** the HZMB
> reclamation period and **before** the 3RS reclamation and the Brothers Marine
> Park. The marine-park compensation post-dates the local disappearance.

## License

Code in this repository is released under the MIT License (see `LICENSE`). The
underlying AFCD and EPD data are © the Government of the Hong Kong SAR and are
**not** covered by that license; cite the original sources and observe the data
providers' terms of use. This repository contains processing/analysis code and
derived tables only.
