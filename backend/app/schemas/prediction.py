"""Pydantic schemas for pregnancy prediction API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PredictionInput(BaseModel):
    """Input features for pregnancy prediction.

    These map to the canonical feature set from REQUIREMENTS §3.4.
    Required fields enforce the business rule that prediction cannot run on incomplete ET input.
    """

    # Numeric features
    cl_measure_mm: float = Field(..., ge=0, le=50, description="CL diameter in mm")
    embryo_stage: int = Field(..., ge=1, le=9, description="IETS embryo stage")
    embryo_grade: Optional[int] = Field(None, ge=1, le=4, description="IETS embryo grade")
    heat_day: Optional[int] = Field(None, description="Days since heat")
    donor_bw_epd: Optional[float] = Field(None, description="Donor birth weight EPD")
    sire_bw_epd: Optional[float] = Field(None, description="Sire birth weight EPD")
    days_opu_to_et: Optional[int] = Field(None, description="Days from OPU to ET")
    bc_score: Optional[float] = Field(None, description="Body condition score")

    # Categorical features
    cl_side: Optional[str] = Field(None, description="CL side: Left or Right")
    protocol_name: Optional[str] = Field(None, description="Synchronization protocol name")
    fresh_or_frozen: Optional[str] = Field(None, description="Embryo preservation: Fresh or Frozen")
    technician_name: Optional[str] = Field(None, description="ET Technician name")
    donor_breed: Optional[str] = Field(None, description="Donor breed")
    semen_type: Optional[str] = Field(None, description="Semen type: Conventional, Sexed, etc.")
    customer_id: Optional[str] = Field(None, description="Customer identifier")

    # Optional: transfer_id for linking prediction to existing record
    transfer_id: Optional[int] = Field(None, description="Link prediction to existing transfer")


class ShapContribution(BaseModel):
    """Single SHAP feature contribution."""

    feature: str
    value: float


class ShapExplanation(BaseModel):
    """SHAP explanation for a prediction."""

    base_value: float = 0.0
    contributions: list[ShapContribution] = Field(default_factory=list)


class PredictionOutput(BaseModel):
    """Prediction result with probability, CI, risk band, and SHAP."""

    probability: float = Field(..., description="P(pregnant)")
    probability_percent: float
    confidence_lower: float = Field(..., description="Lower bound of 95% CI")
    confidence_upper: float = Field(..., description="Upper bound of 95% CI")
    risk_band: str = Field(..., description="Low / Moderate / High")
    uncertainty_level: str
    is_ood: bool = False
    ood_reasons: list[str] = Field(default_factory=list)
    similar_cases: list[dict] = Field(default_factory=list)
    plain_language_summary: str
    feature_schema_version: str
    request_id: str
    created_at: datetime
    model_name: str = Field(..., description="Name of model used")
    model_version: str = Field(..., description="Model artifact version")
    shap_explanation: ShapExplanation = Field(
        default_factory=ShapExplanation,
        description="SHAP feature contributions",
    )
    prediction_id: Optional[int] = Field(None, description="DB prediction_id if persisted")


class ModelInfoResponse(BaseModel):
    """Information about the currently loaded model."""

    model_name: str
    model_version: str
    n_features: int
    best_model_key: str
    feature_schema_version: str = "unknown"
    artifact_integrity_verified: bool = False
    training_split: dict = Field(default_factory=dict)
    top_features: list = Field(default_factory=list)


class PredictionHistoryItem(BaseModel):
    """Single prediction history record."""

    prediction_id: int
    transfer_id: Optional[int] = None
    model_name: str
    model_version: Optional[str] = None
    probability: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    risk_band: Optional[str] = None
    predicted_at: datetime
    shap_json: Optional[dict] = None
    request_id: Optional[str] = None
    uncertainty_level: Optional[str] = None
    is_ood: bool = False
    selected_for_case: bool = False
    actual_outcome: Optional[str] = None


class PredictionHistoryResponse(BaseModel):
    """List of prediction history records."""

    predictions: list[PredictionHistoryItem]
    total: int


class PredictionOutcomeInput(BaseModel):
    actual_outcome: str = Field(pattern="^(Pregnant|Open)$")


class PredictionSelectionInput(BaseModel):
    selected: bool = True



