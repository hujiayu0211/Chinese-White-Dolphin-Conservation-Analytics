# CWD habitat-use model results

Panel: 40 rows (core areas ['NEL', 'NWL', 'WL', 'SWL'], 10 monitoring periods). Response = on-effort sightings, offset = log(survey effort km).

## Overdispersion check

Poisson Pearson chi2 / df = **3.68** (over-dispersed -> Negative Binomial justified).

## Negative Binomial GLM (main)

`sightings ~ area + year + any_reclamation`, offset log(effort). alpha (dispersion) = 0.089; pseudo R2 = 0.241.

|                     |    coef |     IRR |   IRR_lo |   IRR_hi |      p |
|:--------------------|--------:|--------:|---------:|---------:|-------:|
| Intercept           | -5.0632 |  0.0063 |   0.0032 |   0.0124 | 0      |
| C(area_code)[T.NWL] |  1.9189 |  6.8138 |   3.6467 |  12.7316 | 0      |
| C(area_code)[T.WL]  |  3.8448 | 46.748  |  21.6204 | 101.079  | 0      |
| C(area_code)[T.SWL] |  2.3923 | 10.939  |   5.0708 |  23.5983 | 0      |
| year_c              | -0.1327 |  0.8757 |   0.8344 |   0.9191 | 0      |
| any_reclamation     | -0.1691 |  0.8444 |   0.5046 |   1.413  | 0.5197 |

## Non-linearity check (quadratic year)

year_c2 coef = 0.0112 (p = 0.233); little curvature.

## Robustness: West-Lantau core only (NEL excluded)

any_reclamation IRR = 0.699 (p = 0.125); year IRR = 0.902.

## NB-GAM (smooth year) - low power, descriptive only

Fitted GLMGam with a degree-3 B-spline on year (df=5), NB family (alpha=0.089). AIC = 294.0. With only 10 distinct years and 4 areas, treat the smooth as illustrative; the coordinate-level GAM on the 2,209 sightings is where a spatial GAM is properly powered.

## Figures

- `fig_encounter_rate_trend.png` - on-effort encounter rate by area
- `fig_abundance_trend.png` - annual abundance by area
- `fig_nb_irr.png` - NB GLM incidence rate ratios
