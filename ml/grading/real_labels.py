"""Real, verified grade labels for the 482 embryo images.

Source: Rocha et al. 2017, "Automatized image processing of bovine blastocysts
produced in vitro for quantitative variable determination", Scientific Data
(Nature), DOI 10.1038/sdata.2017.192. Dataset DOI 10.6084/m9.figshare.c.3825241
(CC0). See docs/dataset/external/rocha2017_bovine_blastocyst/DATASET_CARD.md.

Ovulite's docs/Blastocystimages/ images were verified byte-for-byte identical
(MD5) to this published dataset. Unlike ml/grading/linkage.py's
build_grade_labels() — which fabricates pseudo-labels from an unrelated
sequential row-index guess against the local ET CSV — these are the actual
expert/algorithm-assigned IETS-style grades (1=excellent/good, 2=fair,
3=poor) for each specific image, from the paper's `Modal value` column
(the consensus of its three independent classification methods).

There is no verified per-image link between these images and any specific
Ovulite ET record, so no ET metadata (stage, donor, technician, etc.) is
attached here — this module supplies image path + grade label only.
"""

from pathlib import Path

import pandas as pd

from .config import IMAGE_DIR, PROJECT_ROOT

LABELS_CSV = (
    PROJECT_ROOT
    / "docs"
    / "dataset"
    / "external"
    / "rocha2017_bovine_blastocyst"
    / "labels_clean.csv"
)

# Paper's 3-class IETS-style grading: 1=excellent/good, 2=fair, 3=poor.
# Model classes are 0-indexed for CrossEntropyLoss.
GRADE_TO_CLASS = {1: 0, 2: 1, 3: 2}
CLASS_TO_GRADE = {v: k for k, v in GRADE_TO_CLASS.items()}
CLASS_NAMES = ["Grade 1 (excellent/good)", "Grade 2 (fair)", "Grade 3 (poor)"]


def load_labeled_images(
    labels_csv: Path = LABELS_CSV,
    image_dir: Path = IMAGE_DIR,
) -> pd.DataFrame:
    """Load the verified image-path + grade-label table.

    Returns a DataFrame with columns: figure_name, image_path, grade (1-3),
    grade_class (0-2, model target).
    """
    if not labels_csv.exists():
        raise FileNotFoundError(
            f"Real grade labels not found at {labels_csv}. "
            "See docs/dataset/external/rocha2017_bovine_blastocyst/DATASET_CARD.md."
        )

    df = pd.read_csv(labels_csv)
    df = df[["figure_name", "Modal value"]].dropna()
    df["grade"] = df["Modal value"].astype(float).astype(int)
    df = df[df["grade"].isin(GRADE_TO_CLASS)].copy()
    df["grade_class"] = df["grade"].map(GRADE_TO_CLASS)
    df["image_path"] = df["figure_name"].apply(lambda name: str(image_dir / f"{name}.jpg"))

    missing = df[~df["image_path"].apply(lambda p: Path(p).exists())]
    if len(missing):
        raise FileNotFoundError(
            f"{len(missing)} labeled images missing from {image_dir}: "
            f"{missing['figure_name'].tolist()[:5]}..."
        )

    return df[["figure_name", "image_path", "grade", "grade_class"]].reset_index(drop=True)


def stratified_split(
    df: pd.DataFrame,
    seed: int = 42,
    train_frac: float = 0.7,
    val_frac: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified train/val/test split by grade_class, image-level (no leakage
    concern since each row is an independent image with no repeated-subject
    grouping information available for this external dataset)."""
    import numpy as np

    rng = np.random.RandomState(seed)
    train_parts, val_parts, test_parts = [], [], []

    for _, group in df.groupby("grade_class"):
        idx = group.index.to_numpy().copy()
        rng.shuffle(idx)
        n = len(idx)
        n_train = int(round(n * train_frac))
        n_val = int(round(n * val_frac))
        train_parts.append(df.loc[idx[:n_train]])
        val_parts.append(df.loc[idx[n_train : n_train + n_val]])
        test_parts.append(df.loc[idx[n_train + n_val :]])

    def _concat(parts):
        return pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)

    return _concat(train_parts), _concat(val_parts), _concat(test_parts)
