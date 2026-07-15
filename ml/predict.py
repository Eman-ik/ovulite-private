"""Inference helper — load trained model and predict for new inputs."""

import json
import hashlib
import logging
from pathlib import Path

import joblib
import numpy as np

from ml.config import ARTIFACTS_DIR, get_risk_band
from ml.train_pipeline import compute_confidence_interval

logger = logging.getLogger(__name__)


class PregnancyPredictor:
    """Stateful predictor that loads a trained model version and serves predictions."""

    def __init__(self, version: str | None = None):
        """Load model artifacts for the given version (or latest)."""
        if version:
            self.artifact_dir = ARTIFACTS_DIR / version
            self._validate_artifact_dir(self.artifact_dir)
        else:
            self.artifact_dir = self._resolve_latest_valid_artifact_dir()

        self.version = self.artifact_dir.name
        logger.info("Loading model artifacts from %s", self.artifact_dir)

        # Load encoder map
        self.encoder_map = joblib.load(self.artifact_dir / "encoder_map.joblib")

        # Load feature names
        with open(self.artifact_dir / "feature_names.json") as f:
            self.feature_names = json.load(f)

        # Load metadata to find best model
        with open(self.artifact_dir / "metadata.json") as f:
            self.metadata = json.load(f)
        self._verify_manifest()

        best_key = self.metadata.get("best_model", "logistic")

        # Load model (try calibrated first, then raw)
        model_path = self.artifact_dir / f"{best_key}_model.joblib"
        if not model_path.exists():
            # Fallback to any available model
            for fname in ("logistic_model.joblib", "xgboost_model.joblib", "tabpfn_model.joblib"):
                candidate = self.artifact_dir / fname
                if candidate.exists():
                    model_path = candidate
                    break
        if not model_path.exists():
            raise FileNotFoundError(
                f"No trained model file found under {self.artifact_dir}. "
                "Expected one of: logistic_model.joblib, xgboost_model.joblib, tabpfn_model.joblib"
            )

        self.model = joblib.load(model_path)
        self.model_name = self.metadata.get("models", {}).get(best_key, {}).get("name", best_key)
        
        # Load background summary for SHAP
        bg_path = self.artifact_dir / "background_summary.joblib"
        if bg_path.exists():
            self.background = joblib.load(bg_path)
            logger.info("Loaded SHAP background summary from %s", bg_path)
        else:
            self.background = None
            logger.warning("No SHAP background found. Contributions may be zero for this version.")

        logger.info("Loaded model: %s (version: %s)", self.model_name, self.version)

        reference_path = self.artifact_dir / "reference_cases.joblib"
        self.reference_cases = joblib.load(reference_path) if reference_path.exists() else None

    def _verify_manifest(self) -> None:
        path = self.artifact_dir / "manifest.json"
        if not path.exists():
            logger.warning("No artifact manifest found for legacy model %s", self.version)
            return
        manifest = json.loads(path.read_text())
        for name, expected in manifest.get("files", {}).items():
            candidate = self.artifact_dir / name
            actual = hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate.exists() else None
            if actual != expected:
                raise ValueError(f"Artifact integrity check failed for {name}")

    @staticmethod
    def _validate_artifact_dir(path: Path) -> None:
        required = ["encoder_map.joblib", "feature_names.json", "metadata.json"]
        missing = [name for name in required if not (path / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Model artifact directory is incomplete: {path}. Missing files: {', '.join(missing)}"
            )

    @classmethod
    def _resolve_latest_valid_artifact_dir(cls) -> Path:
        if not ARTIFACTS_DIR.exists():
            raise FileNotFoundError(f"No model artifacts found in {ARTIFACTS_DIR}")

        versions = [p for p in ARTIFACTS_DIR.iterdir() if p.is_dir() and p.name.startswith("v")]
        versions = sorted(versions, key=lambda p: p.stat().st_mtime)
        for candidate in reversed(versions):
            try:
                cls._validate_artifact_dir(candidate)
                return candidate
            except FileNotFoundError:
                continue

        raise FileNotFoundError(
            f"No complete model artifact set found in {ARTIFACTS_DIR}. "
            "Run training to generate versioned artifacts."
        )

    def predict(self, features: dict) -> dict:
        """Generate pregnancy prediction for a single transfer.

        Parameters
        ----------
        features : dict with canonical feature names as keys

        Returns
        -------
        dict with probability, confidence_lower, confidence_upper, risk_band, shap_values
        """
        import pandas as pd

        from ml.config import CATEGORICAL_FEATURES, NUMERIC_FEATURES
        from ml.features import preprocess_for_model

        # Build a single-row DataFrame
        row = {}
        for col in NUMERIC_FEATURES:
            val = features.get(col)
            row[col] = float(val) if val is not None else np.nan
        for col in CATEGORICAL_FEATURES:
            row[col] = features.get(col, "Unknown")

        row["bc_missing"] = 1 if (features.get("bc_score") is None or pd.isna(features.get("bc_score"))) else 0
        row["pregnancy_outcome"] = 0  # dummy, won't be used

        df = pd.DataFrame([row])

        X, _, _, _ = preprocess_for_model(df, fit=False, encoder_map=self.encoder_map)

        # Predict probability
        prob = float(self.model.predict_proba(X)[:, 1][0])

        # Confidence interval
        ci_lower, ci_upper = compute_confidence_interval(np.array([prob]))
        ci_lo = float(ci_lower[0])
        ci_hi = float(ci_upper[0])

        # Risk band
        band = get_risk_band(prob, self.metadata.get("risk_band_thresholds"))

        # SHAP values for this prediction
        shap_dict = self._compute_shap_single(X)

        width = ci_hi - ci_lo
        ood_reasons = self._ood_reasons(X, features)
        return {
            "probability": round(prob, 4),
            "confidence_lower": round(ci_lo, 4),
            "confidence_upper": round(ci_hi, 4),
            "risk_band": band,
            "probability_percent": round(prob * 100, 1),
            "uncertainty_level": "High" if width > self.metadata.get("uncertainty_high_width", 0.30) else ("Moderate" if width > 0.15 else "Low"),
            "is_ood": bool(ood_reasons),
            "ood_reasons": ood_reasons,
            "similar_cases": self._similar_cases(X),
            "feature_schema_version": self.metadata.get("feature_schema_version", "unknown"),
            "model_name": self.model_name,
            "model_version": self.version,
            "shap_values": shap_dict,
        }

    def _ood_reasons(self, X: np.ndarray, features: dict) -> list[str]:
        reasons = []
        if self.reference_cases is not None:
            ref = np.asarray(self.reference_cases["X"], dtype=float)
            lower, upper = np.percentile(ref, [1, 99], axis=0)
            unusual = np.flatnonzero((X[0] < lower) | (X[0] > upper))
            reasons.extend(f"{self.feature_names[i]} is outside the training reference range" for i in unusual[:5])
        for name in ("cl_side", "fresh_or_frozen", "semen_type", "protocol_name", "technician_name", "donor_breed"):
            value = str(features.get(name, "Unknown"))
            known = self.encoder_map.get(f"{name}_categories", [])
            if value not in known and value != "Unknown":
                reasons.append(f"Unseen {name} category: {value}")
        return reasons

    def _similar_cases(self, X: np.ndarray, limit: int = 5) -> list[dict]:
        if self.reference_cases is None:
            return []
        ref = np.asarray(self.reference_cases["X"], dtype=float)
        scale = np.std(ref, axis=0)
        scale[scale == 0] = 1.0
        distance = np.sqrt(np.mean(((ref - X[0]) / scale) ** 2, axis=1))
        cases = []
        for index in np.argsort(distance)[:limit]:
            row = self.reference_cases["rows"][int(index)]
            cases.append({"transfer_reference": row["et_number"], "et_date": row["et_date"], "outcome": int(self.reference_cases["y"][index]), "distance": round(float(distance[index]), 4)})
        return cases

    def _compute_shap_single(self, X: np.ndarray) -> dict:
        """Compute SHAP contribution for a single prediction."""
        # The deployed calibrated logistic model already provides a stable,
        # validated linear explanation surrogate. Using its coefficients keeps
        # online inference fast; generic permutation SHAP takes 20-30 seconds
        # per request on the supported farm hardware.
        calibrated = getattr(self.model, "calibrated_classifiers_", None)
        if calibrated:
            coefficient_rows = []
            for classifier in calibrated:
                estimator = getattr(classifier, "estimator", None)
                if estimator is not None and hasattr(estimator, "coef_"):
                    coefficient_rows.append(np.asarray(estimator.coef_[0], dtype=float))
            if coefficient_rows:
                coefficients = np.mean(coefficient_rows, axis=0)
                center = np.mean(self.background, axis=0) if self.background is not None else np.zeros(X.shape[1])
                values = coefficients * (X[0] - center)
                contributions = sorted(
                    zip(self.feature_names, values.tolist()),
                    key=lambda item: abs(item[1]),
                    reverse=True,
                )
                return {
                    "base_value": float(self.model.predict_proba(center.reshape(1, -1))[0, 1]),
                    "contributions": contributions[:15],
                    "method": "calibrated_linear_surrogate",
                }
        try:
            import shap

            # Use saved background if available, otherwise fallback to zero-vector to avoid 0s
            background = self.background
            if background is None:
                background = np.zeros_like(X)
            
            # Use appropriate explainer
            explainer = shap.Explainer(self.model.predict_proba, background, feature_names=self.feature_names)
            sv = explainer(X)
            
            if len(sv.shape) == 3:
                vals = sv.values[0, :, 1]
                base_val = float(sv.base_values[0, 1])
            else:
                vals = sv.values[0]
                base_val = float(sv.base_values[0])

            contributions = sorted(
                zip(self.feature_names, vals.tolist()),
                key=lambda x: abs(x[1]),
                reverse=True,
            )
            return {
                "base_value": base_val,
                "contributions": contributions[:15],
            }
        except Exception as exc:
            logger.warning("SHAP failed for single prediction: %s", exc)
            return {"base_value": 0, "contributions": []}


# Module-level singleton (lazy loaded)
_predictor: PregnancyPredictor | None = None


def get_predictor(version: str | None = None) -> PregnancyPredictor:
    """Get or lazy-load the singleton predictor."""
    global _predictor
    if _predictor is None or (version and _predictor.version != version):
        _predictor = PregnancyPredictor(version=version)
    return _predictor
