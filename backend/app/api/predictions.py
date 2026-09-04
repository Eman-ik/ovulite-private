"""Prediction API — POST /predict/pregnancy → P + CI + SHAP (ROADMAP task 2.9).

Loads trained model artifacts and serves real-time pregnancy predictions
with uncertainty estimates and SHAP explanations.
"""

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import (
    ModelInfoResponse,
    PredictionHistoryItem,
    PredictionHistoryResponse,
    PredictionInput,
    PredictionOutcomeInput,
    PredictionOutput,
    PredictionSelectionInput,
    ShapContribution,
    ShapExplanation,
)

# Add project root to path so ml package is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_predictor():
    """Lazy-load the ML predictor (singleton)."""
    try:
        from ml.predict import get_predictor

        return get_predictor()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No trained model found: {exc}",
        )
    except Exception as exc:
        logger.error("Failed to load predictor: %s", exc)
        raise HTTPException(status_code=503, detail=f"Model loading error: {exc}")


@router.post("/pregnancy", response_model=PredictionOutput)
def predict_pregnancy(
    input_data: PredictionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict pregnancy probability for an ET transfer.

    Returns probability, 95% confidence interval, risk band, and SHAP
    feature contributions.
    """
    predictor = _get_predictor()

    # Build features dict from input
    features = input_data.model_dump(exclude={"transfer_id"}, exclude_none=False)

    try:
        result = predictor.predict(features)
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Prediction error: {exc}")

    # Build SHAP explanation
    shap_raw = result.get("shap_values", {})
    contributions = [
        ShapContribution(feature=feat, value=val)
        for feat, val in shap_raw.get("contributions", [])
    ]
    shap_explanation = ShapExplanation(
        base_value=shap_raw.get("base_value", 0),
        contributions=contributions,
        method=shap_raw.get("method", "shap"),
    )
    request_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    positive = [feat for feat, value in shap_raw.get("contributions", []) if value > 0][:3]
    negative = [feat for feat, value in shap_raw.get("contributions", []) if value < 0][:3]
    summary = (
        f"Estimated pregnancy probability is {result['probability_percent']:.1f}% "
        f"({result['risk_band']} band, {result['uncertainty_level'].lower()} uncertainty)."
    )
    if result.get("is_ood"):
        summary += " This case is outside the model's usual training experience and should be interpreted with extra caution."
    if positive:
        summary += f" Supporting factors include {', '.join(positive)}."
    if negative:
        summary += f" Factors reducing the estimate include {', '.join(negative)}."

    # Persist prediction to DB
    prediction_record = Prediction(
        transfer_id=input_data.transfer_id,
        organization_id=current_user.organization_id,
        model_name=result["model_name"],
        model_version=result["model_version"],
        probability=result["probability"],
        confidence_lower=result["confidence_lower"],
        confidence_upper=result["confidence_upper"],
        risk_band=result["risk_band"],
        shap_json={
            "base_value": shap_raw.get("base_value", 0),
            "contributions": shap_raw.get("contributions", []),
            "method": shap_raw.get("method", "shap"),
        },
        feature_snapshot=features,
        feature_schema_version=result["feature_schema_version"],
        request_id=request_id,
        uncertainty_level=result["uncertainty_level"],
        is_ood=result["is_ood"],
        ood_reasons=result["ood_reasons"],
        similar_cases=result["similar_cases"],
        plain_language_summary=summary,
    )
    db.add(prediction_record)
    db.commit()
    db.refresh(prediction_record)

    return PredictionOutput(
        probability=result["probability"],
        probability_percent=result["probability_percent"],
        confidence_lower=result["confidence_lower"],
        confidence_upper=result["confidence_upper"],
        risk_band=result["risk_band"],
        uncertainty_level=result["uncertainty_level"],
        is_ood=result["is_ood"],
        ood_reasons=result["ood_reasons"],
        similar_cases=result["similar_cases"],
        plain_language_summary=summary,
        feature_schema_version=result["feature_schema_version"],
        request_id=request_id,
        created_at=created_at,
        model_name=result["model_name"],
        model_version=result["model_version"],
        shap_explanation=shap_explanation,
        prediction_id=prediction_record.prediction_id,
    )


@router.get("/model-info", response_model=ModelInfoResponse)
def get_model_info(current_user: User = Depends(get_current_user)):
    """Return information about the currently loaded prediction model."""
    predictor = _get_predictor()
    metadata = predictor.metadata

    return ModelInfoResponse(
        model_name=predictor.model_name,
        model_version=predictor.version,
        n_features=len(predictor.feature_names),
        best_model_key=metadata.get("best_model", "unknown"),
        feature_schema_version=metadata.get("feature_schema_version", "unknown"),
        artifact_integrity_verified=(predictor.artifact_dir / "manifest.json").exists(),
        training_split=metadata.get("split", {}),
        top_features=metadata.get("shap_top_features", []),
    )


@router.get("/history", response_model=PredictionHistoryResponse)
def get_prediction_history(
    transfer_id: int | None = Query(None, description="Filter by transfer ID"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve prediction history, optionally filtered by transfer_id."""
    query = db.query(Prediction).filter(Prediction.organization_id == current_user.organization_id)
    
    if transfer_id is not None:
        query = query.filter(Prediction.transfer_id == transfer_id)
    
    # Order by most recent first
    query = query.order_by(Prediction.predicted_at.desc())
    
    # Get total count before applying limit
    total = query.count()
    
    # Apply limit
    predictions = query.limit(limit).all()
    
    # Convert to response schema
    items = [
        PredictionHistoryItem(
            prediction_id=pred.prediction_id,
            transfer_id=pred.transfer_id,
            model_name=pred.model_name,
            model_version=pred.model_version,
            probability=float(pred.probability),
            confidence_lower=float(pred.confidence_lower) if pred.confidence_lower else None,
            confidence_upper=float(pred.confidence_upper) if pred.confidence_upper else None,
            risk_band=pred.risk_band,
            predicted_at=pred.predicted_at,
            shap_json=pred.shap_json,
            request_id=pred.request_id,
            uncertainty_level=pred.uncertainty_level,
            is_ood=pred.is_ood,
            selected_for_case=pred.selected_for_case,
            actual_outcome=pred.actual_outcome,
        )
        for pred in predictions
    ]
    
    return PredictionHistoryResponse(predictions=items, total=total)


def _owned_prediction(prediction_id: int, db: Session, user: User) -> Prediction:
    prediction = db.query(Prediction).filter(
        Prediction.prediction_id == prediction_id,
        Prediction.organization_id == user.organization_id,
    ).first()
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction


@router.patch("/{prediction_id}/selection", response_model=PredictionHistoryItem)
def select_prediction(prediction_id: int, payload: PredictionSelectionInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prediction = _owned_prediction(prediction_id, db, current_user)
    prediction.selected_for_case = payload.selected
    db.commit()
    db.refresh(prediction)
    return PredictionHistoryItem.model_validate(prediction, from_attributes=True)


@router.patch("/{prediction_id}/outcome", response_model=PredictionHistoryItem)
def record_prediction_outcome(prediction_id: int, payload: PredictionOutcomeInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prediction = _owned_prediction(prediction_id, db, current_user)
    prediction.actual_outcome = payload.actual_outcome
    prediction.actual_outcome_recorded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prediction)
    return PredictionHistoryItem.model_validate(prediction, from_attributes=True)

