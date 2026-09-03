"""Embryo image preprocessing pipeline (ROADMAP task 3.1).

Handles:
- Loading JPEG images from the Blastocyst images directory
- Resize to 224×224
- Normalization to ImageNet stats
- Data augmentation (rotation, flip, contrast jitter, color jitter)
- Returns PyTorch tensors ready for model input
"""

from pathlib import Path

import numpy as np

try:
    import torch
    from torch.utils.data import Dataset
    from torchvision import transforms

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .config import (
    IMAGE_DIR,
    IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
)


def get_train_transforms():
    """Augmented transforms for training."""
    if not HAS_TORCH:
        raise ImportError("PyTorch and torchvision required for image preprocessing")
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomRotation(degrees=30),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def get_eval_transforms():
    """Non-augmented transforms for evaluation/inference."""
    if not HAS_TORCH:
        raise ImportError("PyTorch and torchvision required for image preprocessing")
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def get_simclr_transforms():
    """Two-view augmentation for SimCLR contrastive pretraining (task 3.3)."""
    if not HAS_TORCH:
        raise ImportError("PyTorch and torchvision required")
    base = transforms.Compose([
        transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.2, 1.0)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomApply([
            transforms.ColorJitter(0.4, 0.4, 0.4, 0.1)
        ], p=0.8),
        transforms.RandomGrayscale(p=0.2),
        transforms.GaussianBlur(kernel_size=23, sigma=(0.1, 2.0)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])
    return SimCLRPairTransform(base)


class SimCLRPairTransform:
    """Apply the same base transform twice to produce two views."""

    def __init__(self, base_transform):
        self.base = base_transform

    def __call__(self, img):
        return self.base(img), self.base(img)


class EmbryoImageDataset(Dataset):
    """PyTorch Dataset for embryo images.

    Supports:
    - Plain image loading (for SimCLR / inference)
    - Image + metadata + label loading (for supervised grading)

    When transform returns a tuple (SimCLR pair), __getitem__ returns the tuple
    directly so a DataLoader yields (view1_batch, view2_batch).
    """

    def __init__(
        self,
        image_paths: list[Path] | None = None,
        labels: list[int] | None = None,
        metadata: list[dict] | None = None,
        transform=None,
        image_dir: Path | None = None,
        mode: str = "plain",
    ):
        if image_paths is not None:
            self.image_paths = [Path(p) for p in image_paths]
        else:
            # Auto-discover all images
            img_dir = image_dir or IMAGE_DIR
            self.image_paths = sorted(img_dir.glob("*.jpg"))

        self.labels = labels
        self.metadata = metadata
        self.transform = transform or get_eval_transforms()
        self.mode = mode

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        from PIL import Image

        img_path = self.image_paths[idx]
        img = Image.open(img_path).convert("RGB")

        transformed = self.transform(img)

        # SimCLR mode: transform returns (view1, view2) tuple
        if isinstance(transformed, tuple):
            return transformed

        return transformed


def load_image_for_inference(image_path: str | Path) -> "torch.Tensor":
    """Load and preprocess a single image for model inference.

    Returns a batch tensor of shape (1, 3, 224, 224).
    """
    from PIL import Image

    if not HAS_TORCH:
        raise ImportError("PyTorch required")

    img = Image.open(image_path).convert("RGB")
    transform = get_eval_transforms()
    tensor = transform(img)
    return tensor.unsqueeze(0)  # Add batch dimension


def load_image_from_bytes(image_bytes: bytes) -> "torch.Tensor":
    """Load image from raw bytes (for API upload) and preprocess.

    Returns a batch tensor of shape (1, 3, 224, 224).
    """
    import io
    from PIL import Image

    if not HAS_TORCH:
        raise ImportError("PyTorch required")

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    transform = get_eval_transforms()
    tensor = transform(img)
    return tensor.unsqueeze(0)


class LabeledImageDataset(Dataset):
    """Plain (image, label) dataset — no metadata fusion.

    Used for training/evaluating EmbryoGradeClassifier on the verified
    real grade labels (ml/grading/real_labels.py), where no per-image
    ET metadata is reliably available.
    """

    def __init__(self, image_paths: list, labels: list[int], transform=None):
        self.image_paths = [Path(p) for p in image_paths]
        self.labels = labels
        self.transform = transform or get_eval_transforms()

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        from PIL import Image as PILImage

        img = PILImage.open(self.image_paths[idx]).convert("RGB")
        img_tensor = self.transform(img)
        label = torch.tensor(self.labels[idx], dtype=torch.long)
        return img_tensor, label


class GradingDataset(Dataset):
    """Dataset for supervised grading that returns image + metadata + labels.

    Used by train.py for the supervised fine-tuning stage.
    """

    # Categorical vocab built from training data
    _breed_vocab: dict[str, int] = {}
    _tech_vocab: dict[str, int] = {}
    _ff_vocab: dict[str, int] = {"Fresh": 1, "Frozen": 2}

    def __init__(
        self,
        image_paths: list,
        labels: list[int],
        metadata: list[dict],
        transform=None,
    ):
        self.image_paths = [Path(p) for p in image_paths]
        self.labels = labels
        self.metadata = metadata
        self.transform = transform or get_eval_transforms()

        # Build categorical vocabs from this dataset
        for m in metadata:
            breed = m.get("donor_breed", "Unknown")
            if breed not in GradingDataset._breed_vocab:
                GradingDataset._breed_vocab[breed] = len(GradingDataset._breed_vocab) + 1
            tech = m.get("technician_name", "Unknown")
            if tech not in GradingDataset._tech_vocab:
                GradingDataset._tech_vocab[tech] = len(GradingDataset._tech_vocab) + 1
            ff = m.get("fresh_or_frozen", "Fresh")
            if ff not in GradingDataset._ff_vocab:
                GradingDataset._ff_vocab[ff] = len(GradingDataset._ff_vocab) + 1

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        from PIL import Image as PILImage

        img = PILImage.open(self.image_paths[idx]).convert("RGB")
        img_tensor = self.transform(img)

        m = self.metadata[idx]
        numeric = torch.tensor([
            float(m.get("embryo_stage", 6.0)),
            float(m.get("embryo_grade", 1.0)),
        ], dtype=torch.float32)

        categorical = {
            "donor_breed": torch.tensor(
                GradingDataset._breed_vocab.get(m.get("donor_breed", "Unknown"), 0),
                dtype=torch.long,
            ),
            "fresh_or_frozen": torch.tensor(
                GradingDataset._ff_vocab.get(m.get("fresh_or_frozen", "Fresh"), 0),
                dtype=torch.long,
            ),
            "technician_name": torch.tensor(
                GradingDataset._tech_vocab.get(m.get("technician_name", "Unknown"), 0),
                dtype=torch.long,
            ),
        }

        label = self.labels[idx]
        viability = 1.0 if label == 2 else 0.0  # High viability = pregnant

        return {
            "image": img_tensor,
            "grade_label": torch.tensor(label, dtype=torch.long),
            "viability_label": torch.tensor(viability, dtype=torch.float32),
            "numeric_meta": numeric,
            "categorical_meta": categorical,
        }
