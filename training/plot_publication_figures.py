#!/usr/bin/env python3
"""Generate Figures 2--7 used by the PaleoVeg 1.0 manuscript."""

from __future__ import annotations

import bz2
import logging
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle
from sklearn.metrics import confusion_matrix

from paleoveg_training import CLASSES, FEATURES, configure_logging

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "training/results/predictor_set_comparison"
SPATIAL_RESULTS = ROOT / "training/results/spatial_validation_v1"
MODELS = ROOT / "training/models/predictor_set_comparison"
FIGURES = ROOT / "figures"
SHORT_NAMES = ["ENF", "EBF", "DNF", "DBF", "MF", "WL", "WGL", "CSL", "OSL", "GL", "BG"]
FULL_NAMES = [
    "Evergreen needleleaf forest", "Evergreen broadleaf forest",
    "Deciduous needleleaf forest", "Deciduous broadleaf forest",
    "Mixed forest", "Woodland", "Wooded grassland", "Closed shrubland",
    "Open shrubland", "Grassland", "Bare ground",
]
COLORS = {"shao_like_bio1_bio12": "#D55E00", "full_bioclim": "#0072B2"}


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def parse_tile(tile_id: str) -> tuple[int, int]:
    parts = tile_id.split("_")
    return int(parts[1][1:]), int(parts[2][1:])


def tile_rectangle(ax, tile_id: str, **kwargs) -> None:
    row, col = parse_tile(tile_id)
    ax.add_patch(Rectangle((-180 + 5 * col, -90 + 5 * row), 5, 5, **kwargs))


def format_world_axis(ax, title: str) -> None:
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(np.arange(-180, 181, 60))
    ax.set_yticks(np.arange(-90, 91, 30))
    ax.grid(color="0.85", linewidth=0.4)
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_title(title)


def split_map() -> None:
    manifest = pd.read_csv(SPATIAL_RESULTS / "spatial_split_manifest.csv")
    fig, ax = plt.subplots(figsize=(12, 6.2))
    for row in manifest.itertuples(index=False):
        color = "#E69F00" if row.split_group == "external_test" else "#B8C2CC"
        tile_rectangle(ax, row.outer_tile_id, facecolor=color, edgecolor="white", linewidth=0.15)
    format_world_axis(ax, "Spatial partition of valid 5° × 5° tiles")
    handles = [Rectangle((0, 0), 1, 1, color="#B8C2CC", label="Development (1,182 tiles)"), Rectangle((0, 0), 1, 1, color="#E69F00", label="External test (132 tiles)")]
    ax.legend(handles=handles, loc="lower left", frameon=True)
    save_figure(fig, "fig02_spatial_split")


def cv_performance() -> None:
    data = pd.read_csv(RESULTS / "metrics.csv")
    data = data[data["evaluation"] == "blocked_cv"]
    metrics = [("accuracy", "Accuracy"), ("balanced_accuracy", "Balanced accuracy"), ("macro_f1", "Macro F1"), ("multiclass_log_loss", "Multiclass log loss")]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for ax, (metric, label) in zip(axes.ravel(), metrics):
        values = [data.loc[data.configuration == config, metric].to_numpy() for config in CONFIG_ORDER]
        positions = [0, 1]
        bp = ax.boxplot(values, positions=positions, widths=0.5, patch_artist=True, showmeans=True, showfliers=False,
                        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": "black", "markersize": 6},
                        medianprops={"color": "black", "linewidth": 1.2})
        for patch_box, config in zip(bp["boxes"], CONFIG_ORDER):
            patch_box.set_facecolor(COLORS[config]); patch_box.set_alpha(0.75)
        for position, config, vals in zip(positions, CONFIG_ORDER, values):
            jitter = np.linspace(-0.08, 0.08, len(vals))
            ax.scatter(position + jitter, vals, s=20, color="black", zorder=3)
        ax.set_xticks(positions, ["BIO1 + BIO12", "17 BIOCLIM"])
        ax.set_ylabel(label)
        ax.grid(axis="y", color="0.88")
    fig.suptitle("Matched five-fold spatial validation", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "fig03_blocked_cv_comparison")


CONFIG_ORDER = ["shao_like_bio1_bio12", "full_bioclim"]


def shao_score_comparison() -> None:
    summary = pd.read_csv(RESULTS / "shao_goodness_cv_summary.csv")
    summary["class"] = summary["class"].astype(str)
    summary = summary[summary["class"] != "ensemble_mean"]
    published = pd.read_csv(RESULTS / "shao_model5_external_comparison.csv")
    published["class"] = published["class"].astype(str)
    published = published[published["class"] != "ensemble_mean"].drop_duplicates("class")
    fig, ax = plt.subplots(figsize=(12, 6.8))
    x = np.arange(len(CLASSES))
    # Subtle bands group the three comparison marks belonging to each class.
    for i in range(len(CLASSES)):
        if i % 2 == 0:
            ax.axvspan(i - 0.5, i + 0.5, color="0.94", zorder=0)
    shao_values = [float(published.loc[published["class"] == str(code), "shao_2018_model_5_score"].iloc[0]) for code in CLASSES]
    ax.scatter(x - 0.22, shao_values, marker="s", s=48, color="#555555", label="Shao et al. model 5 (published)", zorder=4)
    for offset, config, label in [
        (0.0, "shao_like_bio1_bio12", "BIO1 + BIO12 RF (blocked CV)"),
        (0.22, "full_bioclim", "17-predictor RF (blocked CV)"),
    ]:
        part = summary[summary.configuration == config].set_index("class")
        means = np.array([part.loc[str(code), "mean"] for code in CLASSES])
        errors = np.array([part.loc[str(code), "std"] for code in CLASSES])
        ax.errorbar(x + offset, means, yerr=errors, fmt="o", capsize=3, color=COLORS[config], label=label)
    ax.set_xticks(x, SHORT_NAMES)
    ax.set_ylabel("Shao et al. Equation 3 goodness score")
    ax.set_ylim(0, 1.03)
    ax.grid(axis="y", color="0.90", linewidth=0.6)
    ax.legend(ncol=1, loc="lower right")
    ax.set_title("Class-wise goodness scores", fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "fig04_shao_goodness_scores")


def load_predictions(configuration: str) -> pd.DataFrame:
    return pd.read_parquet(RESULTS / f"{configuration}_external_predictions.parquet")


def confusion_matrices() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.7))
    for ax, config, title in zip(axes, CONFIG_ORDER, ["BIO1 + BIO12", "17 BIOCLIM predictors"]):
        if (RESULTS / f"{config}_external_predictions.parquet").exists():
            frame = load_predictions(config)
            matrix = confusion_matrix(frame["land_use_type"], frame["predicted_class"], labels=CLASSES, normalize="true")
        else:
            counts = pd.read_csv(RESULTS / f"{config}_external_confusion_matrix.csv", index_col=0).to_numpy(dtype=float)
            matrix = np.divide(counts, counts.sum(axis=1, keepdims=True), out=np.zeros_like(counts), where=counts.sum(axis=1, keepdims=True) != 0)
        image = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
        ax.set_xticks(range(len(CLASSES)), SHORT_NAMES, rotation=45, ha="right")
        ax.set_yticks(range(len(CLASSES)), SHORT_NAMES)
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("Observed class")
        ax.set_title(title)
    cbar = fig.colorbar(image, ax=axes, fraction=0.025, pad=0.03)
    cbar.set_label("Row-normalized fraction")
    fig.suptitle("External spatial-test confusion matrices", fontsize=14, fontweight="bold")
    save_figure(fig, "fig05_external_confusion_matrices")


def external_tile_maps() -> None:
    if all((RESULTS / f"{config}_external_predictions.parquet").exists() for config in CONFIG_ORDER):
        summaries = {}
        for config in CONFIG_ORDER:
            frame = load_predictions(config)
            frame["correct"] = frame["land_use_type"] == frame["predicted_class"]
            summaries[config] = frame.groupby("outer_tile_id")["correct"].mean()
        tile_summary = pd.concat(
            [
                summaries["shao_like_bio1_bio12"].rename("bio1_bio12_accuracy"),
                summaries["full_bioclim"].rename("full_bioclim_accuracy"),
            ],
            axis=1,
        ).dropna()
        tile_summary["accuracy_difference"] = (
            tile_summary["full_bioclim_accuracy"] - tile_summary["bio1_bio12_accuracy"]
        )
        tile_summary.index.name = "outer_tile_id"
        tile_summary.to_csv(RESULTS / "external_tile_accuracy_comparison.csv")
    else:
        tile_summary = pd.read_csv(RESULTS / "external_tile_accuracy_comparison.csv", index_col=0)

    difference = tile_summary["accuracy_difference"]
    improved = int((difference > 0).sum())
    unchanged = int((difference == 0).sum())
    worsened = int((difference < 0).sum())
    lower, median, upper = difference.quantile([0.25, 0.5, 0.75])

    fig = plt.figure(figsize=(12, 10.2), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.25, 0.85])
    map_ax = fig.add_subplot(grid[0, :])
    scatter_ax = fig.add_subplot(grid[1, 0])
    distribution_ax = fig.add_subplot(grid[1, 1])

    # The light background establishes the geographic support of the development
    # data; only the withheld external tiles carry the accuracy-difference colour.
    manifest = pd.read_csv(SPATIAL_RESULTS / "spatial_split_manifest.csv")
    for row in manifest.itertuples(index=False):
        if row.split_group == "development":
            tile_rectangle(map_ax, row.outer_tile_id, facecolor="0.91", edgecolor="white", linewidth=0.12)
    norm = TwoSlopeNorm(vmin=-0.30, vcenter=0, vmax=0.30)
    cmap = plt.get_cmap("RdBu_r")
    for tile_id, value in difference.items():
        tile_rectangle(map_ax, tile_id, facecolor=cmap(norm(value)), edgecolor="black", linewidth=0.35)
    format_world_axis(map_ax, "(a) Tile-wise accuracy improvement")
    map_ax.set_axisbelow(True)
    map_ax.grid(True, color="0.85", linewidth=0.4)
    map_ax.legend(
        handles=[Rectangle((0, 0), 1, 1, facecolor="0.91", edgecolor="0.7", label="Development tiles")],
        loc="lower left",
        frameon=True,
    )
    scalar = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(
        scalar,
        ax=map_ax,
        fraction=0.025,
        pad=0.015,
        extend="both",
        label="Accuracy difference (17 BIOCLIM minus BIO1 + BIO12)",
    )

    bridge = tile_summary["bio1_bio12_accuracy"]
    full = tile_summary["full_bioclim_accuracy"]
    scatter_ax.scatter(bridge, full, s=24, color="#0072B2", alpha=0.78, edgecolor="white", linewidth=0.35)
    scatter_ax.plot([0, 1], [0, 1], color="0.35", linewidth=1.0, linestyle="--", zorder=0)
    scatter_ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="BIO1 + BIO12 tile accuracy", ylabel="17 BIOCLIM tile accuracy", title="(b) Paired external-tile accuracy")
    scatter_ax.set_aspect("equal", adjustable="box")
    scatter_ax.grid(color="0.88", linewidth=0.6)

    # A box-and-jitter display retains the small number of one-point external
    # tiles without compressing the bulk of the distribution into a single bin.
    distribution_ax.boxplot(
        difference,
        vert=False,
        positions=[0],
        widths=0.22,
        patch_artist=True,
        showfliers=False,
        boxprops={"facecolor": "#0072B2", "alpha": 0.45},
        medianprops={"color": "black", "linewidth": 1.2},
        whiskerprops={"color": "0.3"},
        capprops={"color": "0.3"},
    )
    jitter = np.random.default_rng(42).uniform(-0.10, 0.10, len(difference))
    distribution_ax.scatter(difference, jitter, s=22, color="#0072B2", alpha=0.75, edgecolor="white", linewidth=0.3, zorder=3)
    distribution_ax.axvline(0, color="0.25", linewidth=1.0, linestyle="--")
    distribution_ax.set(
        xlim=(-0.20, 1.05),
        ylim=(-0.25, 0.25),
        xlabel="Accuracy difference (17 BIOCLIM minus BIO1 + BIO12)",
        title="(c) Distribution of tile-wise change",
    )
    distribution_ax.set_yticks([])
    distribution_ax.grid(axis="x", color="0.88", linewidth=0.6)
    distribution_ax.text(
        0.03,
        0.97,
        f"Improved: {improved}/{len(tile_summary)}\n"
        f"Unchanged: {unchanged}; worse: {worsened}\n"
        f"Median: {median * 100:+.1f} pp\n"
        f"IQR: {lower * 100:+.1f} to {upper * 100:+.1f} pp",
        transform=distribution_ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "0.75", "boxstyle": "round,pad=0.3"},
    )
    save_figure(fig, "fig06_external_tile_accuracy")


def load_model(path: Path):
    with bz2.open(path, "rb") as source:
        return pickle.load(source)


def feature_importance() -> None:
    reduced = load_model(MODELS / "shao_like_bio1_bio12_model.pkl.bz2")
    full = load_model(MODELS / "full_bioclim_model.pkl.bz2")
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.8), gridspec_kw={"width_ratios": [0.7, 1.8]})
    axes[0].barh(["BIO1", "BIO12"], reduced.feature_importances_, color=COLORS["shao_like_bio1_bio12"])
    axes[0].invert_yaxis(); axes[0].set_xlabel("Mean decrease in impurity"); axes[0].set_title("BIO1 + BIO12")
    order = np.argsort(full.feature_importances_)
    axes[1].barh(np.array([name.upper() for name in FEATURES])[order], full.feature_importances_[order], color=COLORS["full_bioclim"])
    axes[1].set_xlabel("Mean decrease in impurity"); axes[1].set_title("17 BIOCLIM predictors")
    for ax in axes: ax.grid(axis="x", color="0.88")
    fig.suptitle("Random Forest impurity-based feature importance in all-data models", fontsize=14, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "fig07_feature_importance")


def main() -> None:
    logger = configure_logging(ROOT / "training/logs/plot_publication_figures.log")
    for name, function in [
        # Figure 1 is the authored SVG
        # figures/paleoveg_figure1_model_comparison_layout_v7.svg.
        # Its rendered PDF is included directly by the manuscript.
        ("spatial split", split_map),
        ("CV comparison", cv_performance), ("Shao scores", shao_score_comparison),
        ("confusion matrices", confusion_matrices), ("tile maps", external_tile_maps),
        ("feature importance", feature_importance),
    ]:
        logger.info("Generating %s", name)
        function()
    logger.info("Wrote publication figures to %s", FIGURES)


if __name__ == "__main__":
    main()
