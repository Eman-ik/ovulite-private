import pandas as pd

from ml.config import TARGET_COL
from ml.features import build_feature_matrix, preprocess_for_model
from ml.split import temporal_split


def test_curated_dataset_builds_leakage_safe_features():
    frame = build_feature_matrix()
    assert not frame.empty
    assert set(frame[TARGET_COL].unique()) == {0, 1}
    assert frame["et_date"].notna().all()
    assert "pc1_result" not in frame.columns
    assert "target_pregnant" not in frame.columns


def test_preprocessor_reuses_training_encoding_for_holdout():
    frame = build_feature_matrix()
    train, holdout = temporal_split(frame)
    X_train, y_train, names, encoding = preprocess_for_model(train, fit=True)
    X_holdout, y_holdout, holdout_names, _ = preprocess_for_model(
        holdout, fit=False, encoder_map=encoding
    )
    assert len(train) and len(holdout)
    assert X_train.shape[1] == X_holdout.shape[1]
    assert names == holdout_names
    assert len(y_train) == len(train)
    assert len(y_holdout) == len(holdout)


def test_temporal_split_falls_back_when_cutoff_is_outside_data():
    frame = pd.DataFrame(
        {"et_date": pd.date_range("2024-01-01", periods=10), TARGET_COL: [0, 1] * 5, "donor_tag": ["d"] * 10}
    )
    train, holdout = temporal_split(frame, cutoff="2030-01-01")
    assert len(train) == 8
    assert len(holdout) == 2
    assert train["et_date"].max() < holdout["et_date"].min()
