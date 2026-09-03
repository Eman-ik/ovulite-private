"""Embryo grading module configuration."""

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = Path(__file__).resolve().parent.parent
GRADING_DIR = Path(__file__).resolve().parent
GRADING_ARTIFACTS_DIR = ML_DIR / "artifacts" / "grading"
ARTIFACTS_DIR = GRADING_ARTIFACTS_DIR  # alias
IMAGE_DIR = PROJECT_ROOT / "docs" / "Blastocystimages" / "Blastocyst images"
UPLOAD_DIR = PROJECT_ROOT / "uploads" / "embryo_images"

# ── Image preprocessing ──────────────────────────────────
IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# ── Random seed ──────────────────────────────────────────
SEED = 42

# ── SimCLR config ────────────────────────────────────────
SIMCLR_EPOCHS = 100
SIMCLR_BATCH_SIZE = 32
SIMCLR_LR = 3e-4
SIMCLR_TEMPERATURE = 0.5
SIMCLR_PROJECTION_DIM = 128

# Aliases used by train.py
EPOCHS_SIMCLR = SIMCLR_EPOCHS
BATCH_SIZE_SIMCLR = SIMCLR_BATCH_SIZE
LR_SIMCLR = SIMCLR_LR

# ── Supervised grading config ────────────────────────────
GRADING_EPOCHS = 50
GRADING_BATCH_SIZE = 16
GRADING_LR = 1e-4
GRADING_WEIGHT_DECAY = 1e-4

# Aliases used by train.py
EPOCHS_GRADING = GRADING_EPOCHS
BATCH_SIZE_GRADING = GRADING_BATCH_SIZE
LR_GRADING = GRADING_LR
NUM_GRADES = 3  # Grade 1, 2, 3
METADATA_EMBEDDING_DIM = 32

# ── Backbone ─────────────────────────────────────────────
BACKBONE = "efficientnet_b0"  # EfficientNet-B0 as specified in REQUIREMENTS §4.2
BACKBONE_FEATURE_DIM = 1280  # EfficientNet-B0 output dimension
FREEZE_BACKBONE_LAYERS = True  # Freeze early layers, fine-tune final blocks

# ── Real-label grade classifier (verified Rocha et al. 2017 labels) ──
REAL_GRADING_ARTIFACTS_DIR = GRADING_ARTIFACTS_DIR / "real_labels_v1"
REAL_GRADING_EPOCHS = 60
REAL_GRADING_BATCH_SIZE = 16
REAL_GRADING_LR = 1e-4
REAL_GRADING_PATIENCE = 12

# ── Metadata features for fusion ─────────────────────────
METADATA_FEATURES = [
    "embryo_stage",   # Ordinal 4-8
    "embryo_grade",   # Ordinal 1-4 (manual grade)
    "donor_breed",    # Categorical
    "fresh_or_frozen",  # Binary
    "technician_name",  # Categorical
]

METADATA_NUMERIC = ["embryo_stage", "embryo_grade"]
METADATA_CATEGORICAL = ["donor_breed", "fresh_or_frozen", "technician_name"]
