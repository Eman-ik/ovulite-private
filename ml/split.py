"""Leakage-safe data splitting — temporal holdout + GroupKFold by donor.

Implements the split strategy from REQUIREMENTS §3.2:
1. Temporal holdout: records from Dec 2025+ reserved as final test
2. Training set: records up through Nov 2025
3. Cross-validation: 5-fold GroupKFold grouped by donor_tag
"""

import pandas as pd
from sklearn.model_selection import GroupKFold

from ml.config import GROUP_COL, HOLDOUT_CUTOFF, N_FOLDS, SEED


def temporal_split(
    df: pd.DataFrame,
    cutoff: str = HOLDOUT_CUTOFF,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split into training and holdout sets by date.

    Parameters
    ----------
    df : Feature matrix with 'et_date' column
    cutoff : ISO date string; records >= this go to holdout

    Returns
    -------
    train_df, holdout_df
    """
    cutoff_date = pd.to_datetime(cutoff)
    mask = df["et_date"] < cutoff_date
    # Dataset refreshes do not always cross the configured calendar cutoff.
    # Reserve the latest 20% chronologically so evaluation never uses training rows.
    if mask.all() or (~mask).all():
        ordered = df.sort_values("et_date", kind="stable")
        holdout_size = max(1, int(round(len(ordered) * 0.2)))
        holdout_indices = ordered.tail(holdout_size).index
        mask = ~df.index.isin(holdout_indices)
    train = df[mask].copy().reset_index(drop=True)
    holdout = df[~mask].copy().reset_index(drop=True)
    return train, holdout


def get_group_kfold_splits(
    df: pd.DataFrame,
    n_folds: int = N_FOLDS,
) -> list[tuple[list[int], list[int]]]:
    """Generate GroupKFold splits grouped by donor.

    Parameters
    ----------
    df : Training DataFrame with GROUP_COL column
    n_folds : Number of folds

    Returns
    -------
    List of (train_indices, val_indices) tuples
    """
    groups = df[GROUP_COL].fillna("UNKNOWN").values
    gkf = GroupKFold(n_splits=n_folds)
    # GroupKFold needs X and y but only uses groups for splitting
    X_dummy = df.index.values.reshape(-1, 1)
    y_dummy = df.iloc[:, 0].values
    splits = list(gkf.split(X_dummy, y_dummy, groups=groups))
    return splits


def split_summary(train_df: pd.DataFrame, holdout_df: pd.DataFrame) -> dict:
    """Generate summary statistics for the data split."""
    from ml.config import TARGET_COL

    def _stats(df: pd.DataFrame, name: str) -> dict:
        n = len(df)
        n_pos = int(df[TARGET_COL].sum()) if TARGET_COL in df.columns else 0
        n_neg = n - n_pos
        rate = n_pos / n if n > 0 else 0
        n_donors = df[GROUP_COL].nunique() if GROUP_COL in df.columns else 0
        date_range = ""
        if "et_date" in df.columns and n > 0:
            date_range = f"{df['et_date'].min().date()} to {df['et_date'].max().date()}"
        return {
            "name": name,
            "n_samples": n,
            "n_pregnant": n_pos,
            "n_open": n_neg,
            "pregnancy_rate": round(rate, 4),
            "n_donors": n_donors,
            "date_range": date_range,
        }

    return {
        "train": _stats(train_df, "Training"),
        "holdout": _stats(holdout_df, "Holdout"),
    }
