"""Artifact-first, donor-grouped pregnancy prediction experiment.

The locked temporal holdout is scored exactly once after preprocessing,
calibration, threshold selection, and ensemble weighting are learned from
pre-holdout out-of-fold predictions.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.config import (
    CATEGORICAL_FEATURES,
    GROUP_COL,
    HOLDOUT_CUTOFF,
    NUMERIC_FEATURES,
    SEED,
    TARGET_COL,
)
from ml.features import build_feature_matrix
from ml.split import get_group_kfold_splits, temporal_split

TIME_FEATURES = ["et_month_number", "et_quarter", "et_dayofweek"]
MODEL_ORDER = ("logistic", "catboost", "xgboost", "tabpfn")


@dataclass(frozen=True)
class ExperimentConfig:
    output_dir: Path = Path("outputs/pregnancy_prediction")
    cutoff: str = HOLDOUT_CUTOFF
    folds: int = 5
    seed: int = SEED
    calibration: str = "sigmoid"


def _safe_metric(metric: Callable, y: np.ndarray, p: np.ndarray) -> float:
    try:
        return float(metric(y, p))
    except ValueError:
        return float("nan")


def _metrics(y: np.ndarray, p: np.ndarray, threshold: float) -> dict[str, float | int]:
    pred = (p >= threshold).astype(int)
    cm = confusion_matrix(y, pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    return {
        "roc_auc": _safe_metric(roc_auc_score, y, p),
        "average_precision": _safe_metric(average_precision_score, y, p),
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-7, 1 - 1e-7), labels=[0, 1])),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def _add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    dates = pd.to_datetime(result["et_date"], errors="coerce")
    result["et_month_number"] = dates.dt.month.astype(float)
    result["et_quarter"] = dates.dt.quarter.astype(float)
    result["et_dayofweek"] = dates.dt.dayofweek.astype(float)
    for column in CATEGORICAL_FEATURES:
        # sklearn imputers handle numpy.nan, while pandas.NA has ambiguous
        # boolean semantics in object arrays.
        result[column] = result[column].astype(object).where(result[column].notna(), np.nan)
    return result


def _preprocessor(scale: bool) -> ColumnTransformer:
    numeric_steps = [("impute", SimpleImputer(strategy="median", keep_empty_features=True))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
        ("encode", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=2)),
    ])
    return ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES + TIME_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])


def _builders(seed: int) -> dict[str, Callable[[], Pipeline]]:
    builders: dict[str, Callable[[], Pipeline]] = {
        "logistic": lambda: Pipeline([
            ("preprocess", _preprocessor(scale=True)),
            ("model", LogisticRegression(
                solver="saga", l1_ratio=0.1, C=0.3,
                class_weight="balanced", max_iter=5000, random_state=seed,
            )),
        ])
    }
    try:
        from xgboost import XGBClassifier
        builders["xgboost"] = lambda: Pipeline([
            ("preprocess", _preprocessor(scale=False)),
            ("model", XGBClassifier(
                objective="binary:logistic", eval_metric="auc", tree_method="hist",
                max_depth=3, learning_rate=0.03, n_estimators=500,
                min_child_weight=3, subsample=0.8, colsample_bytree=0.8,
                reg_lambda=10, reg_alpha=1, random_state=seed, n_jobs=-1,
            )),
        ])
    except ImportError:
        pass
    try:
        from catboost import CatBoostClassifier
        builders["catboost"] = lambda: Pipeline([
            ("preprocess", _preprocessor(scale=False)),
            ("model", CatBoostClassifier(
                loss_function="Logloss", eval_metric="AUC", depth=4,
                learning_rate=0.03, iterations=500, l2_leaf_reg=10,
                auto_class_weights="Balanced", random_seed=seed,
                verbose=False, allow_writing_files=False,
            )),
        ])
    except ImportError:
        pass
    # TabPFN is deliberately optional; it is not silently replaced by another model.
    return builders


def _fit_platt(y: np.ndarray, raw: np.ndarray, seed: int) -> LogisticRegression:
    logits = np.log(np.clip(raw, 1e-6, 1 - 1e-6) / np.clip(1 - raw, 1e-6, 1))
    calibrator = LogisticRegression(C=1.0, random_state=seed)
    calibrator.fit(logits.reshape(-1, 1), y)
    return calibrator


def _calibrate(calibrator: LogisticRegression, raw: np.ndarray) -> np.ndarray:
    logits = np.log(np.clip(raw, 1e-6, 1 - 1e-6) / np.clip(1 - raw, 1e-6, 1))
    return calibrator.predict_proba(logits.reshape(-1, 1))[:, 1]


def _ensemble_weights(y: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    count = matrix.shape[1]
    result = minimize(
        lambda w: brier_score_loss(y, np.clip(matrix @ w, 1e-7, 1 - 1e-7)),
        np.full(count, 1 / count), method="SLSQP",
        bounds=[(0.0, 1.0)] * count,
        constraints={"type": "eq", "fun": lambda w: float(w.sum() - 1)},
    )
    return result.x if result.success else np.full(count, 1 / count)


def _threshold(y: np.ndarray, p: np.ndarray) -> float:
    candidates = np.linspace(0.1, 0.9, 161)
    scores = [f1_score(y, p >= value, zero_division=0) for value in candidates]
    return float(candidates[int(np.argmax(scores))])


def _feature_importance(name: str, pipeline: Pipeline) -> pd.DataFrame:
    model = pipeline.named_steps["model"]
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
        kind = "gain"
    elif hasattr(model, "coef_"):
        values = np.asarray(model.coef_[0], dtype=float)
        kind = "coefficient"
    else:
        return pd.DataFrame(columns=["model", "feature", "importance_type", "raw_importance", "normalized_importance", "sign"])
    absolute = np.abs(values)
    total = absolute.sum() or 1.0
    return pd.DataFrame({
        "model": name, "feature": names, "importance_type": kind,
        "raw_importance": values, "normalized_importance": absolute / total,
        "sign": np.sign(values).astype(int),
    }).sort_values("normalized_importance", ascending=False)


def run_experiment(csv_path: str | None = None, config: ExperimentConfig | None = None) -> dict:
    config = config or ExperimentConfig()
    output = Path(config.output_dir)
    models_dir = output / "trained_models"
    models_dir.mkdir(parents=True, exist_ok=True)

    full = _add_time_features(build_feature_matrix(csv_path))
    train, holdout = temporal_split(full, config.cutoff)
    unique_groups = train[GROUP_COL].fillna("UNKNOWN").nunique()
    folds = min(config.folds, int(unique_groups))
    if folds < 2:
        raise ValueError("At least two distinct donor groups are required for grouped validation")
    splits = get_group_kfold_splits(train, folds)
    feature_columns = NUMERIC_FEATURES + TIME_FEATURES + CATEGORICAL_FEATURES
    X_train, y_train = train[feature_columns], train[TARGET_COL].to_numpy(int)
    X_holdout, y_holdout = holdout[feature_columns], holdout[TARGET_COL].to_numpy(int)

    assignments = pd.DataFrame({
        "row_id": train["et_number"].astype(str), "donor": train[GROUP_COL].astype(str),
        "et_date": train["et_date"].astype(str), "fold": -1,
    })
    for fold, (_, valid_idx) in enumerate(splits):
        assignments.loc[valid_idx, "fold"] = fold
    assignments.to_csv(output / "fold_assignments.csv", index=False)

    builders = _builders(config.seed)
    oof_raw: dict[str, np.ndarray] = {}
    holdout_calibrated: dict[str, np.ndarray] = {}
    fitted: dict[str, Pipeline] = {}
    calibrators: dict[str, LogisticRegression] = {}
    runtimes: dict[str, float] = {}
    importance_frames: list[pd.DataFrame] = []

    for name in MODEL_ORDER:
        if name not in builders:
            continue
        started = time.perf_counter()
        raw = np.zeros(len(train), dtype=float)
        for fit_idx, valid_idx in splits:
            fold_model = builders[name]()
            fold_model.fit(X_train.iloc[fit_idx], y_train[fit_idx])
            raw[valid_idx] = fold_model.predict_proba(X_train.iloc[valid_idx])[:, 1]
        calibrator = _fit_platt(y_train, raw, config.seed)
        final_model = builders[name]()
        final_model.fit(X_train, y_train)
        holdout_raw = final_model.predict_proba(X_holdout)[:, 1]
        oof_raw[name] = _calibrate(calibrator, raw)
        holdout_calibrated[name] = _calibrate(calibrator, holdout_raw)
        fitted[name] = final_model
        calibrators[name] = calibrator
        runtimes[name] = time.perf_counter() - started
        importance_frames.append(_feature_importance(name, final_model))
        joblib.dump(final_model, models_dir / f"{name}.joblib")
        joblib.dump(calibrator, models_dir / f"{name}_sigmoid_calibrator.joblib")

    if not fitted:
        raise RuntimeError("No supported base model is installed")
    names = list(fitted)
    oof_matrix = np.column_stack([oof_raw[name] for name in names])
    holdout_matrix = np.column_stack([holdout_calibrated[name] for name in names])
    weights = _ensemble_weights(y_train, oof_matrix)
    oof_ensemble = oof_matrix @ weights
    holdout_ensemble = holdout_matrix @ weights
    decision_threshold = _threshold(y_train, oof_ensemble)
    (models_dir / "ensemble_weights.json").write_text(json.dumps({
        "models": names, "weights": dict(zip(names, map(float, weights))),
        "decision_threshold": decision_threshold,
    }, indent=2), encoding="utf-8")

    oof = assignments.copy()
    oof["actual_label"] = y_train
    for name in names:
        oof[f"{name}_probability"] = oof_raw[name]
    oof["ensemble_probability"] = oof_ensemble
    oof.to_csv(output / "oof_predictions.csv", index=False)

    uncertainty = holdout_matrix.std(axis=1) if len(names) > 1 else np.zeros(len(holdout))
    holdout_predictions = pd.DataFrame({
        "row_id": holdout["et_number"].astype(str),
        "et_date": holdout["et_date"].astype(str),
        "donor": holdout[GROUP_COL].astype(str), "actual_label": y_holdout,
    })
    for name in names:
        holdout_predictions[f"{name}_probability"] = holdout_calibrated[name]
    holdout_predictions["ensemble_probability"] = holdout_ensemble
    holdout_predictions["predicted_class"] = (holdout_ensemble >= decision_threshold).astype(int)
    holdout_predictions["uncertainty_score"] = uncertainty
    holdout_predictions["uncertainty_label"] = pd.cut(
        uncertainty, [-np.inf, 0.05, 0.15, np.inf], labels=["low", "moderate", "high"]
    ).astype(str)
    holdout_predictions.to_csv(output / "holdout_predictions.csv", index=False)

    metric_rows = []
    for name in names + ["ensemble"]:
        oof_p = oof_ensemble if name == "ensemble" else oof_raw[name]
        hold_p = holdout_ensemble if name == "ensemble" else holdout_calibrated[name]
        parameters = (
            fitted[name].named_steps["model"].get_params(deep=False)
            if name in fitted else {"weights": dict(zip(names, map(float, weights)))}
        )
        row = {
            "model": name,
            "runtime_seconds": runtimes.get(name, sum(runtimes.values())),
            "selected_hyperparameters": json.dumps(parameters, default=str, sort_keys=True),
        }
        row.update({f"cv_{key}": value for key, value in _metrics(y_train, oof_p, decision_threshold).items()})
        row.update({f"holdout_{key}": value for key, value in _metrics(y_holdout, hold_p, decision_threshold).items()})
        metric_rows.append(row)
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(output / "model_metrics.csv", index=False)

    importance = pd.concat(importance_frames, ignore_index=True) if importance_frames else pd.DataFrame()
    importance.to_csv(output / "feature_importance.csv", index=False)
    uncertainty_report = pd.DataFrame([{
        "record_type": "summary", "row_id": "", "et_date": "", "donor": "",
        "uncertainty_score": "", "uncertainty_label": "",
        "holdout_rows": len(holdout), "mean_disagreement": float(uncertainty.mean()),
        "max_disagreement": float(uncertainty.max()),
        "high_uncertainty_rows": int((uncertainty > 0.15).sum()),
        "moderate_uncertainty_rows": int(((uncertainty > 0.05) & (uncertainty <= 0.15)).sum()),
        "low_uncertainty_rows": int((uncertainty <= 0.05).sum()),
    }])
    high_rows = holdout_predictions.loc[
        holdout_predictions["uncertainty_label"] == "high",
        ["row_id", "et_date", "donor", "uncertainty_score", "uncertainty_label"],
    ].copy()
    if not high_rows.empty:
        high_rows.insert(0, "record_type", "high_uncertainty_case")
        uncertainty_report = pd.concat([uncertainty_report, high_rows], ignore_index=True)
    uncertainty_report.to_csv(output / "uncertainty_report.csv", index=False)

    calibration_rows = []
    for split_name, labels, probabilities in (
        ("oof", y_train, {**oof_raw, "ensemble": oof_ensemble}),
        ("holdout", y_holdout, {**holdout_calibrated, "ensemble": holdout_ensemble}),
    ):
        for model_name, model_probability in probabilities.items():
            observed, predicted = calibration_curve(labels, model_probability, n_bins=10, strategy="quantile")
            calibration_rows.extend({
                "split": split_name, "model": model_name, "bin": index,
                "mean_predicted_probability": float(predicted_value),
                "observed_positive_rate": float(observed_value),
            } for index, (predicted_value, observed_value) in enumerate(zip(predicted, observed)))
    pd.DataFrame(calibration_rows).to_csv(output / "calibration_report.csv", index=False)

    comparison = {
        "config": {**asdict(config), "output_dir": str(config.output_dir)},
        "training_rows": len(train), "holdout_rows": len(holdout),
        "donor_groups": int(unique_groups), "folds": folds,
        "models": names, "ensemble_weights": dict(zip(names, map(float, weights))),
        "decision_threshold": decision_threshold,
        "champion_by_oof_brier": str(metrics.sort_values("cv_brier_score").iloc[0]["model"]),
        "holdout_is_reporting_only": True,
    }
    (output / "model_comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    (output / "experiment_registry.json").write_text(json.dumps({
        "latest": comparison,
        "artifacts": sorted(str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()),
    }, indent=2), encoding="utf-8")
    (output / "data_prep_summary.json").write_text(json.dumps({
        "source": str(csv_path or "configured default"), "labeled_rows": len(full),
        "training_rows": len(train), "holdout_rows": len(holdout),
        "cutoff": config.cutoff, "features": feature_columns,
    }, indent=2), encoding="utf-8")
    return comparison
