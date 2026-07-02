# Extension analyses (seasonal / group size / change-point / fishery)

Core areas ['NEL', 'NWL', 'WL', 'SWL'], on-effort sightings, monitoring periods 2012-13 to 2021-22.

## 1. Seasonal analysis

| season   |   on_sightings |   effort_km |   enc_per_100km |
|:---------|---------------:|------------:|----------------:|
| SPRING   |            318 |        7084 |            4.49 |
| SUMMER   |            544 |        6953 |            7.82 |
| AUTUMN   |            493 |        7998 |            6.16 |
| WINTER   |            335 |        7424 |            4.51 |

Encounter rate peaks in **SUMMER** (7.82) and is lowest in **SPRING** (4.49 per 100 km).

## 2. Group-size trend

|   monitoring_start_year |   mean |   median |   size |
|------------------------:|-------:|---------:|-------:|
|                    2012 |   3.11 |        2 |    249 |
|                    2013 |   3.16 |        2 |    235 |
|                    2014 |   4.19 |        3 |    181 |
|                    2015 |   3.79 |        3 |    199 |
|                    2016 |   3.42 |        2 |    160 |
|                    2017 |   3.08 |        2 |    144 |
|                    2018 |   3.31 |        2 |    105 |
|                    2019 |   3.44 |        2 |    125 |
|                    2020 |   3.01 |        2 |    144 |
|                    2021 |   3.52 |        3 |    148 |


OLS slope = -0.006 dolphins/year (p = 0.795); Mann-Kendall on annual means: trend = **no trend**, p = 1.000, Sen's slope = -0.006.

Group size shows no significant time trend — i.e. the decline is driven by fewer encounters, not smaller groups.

## 3. Change-point test

- Mann-Kendall: trend = **decreasing**, p = 0.007, Sen's slope = -0.385/yr
- Pettitt single change-point at **2016** (p = 0.066)
- Segmented regression breakpoint at **2018**; slope before = -0.624, after = +0.170 per year


The break falls around 2016, within the HZMB-to-3RS reclamation window (2011-2020), consistent with reclamation-associated decline rather than a purely gradual trend.

## 4. Fishery association

|   monitoring_start_year |   sum |   size |   pct |
|------------------------:|------:|-------:|------:|
|                    2012 |    10 |    249 |   4   |
|                    2013 |    14 |    235 |   6   |
|                    2014 |     8 |    181 |   4.4 |
|                    2015 |     5 |    199 |   2.5 |
|                    2016 |     6 |    160 |   3.8 |
|                    2017 |     5 |    144 |   3.5 |
|                    2018 |     3 |    105 |   2.9 |
|                    2019 |     2 |    125 |   1.6 |
|                    2020 |     5 |    144 |   3.5 |
|                    2021 |    14 |    148 |   9.5 |


Mann-Kendall on the annual association rate: trend = **no trend**, p = 0.419, Sen's slope = -0.0016/yr. Base rate is low, so read this as indicative.

## Figures

- `fig_seasonal.png`  - encounter rate by season
- `fig_group_size.png` - mean herd size over time
- `fig_changepoint.png` - change-point in encounter rate
- `fig_fishery.png`   - fishing-gear association over time
