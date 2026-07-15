"""Ovulite ML pipeline configuration — feature definitions, paths, model params."""

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ML_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = ML_DIR / "artifacts"
DATA_CSV = PROJECT_ROOT / "docs" / "dataset" / "ovulite_cleaned_et_data.csv"

# ── Random seed for reproducibility ──────────────────────────
SEED = 42

# ── Target variable ──────────────────────────────────────────
TARGET_COL = "pregnancy_outcome"  # binary: 1=Pregnant, 0=Open

# ── Temporal split date (records on or after this go to holdout) ──
HOLDOUT_CUTOFF = "2025-12-01"

# ── Feature definitions (from REQUIREMENTS §3.4) ─────────────
NUMERIC_FEATURES = [
    "cl_measure_mm",
    "embryo_stage",
    "embryo_grade",
    "heat_day",
    "donor_bw_epd",
    "sire_bw_epd",
    "days_opu_to_et",
    "bc_score",
]

CATEGORICAL_FEATURES = [
    "cl_side",
    "protocol_name",
    "fresh_or_frozen",
    "technician_name",
    "donor_breed",
    "semen_type",
    "customer_id",
]

BINARY_FLAGS = [
    "bc_missing",  # derived: 1 if bc_score is NaN
]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES + BINARY_FLAGS

# ── Leakage exclusion list (REQUIREMENTS §3.3) ───────────────
LEAKAGE_COLUMNS = [
    "pc1_result",
    "pc1_date",
    "pc2_date",
    "pc2_result",
    "fetal_sexing",
    "days_in_pregnancy",
    "et_number",
    "lab",
    "satellite",
]

# ── GroupKFold grouping column ────────────────────────────────
GROUP_COL = "donor_tag"
N_FOLDS = 5

# ── Model hyperparameters ────────────────────────────────────
LOGISTIC_PARAMS = {
    "C": 1.0,
    "penalty": "l2",
    "class_weight": "balanced",
    "solver": "lbfgs",
    "max_iter": 1000,
    "random_state": SEED,
}

XGBOOST_PARAMS = {
    "max_depth": 4,
    "learning_rate": 0.05,
    "n_estimators": 500,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "scale_pos_weight": None,  # computed from class balance
    "eval_metric": "logloss",
    "early_stopping_rounds": 50,
    "random_state": SEED,
    "use_label_encoder": False,
}

# ── Risk band thresholds ─────────────────────────────────────
RISK_BANDS = {"low_max": 0.35, "high_min": 0.65}
FEATURE_SCHEMA_VERSION = "pregnancy_features_v1.0"


def get_risk_band(probability: float, thresholds: dict | None = None) -> str:
    """Return risk band using business-rule thresholds.

    - High: probability > 0.6
    - Medium: 0.3 <= probability <= 0.6
    - Low: probability < 0.3
    """
    thresholds = thresholds or RISK_BANDS
    if probability >= thresholds["high_min"]:
        return "High"
    if probability >= thresholds["low_max"]:
        return "Moderate"
    return "Low"
