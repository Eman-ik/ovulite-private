"""Train the real-label embryo grade classifier.

Uses the verified Rocha et al. 2017 grade labels (ml/grading/real_labels.py)
instead of the fabricated pseudo-labels in ml/grading/linkage.py. Produces a
versioned artifact directory under ml/artifacts/grading/real_labels_v1/ with
a model card, confusion matrix, and a SHA-256 manifest (same integrity-check
convention as ml/predict.py's pregnancy model artifacts).

Usage:
    python -m ml.grading.train_real_grading
"""

import collections
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .config import (
    ARTIFACTS_DIR,
    REAL_GRADING_BATCH_SIZE,
    REAL_GRADING_EPOCHS,
    REAL_GRADING_LR,
    REAL_GRADING_PATIENCE,
    SEED,
)


def _set_seed(seed: int = SEED):
    import random

    random.seed(seed)
    np.random.seed(seed)
    if HAS_TORCH:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def train_real_grading(
    epochs: int = REAL_GRADING_EPOCHS,
    batch_size: int = REAL_GRADING_BATCH_SIZE,
    lr: float = REAL_GRADING_LR,
    patience: int = REAL_GRADING_PATIENCE,
    save_dir: Path | None = None,
    use_simclr_init: bool = True,
) -> Path:
    if not HAS_TORCH:
        raise ImportError("PyTorch is required for grading training")

    from .models import EmbryoGradeClassifier
    from .preprocessing import LabeledImageDataset, get_eval_transforms, get_train_transforms
    from .real_labels import CLASS_NAMES, load_labeled_images, stratified_split

    logging.basicConfig(level=logging.INFO)
    _set_seed()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Real-label grading training on %s", device)

    if save_dir is None:
        from .config import REAL_GRADING_ARTIFACTS_DIR

        save_dir = REAL_GRADING_ARTIFACTS_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    # ── Data ──
    df = load_labeled_images()
    logger.info("Loaded %d verified-label images", len(df))
    train_df, val_df, test_df = stratified_split(df, seed=SEED)
    logger.info(
        "Split: train=%d val=%d test=%d", len(train_df), len(val_df), len(test_df)
    )

    train_ds = LabeledImageDataset(
        train_df["image_path"].tolist(), train_df["grade_class"].tolist(), get_train_transforms()
    )
    val_ds = LabeledImageDataset(
        val_df["image_path"].tolist(), val_df["grade_class"].tolist(), get_eval_transforms()
    )
    test_ds = LabeledImageDataset(
        test_df["image_path"].tolist(), test_df["grade_class"].tolist(), get_eval_transforms()
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # ── Model ──
    model = EmbryoGradeClassifier(n_grades=3, freeze_backbone=True).to(device)

    simclr_backbone_path = ARTIFACTS_DIR / "simclr_backbone.pt"
    used_simclr_init = False
    if use_simclr_init and simclr_backbone_path.exists():
        logger.info("Initializing backbone from SimCLR self-supervised pretraining")
        state = torch.load(simclr_backbone_path, map_location=device, weights_only=True)
        model.backbone.load_state_dict(state, strict=False)
        used_simclr_init = True
    else:
        logger.info("No SimCLR backbone found, using ImageNet weights only")

    # ── Class-weighted loss (label distribution is imbalanced) ──
    class_counts = collections.Counter(train_df["grade_class"].tolist())
    n_classes = 3
    weights = torch.tensor(
        [len(train_df) / (n_classes * class_counts.get(c, 1)) for c in range(n_classes)],
        dtype=torch.float32,
    ).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)

    backbone_params = [p for n, p in model.named_parameters() if "backbone" in n and p.requires_grad]
    head_params = [p for n, p in model.named_parameters() if "backbone" not in n]
    optimizer = optim.AdamW(
        [
            {"params": backbone_params, "lr": lr * 0.1},
            {"params": head_params, "lr": lr},
        ],
        weight_decay=1e-4,
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    # ── Train loop ──
    best_val_loss = float("inf")
    best_epoch = 0
    history = []
    patience_counter = 0

    model_path = save_dir / "grade_classifier.pt"

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            loss = criterion(logits, labels)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            train_correct += (logits.argmax(1) == labels).sum().item()
            train_total += images.size(0)

        avg_train_loss = train_loss / max(train_total, 1)
        train_acc = train_correct / max(train_total, 1)

        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                logits = model(images)
                loss = criterion(logits, labels)
                val_loss += loss.item() * images.size(0)
                val_correct += (logits.argmax(1) == labels).sum().item()
                val_total += images.size(0)

        avg_val_loss = val_loss / max(val_total, 1)
        val_acc = val_correct / max(val_total, 1)
        scheduler.step(avg_val_loss)

        history.append(
            {
                "epoch": epoch,
                "train_loss": avg_train_loss,
                "train_acc": train_acc,
                "val_loss": avg_val_loss,
                "val_acc": val_acc,
            }
        )

        if epoch % 5 == 0 or epoch == 1:
            logger.info(
                "Epoch %d/%d | Train Loss %.4f Acc %.3f | Val Loss %.4f Acc %.3f",
                epoch, epochs, avg_train_loss, train_acc, avg_val_loss, val_acc,
            )

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            patience_counter = 0
            torch.save(model.state_dict(), model_path)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info("Early stopping at epoch %d (best: %d)", epoch, best_epoch)
                break

    # ── Final test-set evaluation (best checkpoint) ──
    from sklearn.metrics import classification_report, confusion_matrix, f1_score

    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()

    all_preds, all_labels = [], []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            logits = model(images)
            preds = logits.argmax(1).cpu().numpy()
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.numpy().tolist())

    test_acc = float(np.mean(np.array(all_preds) == np.array(all_labels)))
    test_macro_f1 = float(f1_score(all_labels, all_preds, average="macro"))
    cm = confusion_matrix(all_labels, all_preds, labels=[0, 1, 2]).tolist()
    report = classification_report(
        all_labels, all_preds, labels=[0, 1, 2], target_names=CLASS_NAMES, output_dict=True, zero_division=0
    )

    logger.info("=" * 60)
    logger.info("TEST SET: accuracy=%.3f macro_f1=%.3f (n=%d)", test_acc, test_macro_f1, len(all_labels))
    logger.info("Confusion matrix (rows=true, cols=pred): %s", cm)
    logger.info("=" * 60)

    # ── Save model card / metadata ──
    metadata = {
        "type": "embryo_grade_classifier",
        "model_class": "EmbryoGradeClassifier",
        "backbone": "efficientnet_b0",
        "simclr_pretrained_init": used_simclr_init,
        "n_grades": 3,
        "class_names": CLASS_NAMES,
        "label_source": {
            "citation": (
                "Rocha J.C. et al. (2017), 'Automatized image processing of bovine "
                "blastocysts produced in vitro for quantitative variable determination', "
                "Scientific Data 4:170192, doi:10.1038/sdata.2017.192"
            ),
            "dataset_doi": "10.6084/m9.figshare.c.3825241",
            "license": "CC0 (data), CC-BY 4.0 (article)",
            "verification": "MD5-checksum verified byte-identical to docs/Blastocystimages/",
        },
        "caveats": [
            "No metadata fusion — no verified per-image ET record linkage (donor, "
            "technician, stage, etc.) exists for this external image set.",
            "No viability head — pregnancy-outcome linkage for these specific images "
            "is not established; only IETS-style grade is predicted.",
            "482 total images is a small dataset — treat metrics as indicative, not "
            "as a substitute for prospective validation on Ovulite's own future "
            "embryo images.",
        ],
        "split": {"train": len(train_df), "val": len(val_df), "test": len(test_df)},
        "label_distribution_train": {
            CLASS_NAMES[c]: class_counts.get(c, 0) for c in range(3)
        },
        "training": {
            "epochs_run": len(history),
            "epochs_max": epochs,
            "best_epoch": best_epoch,
            "batch_size": batch_size,
            "lr": lr,
            "seed": SEED,
            "device": str(device),
        },
        "test_metrics": {
            "accuracy": test_acc,
            "macro_f1": test_macro_f1,
            "confusion_matrix": cm,
            "confusion_matrix_labels": CLASS_NAMES,
            "classification_report": report,
        },
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(save_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    with open(save_dir / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    # ── Integrity manifest (same convention as ml/predict.py) ──
    manifest = {
        "files": {
            "grade_classifier.pt": _sha256(model_path),
            "metadata.json": _sha256(save_dir / "metadata.json"),
        }
    }
    with open(save_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Artifact saved to %s", save_dir)
    return save_dir


if __name__ == "__main__":
    train_real_grading()
