"""Embryo grade classifier inference (singleton, mirrors similarity.py / ml/predict.py).

Serves the model trained by train_real_grading.py: a 3-class IETS-style
grade classifier (1=excellent/good, 2=fair, 3=poor), trained on the verified
Rocha et al. 2017 labels — see docs/dataset/external/rocha2017_bovine_blastocyst/
DATASET_CARD.md and ml/grading/real_labels.py for provenance.
"""

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .config import REAL_GRADING_ARTIFACTS_DIR
from .real_labels import CLASS_NAMES, CLASS_TO_GRADE


class EmbryoGradeClassifierService:
    """Loads the trained grade classifier once and serves predictions + Grad-CAM."""

    def __init__(self, artifacts_dir: Path = REAL_GRADING_ARTIFACTS_DIR):
        if not HAS_TORCH:
            raise ImportError("PyTorch is required for embryo grade classification")

        import hashlib

        self.artifacts_dir = artifacts_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model_path = artifacts_dir / "grade_classifier.pt"
        metadata_path = artifacts_dir / "metadata.json"
        manifest_path = artifacts_dir / "manifest.json"

        if not model_path.exists():
            raise FileNotFoundError(
                f"No trained grade classifier found at {model_path}. "
                "Run `python -m ml.grading.train_real_grading` to train it."
            )
        if not metadata_path.exists():
            raise FileNotFoundError(f"No metadata.json found at {metadata_path}")

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            for name, expected in manifest.get("files", {}).items():
                candidate = artifacts_dir / name
                actual = (
                    hashlib.sha256(candidate.read_bytes()).hexdigest()
                    if candidate.exists()
                    else None
                )
                if actual != expected:
                    raise ValueError(f"Artifact integrity check failed for {name}")

        self.metadata = json.loads(metadata_path.read_text())
        self.version = self.metadata.get("trained_at", "unknown")

        from .models import EmbryoGradeClassifier

        self.model = EmbryoGradeClassifier(n_grades=3, freeze_backbone=True)
        state = torch.load(model_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

        logger.info(
            "Loaded embryo grade classifier v=%s test_acc=%.3f test_macro_f1=%.3f",
            self.version,
            self.metadata.get("test_metrics", {}).get("accuracy", float("nan")),
            self.metadata.get("test_metrics", {}).get("macro_f1", float("nan")),
        )

    def predict(self, image_bytes: bytes) -> dict:
        """Predict grade probabilities for raw image bytes."""
        from .preprocessing import load_image_from_bytes

        tensor = load_image_from_bytes(image_bytes).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()

        predicted_class = int(np.argmax(probs))
        return {
            "predicted_grade": CLASS_TO_GRADE[predicted_class],
            "predicted_label": CLASS_NAMES[predicted_class],
            "confidence": float(probs[predicted_class]),
            "probabilities": [
                {
                    "grade": CLASS_TO_GRADE[c],
                    "label": CLASS_NAMES[c],
                    "probability": float(probs[c]),
                }
                for c in range(3)
            ],
        }

    def predict_with_heatmap(self, image_bytes: bytes) -> tuple[dict, bytes]:
        """Predict grade and return a Grad-CAM overlay (JPEG bytes) explaining it."""
        from .models import GradCAMClassifier, generate_heatmap_overlay
        from .preprocessing import load_image_from_bytes

        tensor = load_image_from_bytes(image_bytes).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
        predicted_class = int(np.argmax(probs))

        cam = GradCAMClassifier(self.model)
        heatmap = cam.generate(tensor.clone(), target_class=predicted_class)
        overlay_bytes = generate_heatmap_overlay(image_bytes, heatmap)

        result = {
            "predicted_grade": CLASS_TO_GRADE[predicted_class],
            "predicted_label": CLASS_NAMES[predicted_class],
            "confidence": float(probs[predicted_class]),
            "probabilities": [
                {
                    "grade": CLASS_TO_GRADE[c],
                    "label": CLASS_NAMES[c],
                    "probability": float(probs[c]),
                }
                for c in range(3)
            ],
        }
        return result, overlay_bytes


_grade_classifier: EmbryoGradeClassifierService | None = None


def get_grade_classifier(artifacts_dir: Path = REAL_GRADING_ARTIFACTS_DIR) -> EmbryoGradeClassifierService:
    """Get or lazy-load the singleton grade classifier service."""
    global _grade_classifier
    if _grade_classifier is None:
        _grade_classifier = EmbryoGradeClassifierService(artifacts_dir=artifacts_dir)
    return _grade_classifier
