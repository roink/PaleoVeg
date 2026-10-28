#!/usr/bin/env python3
"""Run outer-tile spatial CV, external evaluation, and final model fitting."""

from __future__ import annotations

import argparse
import math
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from paleoveg_training import (
    CLASSES,
    FEATURES,
    RF_PARAMETERS,
    TARGET,
    assign_size_balanced_folds,
    calculate_metrics,
    configure_logging,
    evaluate,
    make_model,
    save_model,
    sha256,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]


def portable_path(path: Path) -> str:
    """Prefer a repository-relative path in archived run metadata."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "training/data/processed/paleoveg_training.parquet")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "training/results/spatial_validation_v1")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "training/models/spatial_validation_v1")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--external-fraction", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-rows", type=int, default=None, help="Smoke tests only; stratified sample of rows.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = configure_logging(ROOT / "training/logs/validate_and_train.log")
    if not 0 < args.external_fraction < 1:
        raise ValueError("--external-fraction must lie strictly between zero and one.")
    frame = pd.read_parquet(args.data)
    required = set(FEATURES + [TARGET, "lon", "lat", "outer_tile_id"])
    if missing := required.difference(frame.columns):
        raise ValueError(f"Modeling table is missing columns: {sorted(missing)}")
    frame = frame.dropna(subset=list(required)).reset_index(drop=True)
    if args.max_rows is not None and len(frame) > args.max_rows:
        frame = frame.groupby(TARGET, group_keys=False).sample(
            n=max(1, args.max_rows // frame[TARGET].nunique()), random_state=args.seed
        ).reset_index(drop=True)
    unknown = sorted(set(frame[TARGET].unique()).difference(CLASSES))
    if unknown:
        raise ValueError(f"Unexpected target classes: {unknown}")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.models_dir.mkdir(parents=True, exist_ok=True)
    tile_counts = frame["outer_tile_id"].value_counts().sort_index()
    rng = np.random.default_rng(args.seed)
    tile_names = tile_counts.index.to_numpy().copy()
    rng.shuffle(tile_names)
    external_count = max(1, math.ceil(len(tile_names) * args.external_fraction))
    external_tiles = set(tile_names[:external_count].tolist())
    development_counts = tile_counts[~tile_counts.index.isin(external_tiles)]
    fold_by_tile = assign_size_balanced_folds(development_counts, args.folds, args.seed + 17)
    manifest = tile_counts.rename("row_count").rename_axis("outer_tile_id").reset_index()
    manifest["split_group"] = np.where(manifest["outer_tile_id"].isin(external_tiles), "external_test", "development")
    manifest["cv_fold"] = manifest["outer_tile_id"].map(fold_by_tile).astype("Int64")
    manifest.to_csv(args.results_dir / "spatial_split_manifest.csv", index=False)
    logger.info("Rows=%s; tiles=%s; external tiles=%s", f"{len(frame):,}", len(tile_counts), len(external_tiles))

    development_mask = ~frame["outer_tile_id"].isin(external_tiles)
    fold_rows = []
    class_reports = []
    for fold in range(args.folds):
        validation_tiles = {tile for tile, assigned in fold_by_tile.items() if assigned == fold}
        validation_mask = frame["outer_tile_id"].isin(validation_tiles)
        train = frame[development_mask & ~validation_mask]
        validation = frame[validation_mask]
        logger.info("Fold %s: fitting %s rows; evaluating %s rows in %s tiles", fold, f"{len(train):,}", f"{len(validation):,}", len(validation_tiles))
        model = make_model()
        model.fit(train[FEATURES], train[TARGET])
        metrics, report, matrix, _, _ = evaluate(model, validation)
        metrics["cv_fold"] = fold
        metrics["train_n"] = len(train)
        metrics["held_out_tiles"] = len(validation_tiles)
        fold_rows.append(metrics)
        report.assign(cv_fold=fold).to_csv(args.results_dir / f"cv_fold_{fold}_class_report.csv")
        matrix.to_csv(args.results_dir / f"cv_fold_{fold}_confusion_matrix.csv")
        class_reports.append(report.assign(cv_fold=fold).reset_index())
    fold_metrics = pd.DataFrame(fold_rows).sort_values("cv_fold")
    fold_metrics.to_csv(args.results_dir / "cv_fold_metrics.csv", index=False)
    pd.concat(class_reports, ignore_index=True).to_csv(args.results_dir / "cv_class_metrics.csv", index=False)
    numeric = ["accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "multiclass_log_loss"]
    cv_summary = {name: {"mean": float(fold_metrics[name].mean()), "sd": float(fold_metrics[name].std(ddof=1))} for name in numeric}
    write_json(cv_summary, args.results_dir / "cv_summary.json")

    development = frame[development_mask]
    external = frame[~development_mask]
    majority_class = int(development[TARGET].mode().iloc[0])
    baseline_prediction = np.full(len(external), majority_class, dtype=np.int16)
    baseline_probabilities = np.zeros((len(external), len(CLASSES)), dtype=np.float64)
    baseline_probabilities[:, CLASSES.index(majority_class)] = 1.0
    baseline_metrics = calculate_metrics(
        external[TARGET].to_numpy(), baseline_prediction, baseline_probabilities
    )
    baseline_metrics["majority_class"] = majority_class
    write_json(baseline_metrics, args.results_dir / "external_test_majority_baseline.json")
    logger.info("Fitting development model on %s rows", f"{len(development):,}")
    development_model = make_model()
    development_model.fit(development[FEATURES], development[TARGET])
    save_model(development_model, args.models_dir / "development_model.pkl.bz2")
    metrics, report, matrix, predicted, probabilities = evaluate(development_model, external)
    write_json(metrics, args.results_dir / "external_test_metrics.json")
    report.to_csv(args.results_dir / "external_test_class_report.csv")
    matrix.to_csv(args.results_dir / "external_test_confusion_matrix.csv")
    prediction_frame = external[["lon", "lat", "outer_tile_id", TARGET]].copy()
    prediction_frame["predicted_class"] = predicted
    for index, class_code in enumerate(CLASSES):
        prediction_frame[f"probability_{class_code}"] = probabilities[:, index]
    prediction_frame.to_parquet(args.results_dir / "external_test_predictions.parquet", index=False)

    logger.info("Fitting release model on all %s rows", f"{len(frame):,}")
    release_model = make_model()
    release_model.fit(frame[FEATURES], frame[TARGET])
    release_path = args.models_dir / "model.pkl.bz2"
    save_model(release_model, release_path)
    write_json({
        "data": {"path": portable_path(args.data), "sha256": sha256(args.data), "rows": len(frame)},
        "model": {"type": "sklearn.ensemble.RandomForestClassifier", "parameters": RF_PARAMETERS, "classes": CLASSES, "artifact": portable_path(release_path), "sha256": sha256(release_path)},
        "validation": {"outer_tile_degrees": 5, "external_fraction": args.external_fraction, "external_tile_count": len(external_tiles), "folds": args.folds, "seed": args.seed},
        "software": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__},
        "smoke_test_max_rows": args.max_rows,
    }, args.results_dir / "run_metadata.json")
    logger.info("Complete. External accuracy=%.6f; macro F1=%.6f", metrics["accuracy"], metrics["macro_f1"])


if __name__ == "__main__":
    main()
