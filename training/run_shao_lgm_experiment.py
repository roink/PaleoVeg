"""Matched six-model PMIP3 LGM PaleoVeg behavioural experiment."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import shapefile
from netCDF4 import Dataset
from paleoveg.bioclim import derive_bioclimatic_variables
from paleoveg.model_loader import load_model
from paleoveg.predictor import predict, CLASS_NAMES
from paleoveg_training import LAND_USE_COLORS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "training/results/shao_lgm_experiment"
CLIMATE = OUT / "climate"
SHAO = ROOT / "training/data/shao_lgm"
MODEL = ROOT / "training/models/predictor_set_comparison/full_bioclim_model.pkl.bz2"
FIGURES = ROOT / "figures"
CLASS_CODES = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12])
SHORT_NAMES = ["ENF", "EBF", "DNF", "DBF", "MF", "WL", "WGL", "CSL", "OSL", "GL", "BG"]
CLASS_COLORS = [LAND_USE_COLORS[int(code)] for code in CLASS_CODES]
PRESENT_DAY_COASTLINE = (
    ROOT / "training/data/natural_earth/ne_110m_coastline.shp"
)

def read(name):
    with Dataset(CLIMATE / f"ensemble_{name}_1deg_monclim.nc") as ds:
        return np.ma.filled(ds.variables[name][:], np.nan), ds.variables['lat'][:], ds.variables['lon'][:]


def area_fractions(values, area):
    """Return area-weighted mean probability for each retained class."""
    return np.array([np.nansum(values[:, i] * area) / np.nansum(area) for i in range(len(CLASS_NAMES))])


def modern_area_fractions():
    """Satellite target fractions on the complete-case 8 km training grid."""
    table = pd.read_parquet(ROOT / "training/data/processed/paleoveg_training.parquet", columns=["lat", "land_use_type"])
    weights = np.cos(np.deg2rad(table["lat"].to_numpy()))
    return np.array([
        weights[table["land_use_type"].to_numpy() == code].sum() / weights.sum()
        for code in CLASS_CODES
    ])


def write_probability_cube(path, probabilities, land, lat, lon):
    cube = np.full((len(CLASS_NAMES), len(lat), len(lon)), np.nan)
    cube[:, land] = probabilities.T
    with Dataset(path, "w") as ds:
        ds.createDimension("class", len(CLASS_NAMES))
        ds.createDimension("lat", len(lat))
        ds.createDimension("lon", len(lon))
        ds.createVariable("class_code", "i2", ("class",))[:] = CLASS_CODES
        ds.createVariable("lat", "f4", ("lat",))[:] = lat
        ds.createVariable("lon", "f4", ("lon",))[:] = lon
        probability = ds.createVariable("probability", "f4", ("class", "lat", "lon"), zlib=True, fill_value=np.nan)
        probability.long_name = "PaleoVeg class probability"
        probability[:] = cube


def global_area_figure(data):
    """Analogue of Shao et al. Fig. 6 with a matched LGM forcing."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    order = ["modern_avhrr", "shao_no_co2", "shao_185ppm", "paleoveg_no_co2", "paleoveg_185ppm"]
    labels = ["Modern\nAVHRR", "Shao\nno CO$_2$", "Shao\n185 ppm", "PaleoVeg\nno CO$_2$", "PaleoVeg\n185 ppm"]
    colours = ["#555555", "#bdbdbd", "#737373", "#78a6c8", "#0072B2"]
    pivot = data.pivot(index="class", columns="configuration", values="area_weighted_fraction").reindex(index=CLASS_NAMES, columns=order)
    x = np.arange(len(CLASS_NAMES))
    offsets = np.linspace(-0.32, 0.32, len(order))
    fig, ax = plt.subplots(figsize=(13.2, 6.5))
    for i in range(len(CLASS_NAMES)):
        if i % 2 == 0:
            ax.axvspan(i - 0.5, i + 0.5, color="0.95", zorder=0)
    for offset, key, label, colour in zip(offsets, order, labels, colours):
        ax.bar(x + offset, pivot[key].to_numpy() * 100, width=0.15, color=colour, label=label, zorder=3)
    ax.set_xticks(x, SHORT_NAMES)
    ax.set_ylabel("Area-weighted fraction of terrestrial grid (%)")
    ax.set_ylim(0, max(32, np.ceil(pivot.to_numpy().max() * 100 / 5) * 5 + 5))
    ax.grid(axis="y", color="0.88", linewidth=0.6, zorder=0)
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.16), frameon=False)
    ax.set_title("Global vegetation-class area fractions under matched LGM forcing", fontweight="bold")
    fig.tight_layout()
    for suffix, kwargs in [("pdf", {}), ("png", {"dpi": 300})]:
        fig.savefig(FIGURES / f"fig09_lgm_global_area.{suffix}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def map_figure(yes, land, lat, lon):
    """Provide one compact example of the corrected LGM reconstruction."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    yes_cube = np.full((len(lat), len(lon)), np.nan)
    yes_cube[land] = np.argmax(yes, axis=1) + 1
    cmap = ListedColormap(CLASS_COLORS)
    norm = BoundaryNorm(np.arange(0.5, len(CLASS_NAMES) + 1.5), cmap.N)
    # PMIP3/Shao longitudes run 0--360 degrees. Reorder to the conventional
    # -180--180 display so that maps are continuous rather than split at Greenwich.
    display_lon = np.where(lon > 180, lon - 360, lon)
    order = np.argsort(display_lon)
    display_lon = display_lon[order]
    yes_cube = yes_cube[:, order]
    fig, ax = plt.subplots(figsize=(12.6, 5.0), constrained_layout=True)
    extent = [float(display_lon.min()), float(display_lon.max() + 1), float(lat.min()), float(lat.max() + 1)]
    image = ax.imshow(yes_cube, origin="lower", extent=extent, cmap=cmap, norm=norm, interpolation="nearest", aspect="auto")
    # Present-day coastline only: a readable geographic reference, not LGM geography.
    if not PRESENT_DAY_COASTLINE.is_file():
        raise FileNotFoundError(
            f"Missing vendored Natural Earth coastline: {PRESENT_DAY_COASTLINE}"
        )
    for shape in shapefile.Reader(str(PRESENT_DAY_COASTLINE)).shapes():
        points = np.asarray(shape.points)
        starts = list(shape.parts) + [len(points)]
        for start, end in zip(starts[:-1], starts[1:]):
            segment = points[start:end]
            # Do not draw an artificial line across the map at the dateline.
            jumps = np.where(np.abs(np.diff(segment[:, 0])) > 180)[0]
            boundaries = np.r_[0, jumps + 1, len(segment)]
            for left, right in zip(boundaries[:-1], boundaries[1:]):
                ax.plot(segment[left:right, 0], segment[left:right, 1], color="0.15", linewidth=0.30, alpha=0.75, zorder=5)
    # Coastline vertices can extend a fraction beyond the conventional bounds.
    # Restore the intended global plotting domain after overlaying them.
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_title("PaleoVeg dominant class under LGM climate with the 185 ppm CO$_2$ correction", fontweight="bold")
    ax.set_xlabel("Longitude (°)"); ax.set_ylabel("Latitude (°)")
    ax.set_xticks(np.arange(-180, 181, 60)); ax.set_yticks(np.arange(-90, 91, 30))
    cbar = fig.colorbar(image, ax=ax, location="right", shrink=0.92, ticks=np.arange(1, 12))
    cbar.ax.set_yticklabels(SHORT_NAMES)
    cbar.set_label("Dominant class")
    for suffix, kwargs in [("pdf", {}), ("png", {"dpi": 300})]:
        fig.savefig(FIGURES / f"fig10_lgm_maps.{suffix}", bbox_inches="tight", **kwargs)
    plt.close(fig)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tas, lat, lon = read('tas'); tmin, _, _ = read('tasmin'); tmax, _, _ = read('tasmax'); pr, _, _ = read('pr')
    # CDO writes time, latitude, longitude. Convert K to C; precipitation is monthly mm.
    bio = derive_bioclimatic_variables(tas.transpose(1,2,0)-273.15, tmin.transpose(1,2,0)-273.15, tmax.transpose(1,2,0)-273.15, pr.transpose(1,2,0))
    with Dataset(SHAO / 'PMIP_1deg_no_co2_correction.nc') as ds:
        shao_no = np.ma.filled(ds.variables['landuse'][:], np.nan)
    with Dataset(SHAO / 'PMIP_1deg_co2_correction.nc') as ds:
        shao_yes = np.ma.filled(ds.variables['landuse'][:], np.nan)
    # The archive has 13 layers: water, the 11 retained vegetation classes,
    # and unassigned.  The retained vegetation classes are layers 1--11.
    shao_no = shao_no[1:12]
    shao_yes = shao_yes[1:12]
    land = (np.nansum(shao_no, axis=0) > 0) & np.isfinite(bio).all(axis=-1)
    frame = pd.DataFrame(bio[land], columns=['bio1','bio4','bio5','bio6','bio7','bio8','bio9','bio10','bio11','bio12','bio13','bio14','bio15','bio16','bio17','bio18','bio19'])
    model = load_model(MODEL)
    no = predict(frame, model=model, c3_c4_correction=False).to_numpy()
    yes = predict(frame, model=model, c3_c4_correction=True, co2_ppm=185).to_numpy()
    area = np.cos(np.deg2rad(lat))[:,None] * np.ones((1,len(lon)))
    shao_no_values = shao_no.transpose(1, 2, 0)[land]
    shao_yes_values = shao_yes.transpose(1, 2, 0)[land]
    weights = area[land]
    fractions = {
        "modern_avhrr": modern_area_fractions(),
        "shao_no_co2": area_fractions(shao_no_values, weights),
        "shao_185ppm": area_fractions(shao_yes_values, weights),
        "paleoveg_no_co2": area_fractions(no, weights),
        "paleoveg_185ppm": area_fractions(yes, weights),
    }
    rows = [{"configuration": label, "class": cls, "area_weighted_fraction": value}
            for label, values in fractions.items() for cls, value in zip(CLASS_NAMES, values)]
    data = pd.DataFrame(rows)
    data.to_csv(OUT / "global_area_fractions.csv", index=False)
    metrics = []
    for state in ("no_co2", "185ppm"):
        p, s = fractions[f"paleoveg_{state}"], fractions[f"shao_{state}"]
        metrics.append({
            "state": state,
            "class_fraction_pearson_r": float(np.corrcoef(p, s)[0, 1]),
            "mean_absolute_difference_percentage_points": float(np.abs(p - s).mean() * 100),
        })
    shao_change = fractions["shao_185ppm"] - fractions["shao_no_co2"]
    paleo_change = fractions["paleoveg_185ppm"] - fractions["paleoveg_no_co2"]
    metrics.append({
        "state": "co2_directional_response",
        "mean_absolute_difference_percentage_points": float(np.abs(shao_change - paleo_change).mean() * 100),
        "matching_class_response_directions": int(np.sum(np.sign(shao_change) == np.sign(paleo_change))),
    })
    pd.DataFrame(metrics).to_csv(OUT / "comparison_metrics.csv", index=False)
    write_probability_cube(OUT / "paleoveg_no_co2.nc", no, land, lat, lon)
    write_probability_cube(OUT / "paleoveg_185ppm.nc", yes, land, lat, lon)
    global_area_figure(data)
    map_figure(yes, land, lat, lon)
    (OUT / "metadata.json").write_text(json.dumps({
        "models": ["CNRM-CM5", "FGOALS-g2", "IPSL-CM5A-LR", "MIROC-ESM", "MPI-ESM-P", "MRI-CGCM3"],
        "co2_ppm": 185,
        "grid": "1 degree",
        "land_cells": int(land.sum()),
        "method": "monthly fields interpolated to 1 degree, ensemble averaged, then converted to BIOCLIM",
    }, indent=2))
if __name__=='__main__': main()
