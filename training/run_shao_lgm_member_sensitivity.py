"""Compare vegetation under ensemble-mean climate with mean member predictions."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
from netCDF4 import Dataset

from paleoveg.bioclim import derive_bioclimatic_variables
from paleoveg.model_loader import load_model
from paleoveg.predictor import CLASS_NAMES, predict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "training/results/shao_lgm_experiment"
MEMBER_CLIMATE = Path("/tmp/paleoveg_shao_lgm_climate")
MODEL = ROOT / "training/models/predictor_set_comparison/full_bioclim_model.pkl.bz2"
MODELS = ["CNRM-CM5", "FGOALS-g2", "IPSL-CM5A-LR", "MIROC-ESM", "MPI-ESM-P", "MRI-CGCM3"]
FEATURES = ["bio1", "bio4", "bio5", "bio6", "bio7", "bio8", "bio9", "bio10", "bio11", "bio12", "bio13", "bio14", "bio15", "bio16", "bio17", "bio18", "bio19"]


def read_member(variable, model):
    with Dataset(MEMBER_CLIMATE / f"{variable}_{model}_1deg_monclim.nc") as ds:
        return np.ma.filled(ds.variables[variable][:], np.nan), ds.variables["lat"][:], ds.variables["lon"][:]


def read_ensemble_prediction(state):
    with Dataset(OUT / f"paleoveg_{state}.nc") as ds:
        return np.ma.filled(ds.variables["probability"][:], np.nan)


def main():
    with Dataset(ROOT / "training/data/shao_lgm/PMIP_1deg_no_co2_correction.nc") as ds:
        shao = np.ma.filled(ds.variables["landuse"][:], np.nan)
    land = np.nansum(shao[1:12], axis=0) > 0
    model = load_model(MODEL)
    member_areas = []
    member_changes = []
    for name in MODELS:
        tas, lat, lon = read_member("tas", name)
        tmin, _, _ = read_member("tasmin", name)
        tmax, _, _ = read_member("tasmax", name)
        pr, _, _ = read_member("pr", name)
        bio = derive_bioclimatic_variables(tas.transpose(1, 2, 0) - 273.15, tmin.transpose(1, 2, 0) - 273.15, tmax.transpose(1, 2, 0) - 273.15, pr.transpose(1, 2, 0))
        valid = land & np.isfinite(bio).all(axis=-1)
        frame = pd.DataFrame(bio[valid], columns=FEATURES)
        no = predict(frame, model=model, c3_c4_correction=False).to_numpy()
        yes = predict(frame, model=model, c3_c4_correction=True, co2_ppm=185).to_numpy()
        weights = np.cos(np.deg2rad(lat))[:, None] * np.ones((1, len(lon)))
        fractions = lambda probabilities: np.array([np.sum(probabilities[:, i] * weights[valid]) / np.sum(weights[valid]) for i in range(len(CLASS_NAMES))])
        no_area, yes_area = fractions(no), fractions(yes)
        member_areas.extend({"model": name, "state": state, "class": cls, "area_weighted_fraction": value}
                            for state, values in [("no_co2", no_area), ("185ppm", yes_area)]
                            for cls, value in zip(CLASS_NAMES, values))
        member_changes.append(yes_area - no_area)
    data = pd.DataFrame(member_areas)
    data.to_csv(OUT / "member_area_fractions.csv", index=False)
    mean_member = data.groupby(["state", "class"], sort=False).area_weighted_fraction.mean().unstack("class").reindex(columns=CLASS_NAMES)
    weights = np.cos(np.deg2rad(lat))[:, None] * np.ones((1, len(lon)))
    ensemble = {}
    for state in ["no_co2", "185ppm"]:
        probabilities = read_ensemble_prediction(state)
        valid = land & np.isfinite(probabilities).all(axis=0)
        ensemble[state] = np.array([np.sum(probabilities[i, valid] * weights[valid]) / np.sum(weights[valid]) for i in range(len(CLASS_NAMES))])
    metrics = []
    for state in ["no_co2", "185ppm"]:
        difference = mean_member.loc[state].to_numpy() - ensemble[state]
        metrics.append({"state": state, "mean_absolute_difference_percentage_points": float(np.abs(difference).mean() * 100), "maximum_absolute_difference_percentage_points": float(np.abs(difference).max() * 100)})
    mean_change = np.mean(member_changes, axis=0)
    ensemble_change = ensemble["185ppm"] - ensemble["no_co2"]
    metrics.append({"state": "co2_direction", "matching_class_response_directions": int(np.sum(np.sign(mean_change) == np.sign(ensemble_change)))})
    pd.DataFrame(metrics).to_csv(OUT / "member_sensitivity_metrics.csv", index=False)
    (OUT / "member_sensitivity_metadata.json").write_text(json.dumps({"models": MODELS, "comparison": "mean member area fractions versus prediction from ensemble-mean climate"}, indent=2))


if __name__ == "__main__":
    main()
