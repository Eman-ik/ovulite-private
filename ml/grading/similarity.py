"""Embryo similarity inference (singleton, mirrors ml/predict.py's get_predictor pattern).

This replaces the abandoned grade-classifier inference path (ml/grading/predict.py's
EmbryoGrader) with an honest nearest-neighbor lookup against the SimCLR embedding
index built by build_index.py: given a new embryo image, find the closest known
cases by visual similarity, no grade classification implied.
"""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .config import ARTIFACTS_DIR


class EmbryoSimilarityIndex:
    """Loads the SimCLR backbone + embedding index once and serves similarity queries."""

    def __init__(self, artifacts_dir: Path = ARTIFACTS_DIR):
        if not HAS_TORCH:
            raise ImportError("PyTorch is required for embryo similarity search")

        import joblib

        self.artifacts_dir = artifacts_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        backbone_path = artifacts_dir / "simclr_backbone.pt"
        index_path = artifacts_dir / "embedding_index.joblib"

        if not backbone_path.exists():
            raise FileNotFoundError(
                f"No SimCLR backbone found at {backbone_path}. "
                "Run `python -m ml.grading.run_training --simclr` to train it."
            )
        if not index_path.exists():
            raise FileNotFoundError(
                f"No embedding index found at {index_path}. "
                "Run `python -m ml.grading.build_index` to build it."
            )

        self.backbone = self._load_backbone(backbone_path)

        index = joblib.load(index_path)
        self.filenames: list[str] = index["filenames"]
        self.embeddings: np.ndarray = np.asarray(index["embeddings"], dtype=np.float32)
        self.metadata: list[dict] = index["metadata"]
        self.index_meta: dict = index.get("meta", {})

        logger.info(
            "Loaded embryo similarity index: %d cases, feature_dim=%d",
            len(self.filenames),
            self.embeddings.shape[1] if self.embeddings.ndim == 2 else -1,
        )

    def _load_backbone(self, backbone_path: Path):
        from torchvision.models import efficientnet_b0

        backbone = efficientnet_b0(weights=None)
        backbone.classifier = torch.nn.Identity()
        state = torch.load(backbone_path, map_location=self.device, weights_only=True)
        backbone.load_state_dict(state)
        backbone.to(self.device)
        backbone.eval()
        return backbone

    def _embed(self, image_bytes: bytes) -> np.ndarray:
        """Embed raw image bytes into a single L2-normalized feature vector."""
        from .preprocessing import load_image_from_bytes

        tensor = load_image_from_bytes(image_bytes).to(self.device)
        with torch.no_grad():
            feat = self.backbone(tensor)
        feat = feat.squeeze(0).cpu().numpy().astype(np.float32)
        norm = np.linalg.norm(feat)
        if norm > 0:
            feat = feat / norm
        return feat

    def find_similar(self, image_bytes: bytes, k: int = 5) -> list[dict]:
        """Return the top-k most visually similar known cases.

        Similarity is cosine similarity between SimCLR backbone embeddings
        (both index and query embeddings are L2-normalized, so this reduces
        to a dot product). This is a nearest-neighbor visual reference tool,
        not a calibrated grade or outcome prediction.
        """
        query = self._embed(image_bytes)
        scores = self.embeddings @ query  # cosine similarity, shape (N,)

        k = max(1, min(k, len(self.filenames)))
        top_idx = np.argsort(-scores)[:k]

        results = []
        for rank, idx in enumerate(top_idx, start=1):
            meta = dict(self.metadata[idx]) if idx < len(self.metadata) else {}
            results.append({
                "rank": rank,
                "filename": self.filenames[idx],
                "similarity": round(float(scores[idx]), 4),
                "metadata": meta,
            })
        return results


# ── Module-level singleton (lazy loaded), mirrors ml/predict.py's get_predictor ──
_similarity_index: EmbryoSimilarityIndex | None = None


def get_similarity_index(artifacts_dir: Path = ARTIFACTS_DIR) -> EmbryoSimilarityIndex:
    """Get or lazy-load the singleton similarity index."""
    global _similarity_index
    if _similarity_index is None:
        _similarity_index = EmbryoSimilarityIndex(artifacts_dir=artifacts_dir)
    return _similarity_index


def find_similar_cases(image_bytes: bytes, k: int = 5) -> list[dict]:
    """Find the k most visually similar known embryo cases for an uploaded image.

    Returns a list of dicts (best match first), each with:
        rank        : int, 1-based
        filename    : str, the matched training image filename
        similarity  : float in [-1, 1], cosine similarity (higher = more similar)
        metadata    : dict of whatever ET-record fields could be linked
                      (donor, donor_breed, et_date, embryo_stage, technician_name,
                      pregnancy_outcome, ...) — may be sparse/empty when linkage
                      wasn't available for that image.
    """
    index = get_similarity_index()
    return index.find_similar(image_bytes, k=k)
