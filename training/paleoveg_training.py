"""Shared, deliberately small training and validation utilities."""

from __future__ import annotations

import bz2
import hashlib
import json
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
)

FEATURES = ["bio1"] + [f"bio{i}" for i in range(4, 20)]
TARGET = "land_use_type"
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12]
EXCLUDED_CLASSES = [0, 11, 13, 14]
RF_PARAMETERS = {"max_depth": 20, "random_state": 42, "n_jobs": -1}
# Shared publication palette, in the class-code order used by the model.
LAND_USE_COLORS = {
    1: "#1b9e77",  # evergreen needleleaf forest
    2: "#006d2c",  # evergreen broadleaf forest
    3: "#66a61e",  # deciduous needleleaf forest
    4: "#e6ab02",  # deciduous broadleaf forest
    5: "#a6761d",  # mixed forest
    6: "#7570b3",  # woodland
    7: "#e7298a",  # wooded grassland
    8: "#d95f02",  # closed shrubland
    9: "#e6ab02",  # open shrubland
    10: "#a6cee3",  # grassland
    12: "#bdbdbd",  # bare ground
}


def configure_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(log_path.stem)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for handler in (logging.StreamHandler(), logging.FileHandler(log_path)):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def outer_tile_ids(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Return stable global 5-degree tile identifiers."""
    col = np.floor((lon + 180.0) / 5.0).astype(np.int16)
    row = np.floor((lat + 90.0) / 5.0).astype(np.int16)
    col = np.clip(col, 0, 71)
    row = np.clip(row, 0, 35)
    return np.asarray(
        [f"outer_r{r:02d}_c{c:02d}" for r, c in zip(row, col)], dtype=object
    )


def make_model() -> RandomForestClassifier:
    return RandomForestClassifier(**RF_PARAMETERS)


def assign_size_balanced_folds(
    tile_counts: pd.Series, fold_count: int, seed: int
) -> dict[str, int]:
    """Assign whole tiles to folds while approximately balancing row counts."""
    if len(tile_counts) < fold_count:
        raise ValueError("There are fewer spatial tiles than requested folds.")
    rng = np.random.default_rng(seed)
    shuffled = tile_counts.rename_axis("tile_id").reset_index(name="row_count")
    shuffled["tie"] = rng.random(len(shuffled))
    shuffled = shuffled.sort_values(["row_count", "tie"], ascending=[False, True])
    loads = np.zeros(fold_count, dtype=np.int64)
    assignments: dict[str, int] = {}
    for row in shuffled.itertuples(index=False):
        candidates = np.flatnonzero(loads == loads.min())
        fold = int(rng.choice(candidates))
        assignments[str(row.tile_id)] = fold
        loads[fold] += int(row.row_count)
    return assignments


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, probabilities: np.ndarray) -> dict:
    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=CLASSES, average="weighted", zero_division=0)),
        "multiclass_log_loss": float(log_loss(y_true, probabilities, labels=CLASSES)),
    }


def shao_goodness_scores(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    classes: list[int] = CLASSES,
    random_state: int = 42,
) -> pd.DataFrame:
    """Calculate the vegetation-class goodness score in Shao et al. Eq. 3.

    ``D_i`` is the mean squared difference between modeled class probability
    and binary observed class occurrence. ``D_i,max`` is the corresponding
    mean squared difference after one deterministic random rearrangement of
    the observed AVHRR labels. The reported score is ``1 - D_i / D_i,max``.

    A single permutation is applied to the categorical labels, preserving all
    class prevalences and their mutually exclusive structure. This implements
    the paper's randomly rearranged AVHRR reference while making the result
    exactly reproducible.
    """
    observed_labels = np.asarray(y_true)
    modeled = np.asarray(probabilities, dtype=np.float64)
    if modeled.shape != (len(observed_labels), len(classes)):
        raise ValueError(
            "probabilities must have shape (n_observations, n_classes) in the supplied class order"
        )
    rng = np.random.default_rng(random_state)
    random_labels = observed_labels[rng.permutation(len(observed_labels))]
    rows = []
    for index, class_code in enumerate(classes):
        observed = (observed_labels == class_code).astype(np.float64)
        random_cover = (random_labels == class_code).astype(np.float64)
        d_model = float(np.mean(np.square(modeled[:, index] - observed)))
        d_random = float(np.mean(np.square(random_cover - observed)))
        score = float(1.0 - (d_model / d_random)) if d_random > 0 else np.nan
        rows.append(
            {
                "class": class_code,
                "d_model": d_model,
                "d_random": d_random,
                "shao_goodness_score": score,
                "observed_prevalence": float(observed.mean()),
                "predicted_mean_probability": float(modeled[:, index].mean()),
            }
        )
    result = pd.DataFrame(rows)
    result["class"] = result["class"].astype(object)
    result.loc[len(result)] = {
        "class": "ensemble_mean",
        "d_model": float(result["d_model"].mean()),
        "d_random": float(result["d_random"].mean()),
        "shao_goodness_score": float(result["shao_goodness_score"].mean()),
        "observed_prevalence": float(result["observed_prevalence"].mean()),
        "predicted_mean_probability": float(result["predicted_mean_probability"].mean()),
    }
    return result


def evaluate(model: RandomForestClassifier, frame: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    x = frame[FEATURES]
    y = frame[TARGET].to_numpy()
    predicted = model.predict(x)
    probabilities = model.predict_proba(x)
    metrics = calculate_metrics(y, predicted, probabilities)
    report = pd.DataFrame(
        classification_report(
            y, predicted, labels=CLASSES, output_dict=True, zero_division=0
        )
    ).T.rename_axis("class")
    matrix = pd.DataFrame(
        confusion_matrix(y, predicted, labels=CLASSES), index=CLASSES, columns=CLASSES
    )
    matrix.index.name = "observed"
    matrix.columns.name = "predicted"
    return metrics, report, matrix, predicted, probabilities


def save_model(model: RandomForestClassifier, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with bz2.BZ2File(path, "w") as target:
        pickle.dump(model, target, protocol=pickle.HIGHEST_PROTOCOL)


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
