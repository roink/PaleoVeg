#!/usr/bin/env python3
"""Compare the Shao-like BIO1+BIO12 RF with the full PaleoVeg RF."""

from __future__ import annotations

import argparse
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
    calculate_metrics,
    configure_logging,
    save_model,
    sha256,
    shao_goodness_scores,
    write_json,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
SHAO_LIKE_FEATURES = ["bio1", "bio12"]
CONFIGURATIONS = {
    "shao_like_bio1_bio12": SHAO_LIKE_FEATURES,
    "full_bioclim": FEATURES,
}
CLASS_NAMES = {
    1: "Evergreen needleleaf forest",
    2: "Evergreen broadleaf forest",
    3: "Deciduous needleleaf forest",
    4: "Deciduous broadleaf forest",
    5: "Mixed forest",
    6: "Woodland",
    7: "Wooded grassland",
    8: "Closed shrubland",
    9: "Open shrubland",
    10: "Grassland",
    12: "Bare ground",
}
SHAO_MODEL_5_SCORES = {
    1: 0.52, 2: 0.77, 3: 0.41, 4: 0.17, 5: 0.34, 6: 0.48,
    7: 0.48, 8: 0.29, 9: 0.50, 10: 0.53, 12: 0.97,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "training/data/processed/paleoveg_training.parquet")
    parser.add_argument("--split-manifest", type=Path, default=ROOT / "training/results/spatial_validation_v1/spatial_split_manifest.csv")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "training/results/predictor_set_comparison")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "training/models/predictor_set_comparison")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def fit_model(frame: pd.DataFrame, features: list[str]) -> RandomForestClassifier:
    model = RandomForestClassifier(**RF_PARAMETERS)
    model.fit(frame[features], frame[TARGET])
    if model.classes_.tolist() != CLASSES:
        raise RuntimeError(f"Unexpected model classes: {model.classes_.tolist()}")
    return model


def predict_and_score(
    model: RandomForestClassifier,
    frame: pd.DataFrame,
    features: list[str],
    random_reference_seed: int,
) -> tuple[dict, pd.DataFrame, np.ndarray, np.ndarray]:
    observed = frame[TARGET].to_numpy()
    probabilities = model.predict_proba(frame[features])
    predicted = model.classes_[np.argmax(probabilities, axis=1)]
    metrics = calculate_metrics(observed, predicted, probabilities)
    shao_scores = shao_goodness_scores(
        observed, probabilities, random_state=random_reference_seed
    )
    return metrics, shao_scores, predicted, probabilities


def main() -> None:
    args = parse_args()
    logger = configure_logging(ROOT / "training/logs/compare_predictor_sets.log")
    frame = pd.read_parquet(
        args.data, columns=FEATURES + [TARGET, "lon", "lat", "outer_tile_id"]
    ).dropna().reset_index(drop=True)
    manifest = pd.read_csv(args.split_manifest)
    required_manifest = {"outer_tile_id", "split_group", "cv_fold"}
    if missing := required_manifest.difference(manifest.columns):
        raise ValueError(f"Split manifest missing columns: {sorted(missing)}")
    split_lookup = manifest.set_index("outer_tile_id")
    frame["split_group"] = frame["outer_tile_id"].map(split_lookup["split_group"])
    frame["cv_fold"] = frame["outer_tile_id"].map(split_lookup["cv_fold"])
    if frame[["split_group"]].isna().any().any():
        raise ValueError("Some modeling rows have no split-manifest assignment.")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.models_dir.mkdir(parents=True, exist_ok=True)
    development = frame[frame["split_group"] == "development"]
    external = frame[frame["split_group"] == "external_test"]
    folds = sorted(int(value) for value in development["cv_fold"].unique())
    metric_rows = []
    shao_rows = []

    for configuration, features in CONFIGURATIONS.items():
        logger.info("Configuration %s with predictors %s", configuration, features)
        for fold in folds:
            train = development[development["cv_fold"] != fold]
            validation = development[development["cv_fold"] == fold]
            logger.info(
                "%s fold %s: train=%s validation=%s",
                configuration, fold, f"{len(train):,}", f"{len(validation):,}",
            )
            model = fit_model(train, features)
            metrics, scores, _, _ = predict_and_score(
                model, validation, features, random_reference_seed=args.seed + 1000 + fold
            )
            metrics.update({"configuration": configuration, "evaluation": "blocked_cv", "cv_fold": fold, "predictor_count": len(features)})
            metric_rows.append(metrics)
            scores.insert(0, "cv_fold", fold)
            scores.insert(0, "evaluation", "blocked_cv")
            scores.insert(0, "configuration", configuration)
            shao_rows.append(scores)

        logger.info("%s external fit: development=%s external=%s", configuration, f"{len(development):,}", f"{len(external):,}")
        development_model = fit_model(development, features)
        metrics, scores, predicted, probabilities = predict_and_score(
            development_model, external, features, random_reference_seed=args.seed + 2000
        )
        metrics.update({"configuration": configuration, "evaluation": "external_test", "cv_fold": None, "predictor_count": len(features)})
        metric_rows.append(metrics)
        scores.insert(0, "cv_fold", pd.NA)
        scores.insert(0, "evaluation", "external_test")
        scores.insert(0, "configuration", configuration)
        shao_rows.append(scores)
        counts = confusion_matrix(external[TARGET], predicted, labels=CLASSES)
        pd.DataFrame(counts, index=CLASSES, columns=CLASSES).to_csv(
            args.results_dir / f"{configuration}_external_confusion_matrix.csv"
        )
        save_model(development_model, args.models_dir / f"{configuration}_development_model.pkl.bz2")

        predictions = external[["lon", "lat", "outer_tile_id", TARGET]].copy()
        predictions["predicted_class"] = predicted
        for index, class_code in enumerate(CLASSES):
            predictions[f"probability_{class_code}"] = probabilities[:, index]
        predictions.to_parquet(args.results_dir / f"{configuration}_external_predictions.parquet", index=False)

        logger.info("%s final all-data fit=%s", configuration, f"{len(frame):,}")
        final_model = fit_model(frame, features)
        save_model(final_model, args.models_dir / f"{configuration}_model.pkl.bz2")

    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(args.results_dir / "metrics.csv", index=False)
    score_table = pd.concat(shao_rows, ignore_index=True)
    score_table["class_name"] = score_table["class"].map(CLASS_NAMES).fillna("Ensemble mean")
    score_table.to_csv(args.results_dir / "shao_goodness_scores.csv", index=False)

    cv_metrics = metrics[metrics["evaluation"] == "blocked_cv"]
    metric_columns = ["accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "multiclass_log_loss"]
    cv_summary = cv_metrics.groupby("configuration")[metric_columns].agg(["mean", "std"])
    cv_summary.columns = [f"{metric}_{stat}" for metric, stat in cv_summary.columns]
    cv_summary.reset_index().to_csv(args.results_dir / "cv_summary.csv", index=False)

    cv_scores = score_table[(score_table["evaluation"] == "blocked_cv")]
    shao_cv_summary = (
        cv_scores.groupby(["configuration", "class", "class_name"], dropna=False)["shao_goodness_score"]
        .agg(["mean", "std"]).reset_index()
    )
    shao_cv_summary.to_csv(args.results_dir / "shao_goodness_cv_summary.csv", index=False)

    published = pd.DataFrame(
        [{"class": code, "class_name": CLASS_NAMES[code], "shao_2018_model_5_score": score} for code, score in SHAO_MODEL_5_SCORES.items()]
        # Preserve the ensemble score printed in Table 1. It differs slightly
        # from the mean of the displayed class values because those are rounded.
        + [{"class": "ensemble_mean", "class_name": "Ensemble mean", "shao_2018_model_5_score": 0.51}]
    )
    external_scores = score_table[score_table["evaluation"] == "external_test"][["configuration", "class", "shao_goodness_score"]]
    comparison = published.merge(external_scores, on="class", how="left")
    comparison.to_csv(args.results_dir / "shao_model5_external_comparison.csv", index=False)

    write_json(
        {
            "data_sha256": sha256(args.data),
            "split_manifest_sha256": sha256(args.split_manifest),
            "configurations": CONFIGURATIONS,
            "model_parameters": RF_PARAMETERS,
            "shao_score": {
                "definition": "S_i = 1 - D_i / D_i,max",
                "random_rearrangement": "one deterministic permutation of categorical observed labels per evaluation set",
                "external_random_reference_seed": args.seed + 2000,
            },
            "software": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__},
        },
        args.results_dir / "run_metadata.json",
    )
    logger.info("Predictor-set comparison complete")


if __name__ == "__main__":
    main()
