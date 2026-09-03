"""Pydantic schemas for embryo grading / similarity API.

Note: this module previously defined GradingResult / GradingResultWithHeatmap
for a Grade 1/2/3 + Grad-CAM classifier, removed because the local ET dataset's
"Embryo Grade" column is 482/488 = Grade 1 (no exploitable signal). That gap
is now closed: the 482 images were verified (MD5) to be a published, openly
licensed dataset (Rocha et al. 2017, Scientific Data) which carries real,
varied expert grade labels for those exact images — see
docs/dataset/external/rocha2017_bovine_blastocyst/DATASET_CARD.md and
ml/grading/real_labels.py. GradePrediction / GradePredictionResponse below
are the restored classifier endpoints, now backed by a real trained model
(ml/grading/train_real_grading.py). SimilarCase / SimilarCasesResponse remain
as a complementary nearest-neighbor lookup.
"""

from pydantic import BaseModel, Field


class GradeProbability(BaseModel):
    """Predicted probability for one grade class."""
    grade: int = Field(..., ge=1, le=3)
    label: str
    probability: float = Field(..., ge=0, le=1)


class GradePredictionResponse(BaseModel):
    """Response from the real, trained embryo grade classifier.

    Trained on Rocha et al. 2017's verified grade labels for these 482
    images (CC0/CC-BY, see DATASET_CARD.md) — NOT on Ovulite's own local
    ET records, which have no usable per-image grade ground truth. See
    `caveats` for what this model does and does not support.
    """
    predicted_grade: int = Field(..., ge=1, le=3, description="1=excellent/good, 2=fair, 3=poor")
    predicted_label: str
    confidence: float = Field(..., ge=0, le=1, description="Softmax probability of the predicted class")
    probabilities: list[GradeProbability]
    model_type: str = "efficientnet_b0_grade_classifier"
    model_version: str
    heatmap_available: bool = Field(
        ..., description="Whether a Grad-CAM heatmap can be requested via /grade/embryo-with-heatmap"
    )
    caveats: list[str] = Field(
        default_factory=lambda: [
            "Trained on an external published dataset (Rocha et al. 2017), not on "
            "Ovulite's own farm images — treat as decision support, not ground truth.",
            "482 total training images is a small sample; metrics are indicative.",
        ]
    )


class GradePredictionWithHeatmapResponse(GradePredictionResponse):
    """Same as GradePredictionResponse, plus a Grad-CAM visual explanation."""
    heatmap_image_base64: str = Field(
        ..., description="JPEG image (base64-encoded) — original image with Grad-CAM overlay"
    )


class GradingMetadata(BaseModel):
    """Optional metadata to improve grading accuracy."""
    embryo_stage: float | None = Field(None, ge=1, le=9, description="Embryo stage (4-8 typical)")
    embryo_grade: float | None = Field(None, ge=1, le=4, description="Manual embryo grade")
    donor_breed: str | None = Field(None, description="Donor breed")
    fresh_or_frozen: str | None = Field(None, description="Fresh or Frozen")
    technician_name: str | None = Field(None, description="ET technician name")


class SimilarCaseMetadata(BaseModel):
    """Whatever ET-record fields could be linked to a matched historical image.

    Every field is optional: linkage is positional (image sequence -> CSV row)
    and best-effort, so any field may be missing for a given match.
    """
    sequence_number: int | None = None
    et_number: str | None = None
    donor: str | None = None
    donor_breed: str | None = None
    et_date: str | None = None
    embryo_stage: str | None = None
    embryo_grade: str | None = None
    fresh_or_frozen: str | None = None
    technician_name: str | None = None
    pregnancy_outcome: str | None = None


class SimilarCase(BaseModel):
    """A single nearest-neighbor match from the embedding index."""
    rank: int = Field(..., ge=1, description="1 = most similar")
    filename: str = Field(..., description="Matched training image filename")
    similarity: float = Field(
        ..., ge=-1, le=1,
        description="Cosine similarity between SimCLR embeddings (higher = more visually similar). "
                    "This is a nearest-neighbor distance measure, not a calibrated confidence score.",
    )
    metadata: SimilarCaseMetadata


class SimilarCasesResponse(BaseModel):
    """Response from the embryo similarity-search endpoint.

    This intentionally does NOT include a grade, viability score, or
    confidence percentage — the AI here surfaces visually similar known
    cases for the embryologist to review, it does not classify or grade.
    """
    matches: list[SimilarCase]
    n_index_cases: int = Field(..., description="Total number of known cases in the similarity index")
    model_type: str = Field("simclr_efficientnet_b0", description="Embedding model used")


class ImageUploadResponse(BaseModel):
    """Response from image upload endpoint."""
    image_id: int
    file_path: str
    width_px: int | None = None
    height_px: int | None = None


class GradingModelInfo(BaseModel):
    """Info about the currently active embryo-similarity model.

    Field names are kept close to the legacy classifier schema where they
    still make sense (model_type, backbone, trained, timestamp) so existing
    API consumers degrade gracefully; grade-classifier-only fields
    (n_grades, grade_labels, best_val_acc, n_train/n_val) are gone since
    there is no grade classifier anymore.
    """
    model_type: str
    backbone: str
    trained: bool
    n_index_cases: int | None = None
    timestamp: str | None = None
