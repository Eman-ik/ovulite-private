"""CNN backbone + metadata fusion + grading head (ROADMAP tasks 3.3-3.8).

Architecture (from REQUIREMENTS §4.2):
- EfficientNet-B0 backbone (pretrained, frozen early layers)
- Metadata branch: numeric + categorical → embedding
- Fusion: CNN embedding ⊕ metadata embedding → MLP → output
- Output heads: Grade (3-class) + Viability probability
- Grad-CAM for visual explanations

SimCLR self-supervised pretraining module for the 482 unlabeled images.
"""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ═══════════════════════════════════════════════════════════
# SimCLR Pretraining (Task 3.3)
# ═══════════════════════════════════════════════════════════

class SimCLRProjectionHead(nn.Module):
    """Projection head for SimCLR contrastive learning."""

    def __init__(self, input_dim: int = 1280, hidden_dim: int = 512, output_dim: int = 128):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = F.relu(self.bn1(self.fc1(x)))
        x = self.fc2(x)
        return F.normalize(x, dim=1)


class SimCLRModel(nn.Module):
    """SimCLR model wrapping EfficientNet-B0 backbone + projection head."""

    def __init__(self, projection_dim: int = 128):
        super().__init__()
        if not HAS_TORCH:
            raise ImportError("PyTorch required")

        from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

        # Load pretrained EfficientNet-B0
        self.backbone = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
        feature_dim = self.backbone.classifier[1].in_features

        # Remove classifier head
        self.backbone.classifier = nn.Identity()

        # SimCLR projection head
        self.projection = SimCLRProjectionHead(
            input_dim=feature_dim,
            output_dim=projection_dim,
        )

    def forward(self, x):
        features = self.backbone(x)
        projections = self.projection(features)
        return features, projections


def nt_xent_loss(z1, z2, temperature: float = 0.5):
    """Normalized temperature-scaled cross-entropy loss for SimCLR."""
    batch_size = z1.shape[0]
    z = torch.cat([z1, z2], dim=0)  # (2B, D)
    sim = torch.mm(z, z.t()) / temperature  # (2B, 2B)

    # Mask out self-similarities
    mask = torch.eye(2 * batch_size, device=z.device).bool()
    sim = sim.masked_fill(mask, -1e9)

    # Positive pairs: (i, i+B) and (i+B, i)
    labels = torch.cat([
        torch.arange(batch_size, 2 * batch_size),
        torch.arange(batch_size),
    ]).to(z.device)

    return F.cross_entropy(sim, labels)


# ═══════════════════════════════════════════════════════════
# Metadata Branch (Task 3.5)
# ═══════════════════════════════════════════════════════════

class MetadataBranch(nn.Module):
    """Encodes embryo metadata into a fixed-size embedding.

    Handles: embryo_stage (numeric), embryo_grade (numeric),
    donor_breed (categorical), fresh_or_frozen (categorical),
    technician_name (categorical)
    """

    def __init__(
        self,
        n_numeric: int = 2,
        categorical_cardinalities: dict[str, int] | None = None,
        embedding_dim: int = 8,
        output_dim: int = 32,
    ):
        super().__init__()
        self.n_numeric = n_numeric

        # Categorical embeddings
        if categorical_cardinalities is None:
            categorical_cardinalities = {
                "donor_breed": 20,
                "fresh_or_frozen": 3,
                "technician_name": 10,
            }

        self.embeddings = nn.ModuleDict()
        total_cat_dim = 0
        for name, cardinality in categorical_cardinalities.items():
            emb_size = min(embedding_dim, (cardinality + 1) // 2)
            self.embeddings[name] = nn.Embedding(cardinality + 1, emb_size)  # +1 for unknown
            total_cat_dim += emb_size

        total_input = n_numeric + total_cat_dim
        self.mlp = nn.Sequential(
            nn.Linear(total_input, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, output_dim),
            nn.ReLU(),
        )

    def forward(self, numeric_features, categorical_features: dict[str, torch.Tensor]):
        parts = [numeric_features]
        for name, emb_layer in self.embeddings.items():
            if name in categorical_features:
                parts.append(emb_layer(categorical_features[name]))

        x = torch.cat(parts, dim=1)
        return self.mlp(x)


# ═══════════════════════════════════════════════════════════
# Fusion Model (Tasks 3.4, 3.6, 3.8)
# ═══════════════════════════════════════════════════════════

class EmbryoGradingModel(nn.Module):
    """Fusion model: CNN backbone + metadata branch → MLP → grade + viability.

    Architecture REQUIREMENTS §4.2:
    - EfficientNet-B0 backbone (pretrained, frozen early layers)
    - Metadata branch embedding
    - Concatenation fusion
    - Grade head: 3-class classification (Grade 1/2/3)
    - Viability head: sigmoid probability
    """

    def __init__(
        self,
        backbone_feature_dim: int = 1280,
        metadata_output_dim: int = 32,
        n_grades: int = 3,
        categorical_cardinalities: dict[str, int] | None = None,
        freeze_backbone: bool = True,
    ):
        super().__init__()
        if not HAS_TORCH:
            raise ImportError("PyTorch required")

        from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

        # ── CNN Backbone (Task 3.4) ──
        self.backbone = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
        actual_dim = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Identity()

        if freeze_backbone:
            # Freeze everything except the last block (features[-1]) and classifier
            for name, param in self.backbone.named_parameters():
                if "features.8" not in name and "features.7" not in name:
                    param.requires_grad = False

        # ── Metadata Branch (Task 3.5) ──
        self.metadata_branch = MetadataBranch(
            n_numeric=2,
            categorical_cardinalities=categorical_cardinalities,
            output_dim=metadata_output_dim,
        )

        # ── Fusion MLP (Task 3.6) ──
        fusion_dim = actual_dim + metadata_output_dim
        self.fusion = nn.Sequential(
            nn.Linear(fusion_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
        )

        # ── Grade Head (Task 3.8) ── 3-class classification
        self.grade_head = nn.Linear(128, n_grades)

        # ── Viability Head (Task 3.8) ── binary probability
        self.viability_head = nn.Sequential(
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

        # Store backbone feature dim for Grad-CAM
        self._backbone_features = None
        self._gradient_hook = None

    def forward(self, image, numeric_meta, categorical_meta: dict):
        # CNN features
        cnn_features = self.backbone(image)

        # Metadata embedding
        meta_embedding = self.metadata_branch(numeric_meta, categorical_meta)

        # Fusion
        fused = torch.cat([cnn_features, meta_embedding], dim=1)
        fused = self.fusion(fused)

        # Output heads
        grade_logits = self.grade_head(fused)
        viability = self.viability_head(fused).squeeze(-1)

        return grade_logits, viability

    def forward_with_cam(self, image, numeric_meta, categorical_meta: dict):
        """Forward pass that also returns the last conv feature map for Grad-CAM."""
        # Hook to capture backbone features before pooling
        features = {}

        def hook_fn(module, input, output):
            features["last_conv"] = output

        # Register hook on the last conv block
        handle = self.backbone.features[-1].register_forward_hook(hook_fn)

        grade_logits, viability = self.forward(image, numeric_meta, categorical_meta)

        handle.remove()

        return grade_logits, viability, features.get("last_conv")


# ═══════════════════════════════════════════════════════════
# Image-only grade classifier (real-label training, no metadata fusion)
# ═══════════════════════════════════════════════════════════

class EmbryoGradeClassifier(nn.Module):
    """CNN-only 3-class grade classifier for the verified real labels.

    No metadata branch and no viability head: there is no reliable
    per-image ET metadata or pregnancy-outcome linkage for the Rocha
    et al. 2017 image set (see ml/grading/real_labels.py), so this
    model is intentionally simpler than EmbryoGradingModel — it only
    predicts what the training labels actually support: image → grade.
    """

    def __init__(self, n_grades: int = 3, freeze_backbone: bool = True):
        super().__init__()
        if not HAS_TORCH:
            raise ImportError("PyTorch required")

        from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

        self.backbone = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
        feature_dim = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Identity()

        if freeze_backbone:
            # Freeze everything except the last two feature blocks, same
            # policy as EmbryoGradingModel / ROADMAP task 3.4.
            for name, param in self.backbone.named_parameters():
                if "features.8" not in name and "features.7" not in name:
                    param.requires_grad = False

        self.classifier_head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, n_grades),
        )

    def forward(self, image):
        features = self.backbone(image)
        return self.classifier_head(features)


class GradCAMClassifier:
    """Grad-CAM for EmbryoGradeClassifier (image-only forward signature)."""

    def __init__(self, model: EmbryoGradeClassifier):
        if not HAS_TORCH:
            raise ImportError("PyTorch required")
        self.model = model
        self.gradients = None
        self.activations = None

    def _register_hooks(self, target_layer):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        fh = target_layer.register_forward_hook(forward_hook)
        bh = target_layer.register_full_backward_hook(backward_hook)
        return fh, bh

    def generate(self, image: "torch.Tensor", target_class: int | None = None) -> np.ndarray:
        """Generate a Grad-CAM heatmap for a single (1, 3, 224, 224) image tensor."""
        self.model.eval()
        target_layer = self.model.backbone.features[-1]
        fh, bh = self._register_hooks(target_layer)

        try:
            image.requires_grad_(True)
            grade_logits = self.model(image)

            if target_class is None:
                target_class = grade_logits.argmax(dim=1).item()

            self.model.zero_grad()
            score = grade_logits[0, target_class]
            score.backward(retain_graph=True)

            weights = self.gradients.mean(dim=(2, 3), keepdim=True)
            cam = (weights * self.activations).sum(dim=1, keepdim=True)
            cam = F.relu(cam)

            cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
            cam = cam.squeeze().detach().cpu().numpy()

            cam_min, cam_max = cam.min(), cam.max()
            if cam_max - cam_min > 1e-8:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                cam = np.zeros_like(cam)

            return cam
        finally:
            fh.remove()
            bh.remove()


# ═══════════════════════════════════════════════════════════
# Grad-CAM (Task 3.7)
# ═══════════════════════════════════════════════════════════

class GradCAM:
    """Gradient-weighted Class Activation Mapping for visual explanations.

    Produces a heatmap showing which image regions influenced the grade prediction.
    """

    def __init__(self, model: EmbryoGradingModel):
        if not HAS_TORCH:
            raise ImportError("PyTorch required")
        self.model = model
        self.gradients = None
        self.activations = None

    def _register_hooks(self, target_layer):
        """Register forward and backward hooks on the target layer."""

        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        fh = target_layer.register_forward_hook(forward_hook)
        bh = target_layer.register_full_backward_hook(backward_hook)
        return fh, bh

    def generate(
        self,
        image: "torch.Tensor",
        numeric_meta: "torch.Tensor",
        categorical_meta: dict,
        target_class: int | None = None,
    ) -> np.ndarray:
        """Generate Grad-CAM heatmap for a single image.

        Parameters
        ----------
        image : (1, 3, 224, 224) tensor
        target_class : class index for grade head (None = predicted class)

        Returns
        -------
        heatmap : (224, 224) float array in [0, 1]
        """
        self.model.eval()
        target_layer = self.model.backbone.features[-1]
        fh, bh = self._register_hooks(target_layer)

        try:
            image.requires_grad_(True)
            grade_logits, viability = self.model(image, numeric_meta, categorical_meta)

            if target_class is None:
                target_class = grade_logits.argmax(dim=1).item()

            # Backward from target class score
            self.model.zero_grad()
            score = grade_logits[0, target_class]
            score.backward(retain_graph=True)

            # Compute Grad-CAM
            weights = self.gradients.mean(dim=(2, 3), keepdim=True)  # Global average pooling
            cam = (weights * self.activations).sum(dim=1, keepdim=True)
            cam = F.relu(cam)  # ReLU to keep only positive contributions

            # Resize to image size
            cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
            cam = cam.squeeze().cpu().numpy()

            # Normalize to [0, 1]
            cam_min, cam_max = cam.min(), cam.max()
            if cam_max - cam_min > 1e-8:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                cam = np.zeros_like(cam)

            return cam

        finally:
            fh.remove()
            bh.remove()


def generate_heatmap_overlay(
    original_image_bytes: bytes,
    heatmap: np.ndarray,
    alpha: float = 0.4,
) -> bytes:
    """Overlay Grad-CAM heatmap on the original image and return as JPEG bytes.

    Parameters
    ----------
    original_image_bytes : raw JPEG bytes
    heatmap : (224, 224) float array in [0, 1]
    alpha : overlay transparency

    Returns
    -------
    JPEG bytes of the overlaid image
    """
    import io

    import numpy as np
    from PIL import Image

    # Load original
    img = Image.open(io.BytesIO(original_image_bytes)).convert("RGB")
    img = img.resize((224, 224))
    img_array = np.array(img, dtype=np.float32)

    # Create colormap (blue→green→red)
    heatmap_uint8 = (heatmap * 255).astype(np.uint8)

    try:
        import cv2
        heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB).astype(np.float32)
    except ImportError:
        # Manual colormap fallback (red channel = heat intensity)
        heatmap_color = np.zeros((*heatmap.shape, 3), dtype=np.float32)
        heatmap_color[:, :, 0] = heatmap * 255  # Red
        heatmap_color[:, :, 1] = (1 - heatmap) * 100  # Faint green for cool areas

    # Blend
    blended = (1 - alpha) * img_array + alpha * heatmap_color
    blended = np.clip(blended, 0, 255).astype(np.uint8)

    # Encode to JPEG
    result = Image.fromarray(blended)
    buffer = io.BytesIO()
    result.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
