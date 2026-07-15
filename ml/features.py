"""Canonical, leakage-safe feature preparation for pregnancy prediction."""

import re

import numpy as np
import pandas as pd

from ml.config import CATEGORICAL_FEATURES, DATA_CSV, NUMERIC_FEATURES, TARGET_COL


_COL_MAP = {
    "# ET": "et_number",
    "ET Date": "et_date",
    "Customer ID": "customer_id",
    "ET Location (recipient farm)": "farm_location",
    "ET Location": "farm_location",
    "Recipient ID": "recipient_tag",
    "Cow/Heifer": "cow_or_heifer",
    "BC Score": "bc_score",
    "BCScore": "bc_score",
    "CL Side": "cl_side",
    "CL measure (mm)": "cl_measure_mm",
    "Protocol": "protocol_name",
    "Fresh or Frozen": "fresh_or_frozen",
    "ET Tech": "technician_name",
    "Embryo Stage 4-8": "embryo_stage",
    "Embryo Grade": "embryo_grade",
    "Heat day": "heat_day",
    "1st PC Result": "pc1_result",
    "OPU Date": "opu_date",
    "Donor": "donor_tag",
    "Donor Breed": "donor_breed",
    "Donor BW EPD": "donor_bw_epd",
    "SIRE BW EPD": "sire_bw_epd",
    "Semen type": "semen_type",
}


def load_raw_csv(csv_path: str | None = None) -> pd.DataFrame:
    """Load a dataset-folder CSV without silently coercing identifiers."""
    return pd.read_csv(csv_path or DATA_CSV, dtype=str).dropna(how="all").reset_index(drop=True)


def _target_from_result(values: pd.Series) -> pd.Series:
    normalized = values.fillna("").astype(str).str.strip().str.lower()
    return normalized.map({"pregnant": 1, "p": 1, "positive": 1, "open": 0, "o": 0, "negative": 0})


def build_feature_matrix(csv_path: str | None = None) -> pd.DataFrame:
    """Return pre-transfer features plus target, donor group, and transfer date.

    Outcome/result columns are used only to construct the label and are never
    returned as model features.
    """
    raw = load_raw_csv(csv_path)
    rename = {column: _COL_MAP[column.strip()] for column in raw.columns if column.strip() in _COL_MAP}
    df = raw.rename(columns=rename).replace(r"^\s*[.\-]?\s*$", np.nan, regex=True)

    for column in ("et_date", "opu_date"):
        if column not in df:
            df[column] = pd.NaT
        df[column] = pd.to_datetime(df[column], errors="coerce")

    if "target_pregnant" in df:
        target = pd.to_numeric(df["target_pregnant"], errors="coerce")
    elif "pc1_result" in df:
        target = _target_from_result(df["pc1_result"])
    else:
        raise ValueError("Dataset has neither target_pregnant nor 1st PC Result")
    df[TARGET_COL] = target
    df = df[df[TARGET_COL].isin([0, 1]) & df["et_date"].notna()].copy()
    df[TARGET_COL] = df[TARGET_COL].astype(int)

    if "days_opu_to_et" not in df:
        df["days_opu_to_et"] = (df["et_date"] - df["opu_date"]).dt.days
    for column in NUMERIC_FEATURES:
        if column not in df:
            df[column] = np.nan
        df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in CATEGORICAL_FEATURES:
        if column not in df:
            df[column] = np.nan
    if "cl_side" in df:
        cl = df["cl_side"].astype("string").str.strip().str.title()
        df["cl_side"] = cl.where(cl.isin(["Left", "Right"]))
    if "semen_type" in df:
        df["semen_type"] = df["semen_type"].apply(
            lambda value: "Sexed" if pd.notna(value) and re.search(r"pre.?sort", str(value), re.I) else value
        )

    df["bc_missing"] = df["bc_score"].isna().astype(int)
    if "donor_tag" not in df:
        df["donor_tag"] = "UNKNOWN"
    if "et_number" not in df:
        df["et_number"] = df.index.astype(str)

    columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES + [
        "bc_missing", TARGET_COL, "donor_tag", "et_date", "et_number"
    ]
    return df[columns].reset_index(drop=True)


def preprocess_for_model(df, fit=True, encoder_map=None):
    """Median-impute numeric values and one-hot encode categoricals."""
    encoder_map = {} if encoder_map is None else encoder_map
    frame = df.copy()
    feature_names = []
    for column in NUMERIC_FEATURES:
        values = pd.to_numeric(frame.get(column, np.nan), errors="coerce")
        median = float(values.median()) if fit and pd.notna(values.median()) else float(encoder_map.get(f"{column}_median", 0.0))
        if fit:
            encoder_map[f"{column}_median"] = median
        frame[column] = values.fillna(median)
        feature_names.append(column)

    frame["bc_missing"] = pd.to_numeric(frame.get("bc_missing", 0), errors="coerce").fillna(0)
    feature_names.append("bc_missing")
    for column in CATEGORICAL_FEATURES:
        values = frame[column] if column in frame else pd.Series("Unknown", index=frame.index)
        values = values.fillna("Unknown").astype(str)
        categories = sorted(values.unique()) if fit else encoder_map.get(f"{column}_categories", [])
        if fit:
            encoder_map[f"{column}_categories"] = categories
        for category in categories:
            name = f"{column}__{category}"
            frame[name] = (values == category).astype(int)
            feature_names.append(name)

    X = frame[feature_names].to_numpy(dtype=np.float64)
    y = frame[TARGET_COL].to_numpy(dtype=int) if TARGET_COL in frame else np.zeros(len(frame), dtype=int)
    return X, y, feature_names, encoder_map
