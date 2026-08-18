# IPCC AR6 atmospheric CO₂ observations

`co2_ipcc_ar6.csv` contains the 1,894 irregular CO₂ observations extracted
from column 1 (age) and column 2 (CO₂) of `fig2_4a_main_figure_data.csv`.
No observations were resampled or removed. The source age is retained, and
`age_ka_bp` was calculated as `source_age_kyr_before_2000 - 0.05` so that BP
refers to 1950. The duplicate source age 0.277 is deliberately retained.

Source SHA-256:
`8d473c3b67bdd26e395bc335096a99a15630cececa738010a61c2bedeb67f859`

Data citation:

> Ahn, J. (2023). Chapter 2 of the Working Group I Contribution to the IPCC
> Sixth Assessment Report – data for Figure 2.4 (v20221219). NERC EDS Centre
> for Environmental Data Analysis. https://doi.org/10.5285/60eeb3cce51a457cb5ee1c577a0c8674

The source is licensed under Creative Commons Attribution 4.0 International.
CEDA additionally requests citation of the IPCC report chapter and the related
source publications listed in the dataset catalogue. See `LICENSE.md` and the
[CEDA catalogue record](https://catalogue.ceda.ac.uk/uuid/60eeb3cce51a457cb5ee1c577a0c8674/).

Report chapter:

> Gulev, S.K., et al. (2021). Changing State of the Climate System. In
> *Climate Change 2021: The Physical Science Basis*, pp. 287–422.
> https://doi.org/10.1017/9781009157896.004

Underlying Antarctic CO₂ compilation:

> Bereiter, B., Eggleston, S., Schmitt, J., Nehrbass-Ahles, C., Stocker, T.F.,
> Fischer, H., Kipfstuhl, S., & Chappellaz, J. (2015). Revision of the EPICA
> Dome C CO₂ record from 800 to 600-kyr before present. *Geophysical Research
> Letters*. https://doi.org/10.1002/2014GL061957

Regenerate the compact file from the downloaded CEDA source with:

```bash
python scripts/prepare_co2_data.py fig2_4a_main_figure_data.csv paleoveg/data/co2/co2_ipcc_ar6.csv
```
