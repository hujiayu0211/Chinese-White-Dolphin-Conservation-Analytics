# Water-quality NB model + VIF diagnostics

Core areas ['NEL', 'NWL', 'WL', 'SWL'], 40 rows. WQ standardised (per 1 SD). total_inorganic_nitrogen dropped a priori (r=-0.92 with salinity).

## VIF among water-quality variables only

| variable                |     VIF |
|:------------------------|--------:|
| temperature_z           | 2.25961 |
| salinity_z              | 2.20067 |
| suspended_solids_z      | 2.0799  |
| chlorophyll_a_z         | 2.01217 |
| ammonia_nitrogen_z      | 1.66747 |
| dissolved_oxygen_mg_l_z | 1.3442  |
| turbidity_z             | 1.32324 |

## VIF with area fixed effects + year added

High VIF on salinity here is the area/plume confound: within the four areas salinity is almost constant, so it is largely a linear combination of the area dummies.

| variable                |      VIF |
|:------------------------|---------:|
| salinity_z              | 19.2772  |
| C(area_code)[T.NWL]     | 12.5082  |
| C(area_code)[T.WL]      | 12.5082  |
| year_c                  |  7.72931 |
| C(area_code)[T.SWL]     |  5.69582 |
| dissolved_oxygen_mg_l_z |  5.05623 |
| ammonia_nitrogen_z      |  4.49262 |
| temperature_z           |  3.59926 |
| suspended_solids_z      |  2.94898 |
| chlorophyll_a_z         |  2.8149  |
| turbidity_z             |  1.67802 |

## Parsimonious WQ set kept (VIF<=5): ['temperature_z', 'salinity_z', 'suspended_solids_z', 'chlorophyll_a_z', 'ammonia_nitrogen_z', 'dissolved_oxygen_mg_l_z', 'turbidity_z']

## NB model comparison (response = on-effort sightings, offset log effort)

- M0 area+year: year IRR = 0.870, pseudo-R2 = 0.240
- M1 +reclamation: year IRR = 0.876, pseudo-R2 = 0.241
- M2 +water quality: year IRR = 0.861, pseudo-R2 = 0.248


### M2 full table (IRR per 1 SD for WQ)

|                         |     IRR |     lo |       hi |      p |
|:------------------------|--------:|-------:|---------:|-------:|
| Intercept               |  0.0085 | 0.0031 |   0.0237 | 0      |
| C(area_code)[T.NWL]     |  4.5179 | 1.5541 |  13.134  | 0.0056 |
| C(area_code)[T.WL]      | 31.2601 | 9.3822 | 104.154  | 0      |
| C(area_code)[T.SWL]     |  9.9432 | 3.4979 |  28.2654 | 0      |
| year_c                  |  0.8606 | 0.7664 |   0.9664 | 0.0111 |
| any_reclamation         |  0.8785 | 0.5084 |   1.518  | 0.6424 |
| temperature_z           |  0.9625 | 0.7801 |   1.1877 | 0.7218 |
| salinity_z              |  0.7937 | 0.4909 |   1.2832 | 0.3458 |
| suspended_solids_z      |  0.9694 | 0.8058 |   1.1663 | 0.7421 |
| chlorophyll_a_z         |  1.1535 | 0.9607 |   1.385  | 0.1259 |
| ammonia_nitrogen_z      |  0.9825 | 0.7609 |   1.2686 | 0.8924 |
| dissolved_oxygen_mg_l_z |  0.8939 | 0.6914 |   1.1556 | 0.3919 |
| turbidity_z             |  0.9914 | 0.8625 |   1.1395 | 0.9029 |

## Reading the water-quality coefficients

WQ enters as a control: the IRRs are per-1-SD within-panel change after area and year are accounted for. Because salinity barely varies within an area over time (see VIF), its coefficient is weakly identified and should not be read as a causal salinity effect on dolphins. The key check is whether the year trend is robust to adding WQ: compare M0/M1/M2 above.
