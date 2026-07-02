# Spatial habitat-use results

On-effort georeferenced sightings: n = 1732. Surfaces are relative utilization (effort recorded by area, not grid), each block normalised.

## Annual sighting centroid (HK1980 m)

|   msy |      E |      N |
|------:|-------:|-------:|
|  2012 | 804723 | 815792 |
|  2013 | 804079 | 813401 |
|  2014 | 803450 | 812250 |
|  2015 | 803204 | 810913 |
|  2016 | 803092 | 810332 |
|  2017 | 803617 | 811062 |
|  2018 | 803455 | 812669 |
|  2019 | 803006 | 809024 |
|  2020 | 802711 | 809656 |
|  2021 | 802273 | 809776 |


Net centroid shift 2012→2021: ΔE=-2450 m, ΔN=-6016 m (≈ 6.5 km; westward + southward).

## 50% core-area size per block (km²)

| block                       |   n_sightings |   core_50pct_km2 |
|:----------------------------|--------------:|-----------------:|
| 2012-2015 (early / HZMB)    |           889 |             45   |
| 2016-2019 (3RS reclamation) |           550 |             36.2 |
| 2020-2022 (post)            |           293 |             26.3 |

## Share of on-effort sightings by area (%), by block

| block                       |   NEL |   NWL |   WL |   SWL |   DB |
|:----------------------------|------:|------:|-----:|------:|-----:|
| 2012-2015 (early / HZMB)    |   2.4 |  18.7 | 58.2 |  18   |  2.6 |
| 2016-2019 (3RS reclamation) |   0   |   8.4 | 62.9 |  25.8 |  1.3 |
| 2020-2022 (post)            |   0   |   2.7 | 75.4 |  21.5 |  0   |

## Figures

- `fig_kde_blocks.png` — utilization heatmaps per block (50%/95% contours)
- `fig_core_migration.png` — 50% core contours of all blocks + centroid track
- `fig_gam_surfaces.png` — spatial GAM intensity: early, late, difference
