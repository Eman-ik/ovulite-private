"""Embryo grading / similarity API endpoints.

Provides:
- POST /grade/embryo — upload image → Grade 1/2/3 prediction (real trained classifier)
- POST /grade/embryo-with-heatmap — same, plus a Grad-CAM visual explanation
- POST /grade/similar-cases — upload image → nearest visually-similar known cases
- GET  /grade/model-info — similarity model metadata
- POST /grade/upload — upload and store an embryo image

Note on history: /grade/embryo and /grade/embryo-with-heatmap were removed in
an earlier version of this router because the classifier had never been
trained on real labels — the local ET dataset's `Embryo Grade` column is
482/488 rows = Grade 1, no exploitable signal. /grade/similar-cases was
added as an honest replacement (SimCLR nearest-neighbor search, no labels
required). That gap is now closed: the same 482 images were verified
(MD5, byte-identical) to be a published, openly licensed dataset — Rocha
et al. 2017, Scientific Data — which carries real, varied expert grade
labels for those exact images. See
docs/dataset/external/rocha2017_bovine_blastocyst/DATASET_CARD.md and
ml/grading/real_labels.py / train_real_grading.py. /grade/embryo and
/grade/embryo-with-heatmap are restored here, now backed by a real trained
classifier — see GradePredictionResponse.caveats for what it does and does
not support (trained on an external dataset, not Ovulite's own farm data).
/grade/similar-cases remains available as a complementary tool.
"""

import hashlib
import io
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.grading import (
    GradePredictionResponse,
    GradePredictionWithHeatmapResponse,
    GradingModelInfo,
    ImageUploadResponse,
    SimilarCase,
    SimilarCaseMetadata,
    SimilarCasesResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Add project root to sys.path so ml package is importable
_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB


def _validate_and_normalize_image(image_bytes: bytes) -> tuple[bytes, int, int]:
    """Validate image bytes and normalize output while stripping metadata.

    Returns normalized image bytes, width, and height.
    """
    if len(image_bytes) == 0:
        raise HTTPException(400, "Empty image file")
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image too large (max 10MB)")

    try:
        from PIL import Image as PILImage

        # Ensure decoder is initialized and can read uploaded formats.
        PILImage.init()

        with PILImage.open(io.BytesIO(image_bytes)) as img:
            rgb = img.convert("RGB")
            width, height = rgb.size

        # Re-encode to strip EXIF and other metadata.
        sanitized = io.BytesIO()
        rgb.save(sanitized, format="JPEG", quality=95)
        sanitized_bytes = sanitized.getvalue()
        return sanitized_bytes, width, height
    except ImportError:
        logger.exception("Pillow is not installed; cannot process uploaded image")
        raise HTTPException(500, "Image processing backend is unavailable")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid image file")


def _get_similarity_index():
    """Lazy-load the singleton similarity index. Raises on failure (no fake fallback)."""
    from ml.grading.similarity import get_similarity_index

    return get_similarity_index()


def _get_grade_classifier():
    """Lazy-load the singleton grade classifier. Raises on failure (no fake fallback)."""
    from ml.grading.grade_classifier import get_grade_classifier

    return get_grade_classifier()


@router.post("/embryo", response_model=GradePredictionResponse)
async def grade_embryo(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    _current_user: User = Depends(get_current_user),
):
    """Predict embryo grade (1/2/3) for an uploaded image.

    Backed by a real trained classifier (ml/grading/train_real_grading.py)
    using the verified Rocha et al. 2017 grade labels — see
    GradePredictionResponse.caveats for scope and limitations.
    """
    raw_image_bytes = await image.read()
    image_bytes, _, _ = _validate_and_normalize_image(raw_image_bytes)

    try:
        classifier = _get_grade_classifier()
        result = classifier.predict(image_bytes)
    except FileNotFoundError as e:
        raise HTTPException(503, f"Embryo grade classifier not available: {e}")
    except ImportError as e:
        raise HTTPException(503, f"Grade classifier dependencies not available: {e}")
    except Exception as e:
        logger.exception("Grade prediction failed")
        raise HTTPException(500, f"Grade prediction failed: {str(e)}")

    return GradePredictionResponse(
        predicted_grade=result["predicted_grade"],
        predicted_label=result["predicted_label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        model_version=classifier.version,
        heatmap_available=True,
    )


@router.post("/embryo-with-heatmap", response_model=GradePredictionWithHeatmapResponse)
async def grade_embryo_with_heatmap(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    _current_user: User = Depends(get_current_user),
):
    """Predict embryo grade and return a Grad-CAM overlay explaining the prediction."""
    import base64

    raw_image_bytes = await image.read()
    image_bytes, _, _ = _validate_and_normalize_image(raw_image_bytes)

    try:
        classifier = _get_grade_classifier()
        result, overlay_bytes = classifier.predict_with_heatmap(image_bytes)
    except FileNotFoundError as e:
        raise HTTPException(503, f"Embryo grade classifier not available: {e}")
    except ImportError as e:
        raise HTTPException(503, f"Grade classifier dependencies not available: {e}")
    except Exception as e:
        logger.exception("Grade prediction with heatmap failed")
        raise HTTPException(500, f"Grade prediction failed: {str(e)}")

    return GradePredictionWithHeatmapResponse(
        predicted_grade=result["predicted_grade"],
        predicted_label=result["predicted_label"],
        confidence=result["confidence"],
        probabilities=result["probabilities"],
        model_version=classifier.version,
        heatmap_available=True,
        heatmap_image_base64=base64.b64encode(overlay_bytes).decode("ascii"),
    )


@router.post("/similar-cases", response_model=SimilarCasesResponse)
async def grade_similar_cases(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    k: int = Form(5, ge=1, le=20, description="Number of similar cases to return"),
    _current_user: User = Depends(get_current_user),
):
    """Find the k most visually similar known embryo cases for an uploaded image.

    This is a nearest-neighbor visual reference tool built on unsupervised
    SimCLR embeddings — it does NOT assign a grade or a calibrated confidence
    score. Use it to see which historical cases (and their recorded outcomes,
    where available) looked most similar to the new image.
    """
    raw_image_bytes = await image.read()
    image_bytes, _, _ = _validate_and_normalize_image(raw_image_bytes)

    try:
        index = _get_similarity_index()
        matches = index.find_similar(image_bytes, k=k)
    except FileNotFoundError as e:
        raise HTTPException(503, f"Embryo similarity model not available: {e}")
    except ImportError as e:
        raise HTTPException(503, f"Similarity model dependencies not available: {e}")
    except Exception as e:
        logger.exception("Similarity search failed")
        raise HTTPException(500, f"Similarity search failed: {str(e)}")

    return SimilarCasesResponse(
        matches=[
            SimilarCase(
                rank=m["rank"],
                filename=m["filename"],
                similarity=m["similarity"],
                metadata=SimilarCaseMetadata(**m["metadata"]),
            )
            for m in matches
        ],
        n_index_cases=len(index.filenames),
        model_type="simclr_efficientnet_b0",
    )


@router.get("/model-info", response_model=GradingModelInfo)
async def grading_model_info(_current_user: User = Depends(get_current_user)):
    """Return information about the current embryo-similarity model."""
    try:
        index = _get_similarity_index()
    except (FileNotFoundError, ImportError):
        return GradingModelInfo(
            model_type="SimCLR similarity index (unavailable)",
            backbone="efficientnet_b0",
            trained=False,
            n_index_cases=None,
            timestamp=None,
        )
    except Exception as e:
        logger.exception("Failed to get model info")
        raise HTTPException(500, str(e))

    return GradingModelInfo(
        model_type="SimCLR self-supervised similarity index",
        backbone="efficientnet_b0",
        trained=True,
        n_index_cases=len(index.filenames),
        timestamp=index.index_meta.get("timestamp"),
    )


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_embryo_image(
    image: UploadFile = File(..., description="Embryo image (any file format)"),
    embryo_id: int | None = Form(None, description="Optional embryo ID to link to"),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Upload and store an embryo image for later review.

    Saves the image to disk and creates a database record.
    """
    raw_image_bytes = await image.read()
    image_bytes, width, height = _validate_and_normalize_image(raw_image_bytes)

    # Compute hash for dedup
    file_hash = hashlib.sha256(image_bytes).hexdigest()

    # Save file
    upload_dir = _project_root / "uploads" / "embryo_images"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{file_hash[:16]}.jpg"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    relative_path = filepath.relative_to(_project_root).as_posix()

    # Store in DB using API dependency session (supports test overrides).
    try:
        from app.models.embryo_image import EmbryoImage

        record = EmbryoImage(
            embryo_id=embryo_id,
            file_path=relative_path,
            file_hash=file_hash,
            width_px=width,
            height_px=height,
            notes=notes,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return ImageUploadResponse(
            image_id=record.image_id,
            file_path=record.file_path,
            width_px=width,
            height_px=height,
        )
    except Exception as e:
        logger.warning(f"DB insert failed, returning file-only response: {e}")
        # Return without DB record if DB is unavailable
        return ImageUploadResponse(
            image_id=0,
            file_path=relative_path,
            width_px=width,
            height_px=height,
        )
