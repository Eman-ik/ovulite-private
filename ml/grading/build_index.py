"""Build a nearest-neighbor embedding index from the SimCLR-pretrained backbone.

This is the honest replacement for the abandoned grade-classifier: instead of
predicting a fabricated Grade 1/2/3 label, we embed every known embryo image
with the self-supervised SimCLR backbone and store the resulting feature
vectors alongside whatever ET-record metadata we can link to them. At
inference time (see similarity.py) a new image is embedded the same way and
compared against this index via cosine similarity to surface the closest
known cases.

Usage:
    python -m ml.grading.build_index
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Ensure project root is on path when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def _load_backbone(backbone_path: Path, device: "torch.device"):
    """Load the SimCLR-pretrained EfficientNet-B0 backbone (no projection head)."""
    from torchvision.models import efficientnet_b0

    backbone = efficientnet_b0(weights=None)
    backbone.classifier = torch.nn.Identity()

    state = torch.load(backbone_path, map_location=device, weights_only=True)
    backbone.load_state_dict(state)
    backbone.to(device)
    backbone.eval()
    return backbone


def _link_metadata(image_dir: Path, csv_path: Path | None) -> dict:
    """Build a sequence_number -> metadata dict using the ET record linkage.

    Reuses ml.grading.linkage.build_image_record_mapping for the core join
    (image <-> ET row by sequential position), then folds in a couple of
    extra descriptive columns (Donor, ET Date) that linkage.py doesn't
    already carry, purely for display purposes in the similarity UI.

    Deliberately does NOT use linkage.build_grade_labels() — that constructs
    the near-constant-label pseudo-labels this feature is explicitly avoiding.
    """
    import pandas as pd

    from ml.grading.linkage import build_image_record_mapping

    if csv_path is None:
        # Mirror train_grading()'s default CSV resolution so the image-index
        # positional mapping (blq{N}.jpg -> row N) stays consistent with
        # whatever CSV the rest of the grading pipeline treats as canonical.
        csv_candidates = sorted(Path(PROJECT_ROOT / "docs" / "dataset").glob("*ET Data*"))
        if not csv_candidates:
            logger.warning("No ET Data CSV found in docs/dataset/; building index without metadata")
            return {}
        csv_path = csv_candidates[0]

    try:
        mapping = build_image_record_mapping(image_dir, str(csv_path))
    except Exception as e:
        logger.warning("Could not build image/record mapping: %s", e)
        return {}

    # Pull a couple of extra display-only columns directly from the same CSV.
    extra_cols = {}
    try:
        et_df = pd.read_csv(str(csv_path), dtype=str)
        et_df = et_df.dropna(how="all").reset_index(drop=True)
        et_df["sequence_number"] = et_df.index + 1

        def _clean(val):
            if pd.isna(val) or str(val).strip() in (".", "", "nan"):
                return None
            return str(val).strip()

        for _, row in et_df.iterrows():
            extra_cols[row["sequence_number"]] = {
                "donor": _clean(row.get("Donor")),
                "et_date": _clean(row.get("ET Date")),
            }
    except Exception as e:
        logger.warning("Could not load extra display metadata from CSV: %s", e)

    result = {}
    for _, row in mapping.iterrows():
        seq = row["sequence_number"]
        extra = extra_cols.get(seq, {})
        result[row["filename"]] = {
            "sequence_number": int(seq),
            "et_number": row.get("et_number"),
            "donor": extra.get("donor"),
            "donor_breed": row.get("donor_breed"),
            "et_date": extra.get("et_date"),
            "embryo_stage": row.get("embryo_stage"),
            "embryo_grade": row.get("embryo_grade"),
            "fresh_or_frozen": row.get("fresh_or_frozen"),
            "technician_name": row.get("technician_name"),
            "pregnancy_outcome": row.get("pc1_result"),
        }
    return result


def build_embedding_index(
    image_dir: Path | None = None,
    backbone_path: Path | None = None,
    csv_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Embed every image in image_dir with the SimCLR backbone and save an index.

    The index is a dict with:
        filenames   : list[str]
        embeddings  : np.ndarray of shape (N, feature_dim), L2-normalized
        metadata    : list[dict]  (per-image ET record metadata, may be sparse)
        meta        : dict        (build-time provenance info)

    Returns the path the index was saved to.
    """
    if not HAS_TORCH:
        raise ImportError("PyTorch is required to build the embedding index")

    from ml.grading.config import ARTIFACTS_DIR, IMAGE_DIR
    from ml.grading.preprocessing import get_eval_transforms
    from ml.grading.linkage import discover_images
    from PIL import Image

    image_dir = image_dir or IMAGE_DIR
    backbone_path = backbone_path or (ARTIFACTS_DIR / "simclr_backbone.pt")
    output_path = output_path or (ARTIFACTS_DIR / "embedding_index.joblib")

    if not backbone_path.exists():
        raise FileNotFoundError(
            f"No SimCLR backbone found at {backbone_path}. Run train_simclr() first "
            "(python -m ml.grading.run_training --simclr)."
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Building embedding index on %s", device)

    backbone = _load_backbone(backbone_path, device)
    transform = get_eval_transforms()

    images = discover_images(image_dir)
    if not images:
        raise FileNotFoundError(f"No blq*.jpg images found under {image_dir}")

    metadata_by_filename = _link_metadata(image_dir, csv_path)

    filenames = []
    embeddings = []
    metadata_list = []

    with torch.no_grad():
        for rec in images:
            path = Path(rec["path"])
            filename = rec["filename"]
            try:
                img = Image.open(path).convert("RGB")
            except Exception as e:
                logger.warning("Skipping unreadable image %s: %s", filename, e)
                continue

            tensor = transform(img).unsqueeze(0).to(device)
            feat = backbone(tensor)  # (1, feature_dim) backbone feature, NOT projection head
            feat = feat.squeeze(0).cpu().numpy().astype(np.float32)

            filenames.append(filename)
            embeddings.append(feat)
            metadata_list.append(
                metadata_by_filename.get(
                    filename,
                    {"sequence_number": rec["sequence_number"]},
                )
            )

    embeddings = np.stack(embeddings, axis=0)

    # L2-normalize so cosine similarity reduces to a dot product at query time.
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings_normalized = embeddings / norms

    index = {
        "filenames": filenames,
        "embeddings": embeddings_normalized,
        "metadata": metadata_list,
        "meta": {
            "type": "simclr_embedding_index",
            "n_images": len(filenames),
            "feature_dim": int(embeddings.shape[1]),
            "backbone_path": str(backbone_path),
            "image_dir": str(image_dir),
            "device": str(device),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

    import joblib

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(index, output_path)
    logger.info("Saved embedding index (%d images) to %s", len(filenames), output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Build the SimCLR embedding similarity index")
    parser.add_argument("--image-dir", type=str, default=None)
    parser.add_argument("--backbone", type=str, default=None)
    parser.add_argument("--csv", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    build_embedding_index(
        image_dir=Path(args.image_dir) if args.image_dir else None,
        backbone_path=Path(args.backbone) if args.backbone else None,
        csv_path=Path(args.csv) if args.csv else None,
        output_path=Path(args.output) if args.output else None,
    )


if __name__ == "__main__":
    main()
