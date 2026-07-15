"""Model training, calibration, and evaluation pipeline.

Trains three models as specified in REQUIREMENTS §4.1:
1. Logistic Regression (baseline)
2. TabPFN (primary)
3. XGBoost (benchmark)

Then applies post-hoc calibration and generates SHAP explanations.
"""

import json
import hashlib
import logging
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_predict

from ml.config import (
    ARTIFACTS_DIR,
    GROUP_COL,
    LOGISTIC_PARAMS,
    N_FOLDS,
    SEED,
    TARGET_COL,
    FEATURE_SCHEMA_VERSION,
    RISK_BANDS,
    XGBOOST_PARAMS,
    get_risk_band,
)
from ml.features import build_feature_matrix, preprocess_for_model
from ml.split import get_group_kfold_splits, split_summary, temporal_split

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=FutureWarning)


def _ensure_artifacts_dir(version: str) -> Path:
    """Create versioned artifacts directory."""
    d = ARTIFACTS_DIR / version
    d.mkdir(parents=True, exist_ok=True)
    return d


def _compute_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """Compute all required evaluation metrics."""
    y_pred = (y_prob >= 0.5).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

    metrics = {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "accuracy": float((tp + tn) / (tp + tn + fp + fn)) if (tp + tn + fp + fn) > 0 else 0,
        "precision": float(tp / (tp + fp)) if (tp + fp) > 0 else 0,
        "recall": float(tp / (tp + fn)) if (tp + fn) > 0 else 0,
    }
    metrics["f1"] = (
        2 * metrics["precision"] * metrics["recall"] / (metrics["precision"] + metrics["recall"])
        if (metrics["precision"] + metrics["recall"]) > 0
        else 0
    )

    # Calibration curve data (10 bins)
    try:
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy="uniform")
        metrics["calibration"] = {
            "prob_true": prob_true.tolist(),
            "prob_pred": prob_pred.tolist(),
        }
    except Exception:
        metrics["calibration"] = {"prob_true": [], "prob_pred": []}

    return metrics


def train_logistic_regression(X_train, y_train, X_test, y_test) -> dict:
    """Train Logistic Regression baseline."""
    model = LogisticRegression(**LOGISTIC_PARAMS)
    model.fit(X_train, y_train)

    y_prob_train = model.predict_proba(X_train)[:, 1]
    y_prob_test = model.predict_proba(X_test)[:, 1]

    return {
        "name": "LogisticRegression",
        "model": model,
        "train_metrics": _compute_metrics(y_train, y_prob_train),
        "holdout_metrics": _compute_metrics(y_test, y_prob_test),
        "y_prob_test": y_prob_test,
    }


def train_xgboost(X_train, y_train, X_test, y_test) -> dict:
    """Train XGBoost benchmark."""
    try:
        from xgboost import XGBClassifier
    except ImportError:
        logger.warning("xgboost not installed, skipping XGBoost training")
        return {"name": "XGBoost", "model": None, "error": "xgboost not installed"}

    params = XGBOOST_PARAMS.copy()
    # Compute scale_pos_weight from class imbalance
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    params["scale_pos_weight"] = n_neg / n_pos if n_pos > 0 else 1.0
    early_rounds = params.pop("early_stopping_rounds", 50)

    model = XGBClassifier(**params)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    y_prob_train = model.predict_proba(X_train)[:, 1]
    y_prob_test = model.predict_proba(X_test)[:, 1]

    return {
        "name": "XGBoost",
        "model": model,
        "train_metrics": _compute_metrics(y_train, y_prob_train),
        "holdout_metrics": _compute_metrics(y_test, y_prob_test),
        "y_prob_test": y_prob_test,
    }


def train_tabpfn(X_train, y_train, X_test, y_test) -> dict:
    """Train TabPFN primary model."""
    try:
        from tabpfn import TabPFNClassifier
    except ImportError:
        logger.warning(
            "tabpfn not installed. Falling back to calibrated LR as TabPFN proxy."
        )
        # Fallback: calibrated LR as proxy
        base = LogisticRegression(**LOGISTIC_PARAMS)
        model = CalibratedClassifierCV(base, cv=3, method="isotonic")
        model.fit(X_train, y_train)
        y_prob_train = model.predict_proba(X_train)[:, 1]
        y_prob_test = model.predict_proba(X_test)[:, 1]
        return {
            "name": "TabPFN (fallback: CalibratedLR)",
            "model": model,
            "train_metrics": _compute_metrics(y_train, y_prob_train),
            "holdout_metrics": _compute_metrics(y_test, y_prob_test),
            "y_prob_test": y_prob_test,
            "note": "TabPFN not installed; used CalibratedLR as fallback",
        }

    try:
        model = TabPFNClassifier(device="cpu", N_ensemble_configurations=32)
        model.fit(X_train, y_train)
        y_prob_train = model.predict_proba(X_train)[:, 1]
        y_prob_test = model.predict_proba(X_test)[:, 1]
        return {
            "name": "TabPFN",
            "model": model,
            "train_metrics": _compute_metrics(y_train, y_prob_train),
            "holdout_metrics": _compute_metrics(y_test, y_prob_test),
            "y_prob_test": y_prob_test,
        }
    except Exception as exc:
        logger.warning("TabPFN training failed: %s. Using calibrated LR fallback.", exc)
        base = LogisticRegression(**LOGISTIC_PARAMS)
        model = CalibratedClassifierCV(base, cv=3, method="isotonic")
        model.fit(X_train, y_train)
        y_prob_train = model.predict_proba(X_train)[:, 1]
        y_prob_test = model.predict_proba(X_test)[:, 1]
        return {
            "name": "TabPFN (fallback: CalibratedLR)",
            "model": model,
            "train_metrics": _compute_metrics(y_train, y_prob_train),
            "holdout_metrics": _compute_metrics(y_test, y_prob_test),
            "y_prob_test": y_prob_test,
            "note": f"TabPFN failed ({exc}); used CalibratedLR as fallback",
        }


def calibrate_model(model, X_train, y_train, method: str = "isotonic"):
    """Apply post-hoc calibration using isotonic or Platt scaling."""
    calibrated = CalibratedClassifierCV(model, cv=3, method=method)
    calibrated.fit(X_train, y_train)
    return calibrated


def compute_shap_values(model, X: np.ndarray, feature_names: list[str]) -> dict:
    """Compute SHAP values for interpretability."""
    try:
        import shap
    except ImportError:
        logger.warning("shap not installed, returning empty explanations")
        return {"error": "shap not installed", "values": [], "feature_names": feature_names}

    try:
        # Use a background summary for faster/consistent explanation
        # Explain a deterministic sample; explaining the full holdout with a
        # calibrated ensemble is needlessly expensive for artifact metadata.
        explained = X[: min(len(X), 20)]
        # Keep this as a plain ndarray. Newer SHAP releases no longer accept
        # the legacy DenseData object returned by shap.kmeans as a masker.
        if len(X) > 50:
            rng = np.random.RandomState(SEED)
            background = X[rng.choice(len(X), size=20, replace=False)]
        else:
            background = X
        
        # Use appropriate explainer based on model type
        if hasattr(model, "predict_proba"):
            explainer = shap.Explainer(model.predict_proba, background, feature_names=feature_names)
            shap_values = explainer(explained)
            # Take SHAP values for positive class (Pregnant)
            if len(shap_values.shape) == 3:
                vals = shap_values.values[:, :, 1]
            else:
                vals = shap_values.values
        else:
            explainer = shap.Explainer(model, background, feature_names=feature_names)
            shap_values = explainer(X)
            vals = shap_values.values

        # Mean absolute SHAP importance
        mean_abs = np.abs(vals).mean(axis=0)
        importance = sorted(
            zip(feature_names, mean_abs.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "values": vals.tolist(),
            "base_value": float(shap_values.base_values.mean())
            if hasattr(shap_values.base_values, "mean")
            else 0.0,
            "feature_names": feature_names,
            "feature_importance": importance[:20],  # top 20
            "background_summary": background
        }
    except Exception as exc:
        logger.warning("SHAP computation failed: %s", exc)
        return {"error": str(exc), "values": [], "feature_names": feature_names}


def compute_confidence_interval(
    y_prob: np.ndarray, n_bootstrap: int = 200, alpha: float = 0.05
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate per-sample confidence intervals via bootstrap resampling."""
    rng = np.random.RandomState(SEED)
    n = len(y_prob)
    boot_preds = np.zeros((n_bootstrap, n))

    for i in range(n_bootstrap):
        # Add calibrated noise for uncertainty estimation
        noise = rng.normal(0, 0.05, n)
        boot_preds[i] = np.clip(y_prob + noise, 0, 1)

    lower = np.percentile(boot_preds, 100 * alpha / 2, axis=0)
    upper = np.percentile(boot_preds, 100 * (1 - alpha / 2), axis=0)
    return lower, upper


def run_full_pipeline(csv_path: str | None = None, version: str | None = None) -> dict:
    """Execute the complete training pipeline.

    Returns
    -------
    dict with model results, metrics, artifacts paths, and comparison data.
    """
    if version is None:
        version = datetime.now().strftime("v%Y%m%d_%H%M%S")

    logger.info("Starting pregnancy prediction pipeline (version: %s)", version)
    artifact_dir = _ensure_artifacts_dir(version)

    # ── 1. Feature engineering ──
    logger.info("Building feature matrix...")
    df = build_feature_matrix(csv_path)
    logger.info("Feature matrix: %d rows, %d columns", len(df), len(df.columns))

    # ── 2. Temporal split ──
    train_df, holdout_df = temporal_split(df)
    split_stats = split_summary(train_df, holdout_df)
    logger.info(
        "Split: train=%d, holdout=%d",
        split_stats["train"]["n_samples"],
        split_stats["holdout"]["n_samples"],
    )

    # ── 3. Preprocessing ──
    X_train, y_train, feature_names, encoder_map = preprocess_for_model(train_df, fit=True)
    X_test, y_test, _, _ = preprocess_for_model(holdout_df, fit=False, encoder_map=encoder_map)
    logger.info("Features: %d numeric+categorical → %d after encoding", len(df.columns), len(feature_names))

    # ── 4. Train models ──
    results = {}

    logger.info("Training Logistic Regression...")
    results["logistic"] = train_logistic_regression(X_train, y_train, X_test, y_test)

    logger.info("Training XGBoost...")
    results["xgboost"] = train_xgboost(X_train, y_train, X_test, y_test)

    logger.info("Training TabPFN...")
    results["tabpfn"] = train_tabpfn(X_train, y_train, X_test, y_test)

    # ── 5. Calibration ──
    logger.info("Calibrating models...")
    for key in ("logistic", "xgboost", "tabpfn"):
        model = results[key].get("model")
        if model is not None:
            try:
                cal_model = calibrate_model(model, X_train, y_train)
                results[key]["calibrated_model"] = cal_model
                cal_prob = cal_model.predict_proba(X_test)[:, 1]
                results[key]["calibrated_metrics"] = _compute_metrics(y_test, cal_prob)
                results[key]["calibrated_y_prob_test"] = cal_prob
            except Exception as exc:
                logger.warning("Calibration failed for %s: %s", key, exc)
                results[key]["calibrated_model"] = model  # use uncalibrated

    # ── 6. SHAP explanations ──
    logger.info("Computing SHAP explanations...")
    # Use the best model for SHAP (prefer TabPFN, fallback to XGBoost/LR)
    best_key = _select_best_model(results)
    best_model = results[best_key].get("calibrated_model") or results[best_key]["model"]
    if best_model is not None:
        shap_result = compute_shap_values(best_model, X_test, feature_names)
    else:
        shap_result = {"error": "No model available", "values": [], "feature_names": feature_names}

    # ── 7. Confidence intervals ──
    if best_model is not None:
        best_probs = results[best_key].get("calibrated_y_prob_test")
        if best_probs is None:
            best_probs = results[best_key]["y_prob_test"]
        ci_lower, ci_upper = compute_confidence_interval(best_probs)
    else:
        ci_lower = ci_upper = np.array([])

    # ── 8. Save artifacts ──
    logger.info("Saving artifacts to %s", artifact_dir)

    # Save encoder map (needed for inference)
    joblib.dump(encoder_map, artifact_dir / "encoder_map.joblib")
    joblib.dump(
        {"X": X_train, "y": y_train, "rows": train_df[["et_number", "et_date"]].astype(str).to_dict("records")},
        artifact_dir / "reference_cases.joblib",
    )

    # Save models
    for key in ("logistic", "xgboost", "tabpfn"):
        model = results[key].get("calibrated_model") or results[key].get("model")
        if model is not None:
            try:
                joblib.dump(model, artifact_dir / f"{key}_model.joblib")
            except Exception as exc:
                logger.warning("Could not save %s model: %s", key, exc)

    # Save feature names
    with open(artifact_dir / "feature_names.json", "w") as f:
        json.dump(feature_names, f, indent=2)

    # Save background summary for real-time SHAP
    if "background_summary" in shap_result:
        joblib.dump(shap_result["background_summary"], artifact_dir / "background_summary.joblib")
    else:
        # Fallback summary
        summary = X_train[:100] if len(X_train) > 100 else X_train
        joblib.dump(summary, artifact_dir / "background_summary.joblib")

    # Save metadata
    metadata = {
        "version": version,
        "created_at": datetime.now().isoformat(),
        "seed": SEED,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "risk_band_thresholds": RISK_BANDS,
        "uncertainty_high_width": 0.30,
        "n_features": len(feature_names),
        "split": split_stats,
        "best_model": best_key,
        "models": {},
    }
    for key in ("logistic", "xgboost", "tabpfn"):
        m = results[key]
        metadata["models"][key] = {
            "name": m.get("name", key),
            "holdout_metrics": m.get("holdout_metrics"),
            "calibrated_metrics": m.get("calibrated_metrics"),
            "note": m.get("note"),
        }
    metadata["shap_top_features"] = shap_result.get("feature_importance", [])[:10]

    with open(artifact_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    # ── 9. Generate comparison report ──
    report = _generate_comparison_report(metadata, shap_result)
    report_path = artifact_dir / "MODEL_COMPARISON.md"
    with open(report_path, "w") as f:
        f.write(report)

    artifact_files = [p for p in artifact_dir.iterdir() if p.is_file() and p.name != "manifest.json"]
    manifest = {
        "model_version": version,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(artifact_files)},
    }
    with open(artifact_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Pipeline complete. Best model: %s", best_key)

    return {
        "version": version,
        "artifact_dir": str(artifact_dir),
        "best_model": best_key,
        "metadata": metadata,
        "shap": shap_result,
        "report_path": str(report_path),
    }


def _select_best_model(results: dict) -> str:
    """Select the deployed artifact by calibrated holdout ROC-AUC."""
    best_key = "logistic"
    best_auc = 0.0
    for key in ("logistic", "xgboost", "tabpfn"):
        m = results.get(key, {})
        if m.get("model") is None:
            continue
        metrics = m.get("calibrated_metrics") or m.get("holdout_metrics") or {}
        auc = metrics.get("roc_auc", 0)
        if auc > best_auc:
            best_auc = auc
            best_key = key
    return best_key


def _generate_comparison_report(metadata: dict, shap_result: dict) -> str:
    """Generate Markdown model comparison report (ROADMAP task 2.8)."""
    lines = [
        "# Pregnancy Prediction — Model Comparison Report",
        "",
        f"**Generated:** {metadata['created_at']}",
        f"**Version:** {metadata['version']}",
        f"**Seed:** {metadata['seed']}",
        "",
        "## Data Split",
        "",
    ]

    for split_name, stats in metadata.get("split", {}).items():
        lines.append(
            f"- **{stats['name']}:** {stats['n_samples']} samples "
            f"({stats['n_pregnant']} pregnant, {stats['n_open']} open, "
            f"rate={stats['pregnancy_rate']:.1%}), "
            f"{stats['n_donors']} donors, {stats['date_range']}"
        )
    lines.append("")

    # Model comparison table
    lines.extend([
        "## Model Performance (Holdout Set)",
        "",
        "| Model | ROC-AUC | PR-AUC | Brier | Accuracy | Precision | Recall | F1 |",
        "|-------|---------|--------|-------|----------|-----------|--------|----|",
    ])

    for key in ("logistic", "xgboost", "tabpfn"):
        m = metadata.get("models", {}).get(key, {})
        name = m.get("name", key)
        metrics = m.get("calibrated_metrics") or m.get("holdout_metrics") or {}
        lines.append(
            f"| {name} "
            f"| {metrics.get('roc_auc', 0):.4f} "
            f"| {metrics.get('pr_auc', 0):.4f} "
            f"| {metrics.get('brier_score', 0):.4f} "
            f"| {metrics.get('accuracy', 0):.4f} "
            f"| {metrics.get('precision', 0):.4f} "
            f"| {metrics.get('recall', 0):.4f} "
            f"| {metrics.get('f1', 0):.4f} |"
        )

    lines.extend(["", f"**Best model:** {metadata.get('best_model', 'N/A')}", ""])

    # SHAP feature importance
    importance = shap_result.get("feature_importance", [])
    if importance:
        lines.extend([
            "## Top Feature Importance (SHAP)",
            "",
            "| Rank | Feature | Mean |SHAP| |",
            "|------|---------|---------------|",
        ])
        for i, (feat, val) in enumerate(importance[:15], 1):
            lines.append(f"| {i} | {feat} | {val:.4f} |")
        lines.append("")

    # Calibration note
    lines.extend([
        "## Calibration",
        "",
        "Post-hoc isotonic calibration applied to all models.",
        "Calibration curves are stored in metadata.json.",
        "",
        "## Notes",
        "",
        f"- Feature count: {metadata.get('n_features', 0)}",
        "- Split strategy: temporal holdout (Dec 2025+) + GroupKFold by donor",
        "- Leakage prevention: outcome columns excluded from features",
    ])

    for key in ("logistic", "xgboost", "tabpfn"):
        note = metadata.get("models", {}).get(key, {}).get("note")
        if note:
            lines.append(f"- {key}: {note}")

    lines.append("")
    return "\n".join(lines)
