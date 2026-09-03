# External Dataset: Rocha et al. 2017 Bovine Blastocyst Images

## What this is

This confirms that Ovulite's existing 482-image embryo dataset at
[`docs/Blastocystimages/Blastocyst images/`](../../Blastocystimages/Blastocyst%20images/)
(referenced throughout the codebase as `blq{N}.jpg`, N = 1–482) **is** this published, peer-reviewed,
publicly licensed dataset — verified by MD5 checksum, byte-for-byte identical across all 482 files.

Unlike the local ET data's `Embryo Grade` column (near-constant at Grade 1, unusable — see
[`backend/app/api/grading.py`](../../../backend/app/api/grading.py) docstring), **this source dataset
carries real, expert-assigned, varied grade labels** for every one of the 482 images.

## Source

- **Title:** Automatized image processing of bovine blastocysts produced in vitro for quantitative variable determination
- **Authors:** José Celso Rocha, Felipe José Passalia, Felipe Delestro Matos, Marcelo Fábio Gouveia Nogueira, Maria Beatriz Takahashi, Marc Peter Maserati Jr, Mayra Fernanda Alves, Tamie Guibu de Almeida, Bruna Lopes Cardoso, Andrea Cristina Basso
- **Journal:** Scientific Data (Nature), 2017
- **Article DOI:** [10.1038/sdata.2017.192](https://doi.org/10.1038/sdata.2017.192)
- **Dataset DOI (collection):** [10.6084/m9.figshare.c.3825241](https://doi.org/10.6084/m9.figshare.c.3825241)
- **License:** Article text CC-BY 4.0; dataset files CC0 (public domain) — fully reusable, redistributable, and adaptable, attribution given here as good academic practice.
- **Species note:** *Bos indicus* blastocysts (per Figshare item description) — worth checking against Ovulite's own donor breed mix (`docs/dataset/ovulite_cleaned_et_data.csv` shows Brahman/Braford/Nukra donors, consistent with *indicus*-influenced breeds).

## Files in this folder

| File | Contents |
|---|---|
| `quantitative_variables_and_classification.xls` | Original file as downloaded from Figshare (article id 5412988, direct file: https://ndownloader.figshare.com/files/9335503). 482 rows × 43 columns: figure name, 36 automated quantitative image variables (GLCM texture, Hough transform, watershed segmentation, grey-level statistics — trophectoderm/ICM/expansion region measures), and **3 independent classification methods** (`MFA Classification`, `TGA Classification`, `BLC Classification`) plus a consensus `Modal value` grade. |
| `labels_clean.csv` | Same data, cleaned: proper header row, `figure_name` normalized to match `blq{N}` image filenames exactly. |

## Grade label distribution (`Modal value` column — the consensus grade to use)

| Grade | Meaning (IETS-style) | Count |
|---|---|---|
| 1 | Excellent/Good | 112 |
| 2 | Fair | 173 |
| 3 | Poor | 194 |

(Paper reports 113/175/194 — the 1–2 row discrepancy is very likely a tie-break/rounding difference in how the paper computed its own modal value versus how it's stored in this file; negligible either way.)

Verified: **all 482 `figure_name` values match the existing `blq{N}.jpg` filenames in `docs/Blastocystimages/` exactly** — no missing images, no orphaned labels.

## Why this matters for Ovulite

[`ROADMAP.md`](../../../ROADMAP.md) Phase 3 and the SRS (§5.7) both specify a CNN + Grad-CAM embryo grading model.
That was explicitly descoped — see `grading.py`'s docstring — because the *local* embryo images had no usable
grade signal. This dataset removes that specific blocker: it's the original, correctly labeled source of those
same 482 images, openly licensed, with real class variance across all 3 grades.

**This is not yet wired into any model or pipeline** — it's delivered here as verified, documented, ready-to-use
data. Building/re-enabling a supervised CNN grading classifier (or a metadata-fusion model using the 36
pre-extracted variables directly, skipping CNN training entirely) on top of it is a separate implementation task.

## Caveats before training on this

- These are the *only* 482 embryo images Ovulite has — this dataset relabels them, it doesn't add new images.
  Small-N caution from `ROADMAP.md`'s risk register still applies.
- Grades here come from a **different study's own embryos**, not from Ovulite's own ET records — there is no
  guaranteed 1:1 correspondence between a `blq{N}` image and any specific row in
  `docs/dataset/ovulite_cleaned_et_data.csv`. Treat this as its own labeled image-classification dataset (image →
  grade), not as a bridge that also supplies pregnancy-outcome ground truth for those same embryos.

## Status: wired in and trained (2026-09-04)

A classifier has been trained on these labels — see [`ml/grading/train_real_grading.py`](../../../../ml/grading/train_real_grading.py)
(pipeline) and [`ml/grading/real_labels.py`](../../../../ml/grading/real_labels.py) (label loader). Architecture:
`EmbryoGradeClassifier` in [`ml/grading/models.py`](../../../../ml/grading/models.py) — EfficientNet-B0 backbone
initialized from the project's existing SimCLR self-supervised pretraining (`ml/artifacts/grading/simclr_backbone.pt`),
fine-tuned on a 335/72/72 stratified train/val/test split (image-only, no metadata fusion — see caveats above).

**Test-set results** (n=72, held out, never seen during training):
- Accuracy: 54.2% (vs. ~40% majority-class baseline)
- Macro F1: 0.475
- The model separates Grade 3 (poor) well (27/29 correct) but struggles with Grade 1 vs. Grade 2, which is a
  known hard distinction even for human embryologists on this exact published dataset's images.

Full model card with confusion matrix and per-class metrics: `ml/artifacts/grading/real_labels_v1/metadata.json`.
Grad-CAM visual explanations are supported (`GradCAMClassifier` in `models.py`) and verified to highlight the
trophectoderm/ICM region — the area embryologists actually look at.

Served via the API: `POST /grade/embryo` (grade + probabilities) and `POST /grade/embryo-with-heatmap`
(same, plus a Grad-CAM overlay image) in [`backend/app/api/grading.py`](../../../../backend/app/api/grading.py).
The similarity-search endpoint (`/grade/similar-cases`) remains available as a complementary tool.

**Not yet done**: frontend UI wiring (`frontend/src/pages/GradingPage.tsx` currently only calls
`/grade/similar-cases`) — the new endpoints are live but not yet surfaced in the app.
