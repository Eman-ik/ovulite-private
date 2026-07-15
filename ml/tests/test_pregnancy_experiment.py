import numpy as np

from ml.pregnancy_prediction.experiment import _ensemble_weights, _metrics, _threshold


def test_ensemble_weights_are_nonnegative_and_sum_to_one():
    y = np.array([0, 0, 1, 1])
    predictions = np.array([[0.1, 0.4], [0.2, 0.3], [0.8, 0.6], [0.9, 0.7]])
    weights = _ensemble_weights(y, predictions)
    assert np.all(weights >= 0)
    assert np.isclose(weights.sum(), 1.0)


def test_metrics_and_threshold_use_probabilities_without_holdout_state():
    y = np.array([0, 0, 1, 1])
    probability = np.array([0.1, 0.3, 0.7, 0.9])
    threshold = _threshold(y, probability)
    metrics = _metrics(y, probability, threshold)
    assert 0.1 <= threshold <= 0.9
    assert metrics["roc_auc"] == 1.0
    assert metrics["brier_score"] < 0.1
