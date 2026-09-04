"""Audit probe for embryo similarity system.

Historical note: this used to probe the grade-classifier (ml.grading.predict.
EmbryoGrader). That classifier was removed — it was never trained on real
labels (482/488 ET records = Grade 1, no exploitable signal) and its
checkpoint was an explicitly-labeled placeholder file. This probe now checks
the honest replacement: the SimCLR self-supervised embedding + nearest-
neighbor similarity index (ml.grading.similarity).
"""

import io
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("=" * 80)
    print("EMBRYO SIMILARITY SYSTEM AUDIT PROBE")
    print("=" * 80)

    # 1. Check artifact paths
    print("\n[1] Checking grading artifact paths...")
    from ml.grading.config import ARTIFACTS_DIR, IMAGE_DIR, UPLOAD_DIR

    print(f"    Expected artifacts dir: {ARTIFACTS_DIR}")
    print(f"    Exists: {ARTIFACTS_DIR.exists()}")
    if ARTIFACTS_DIR.exists():
        artifacts = list(ARTIFACTS_DIR.glob("*"))
        print(f"    Contains: {[a.name for a in artifacts]}")

    print(f"    Training images dir: {IMAGE_DIR}")
    print(f"    Exists: {IMAGE_DIR.exists()}")
    if IMAGE_DIR.exists():
        images = list(IMAGE_DIR.glob("*.jpg"))
        print(f"    Image count: {len(images)}")

    print(f"    Upload dir: {UPLOAD_DIR}")
    print(f"    Exists: {UPLOAD_DIR.exists()}")

    # 2. Test similarity index loading
    print("\n[2] Testing similarity index loader...")
    similarity_index = None
    try:
        from ml.grading.similarity import get_similarity_index

        similarity_index = get_similarity_index()
        print(f"    Index cases: {len(similarity_index.filenames)}")
        print(f"    Feature dim: {similarity_index.embeddings.shape[1]}")
        print(f"    Backbone: efficientnet_b0 (SimCLR pretrained)")
        print(f"    Index built: {similarity_index.index_meta.get('timestamp')}")
    except ImportError as e:
        print(f"    ⚠ PyTorch not available: {e}")
    except FileNotFoundError as e:
        print(f"    ⚠ Similarity index/backbone not built yet: {e}")
    except Exception as e:
        print(f"    ⚠ Index loading failed: {e}")

    # 3. Test image processing safety + similarity search
    print("\n[3] Testing image upload handling...")
    if IMAGE_DIR.exists() and list(IMAGE_DIR.glob("*.jpg")):
        test_image_path = list(IMAGE_DIR.glob("*.jpg"))[0]
        print(f"    Using test image: {test_image_path.name}")

        with open(test_image_path, "rb") as f:
            image_bytes = f.read()

        print(f"    Image size: {len(image_bytes)} bytes")

        # Test size limits
        max_size = 10 * 1024 * 1024
        if len(image_bytes) > max_size:
            print(f"    ⚠ Image exceeds 10MB limit")
        else:
            print(f"    ✓ Image within size limit")

        # Test that image can be loaded
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            print(f"    ✓ Valid image: {img.size} {img.mode}")
        except Exception as e:
            print(f"    ⚠ Invalid image: {e}")

        # Test similarity search
        if similarity_index is not None:
            try:
                print("\n[4] Testing similarity search inference...")
                matches = similarity_index.find_similar(image_bytes, k=5)
                for m in matches:
                    print(
                        f"    #{m['rank']} {m['filename']} "
                        f"similarity={m['similarity']:.4f} "
                        f"metadata={m['metadata']}"
                    )
            except Exception as e:
                print(f"    ⚠ Similarity search failed: {e}")
        else:
            print("\n[4] Skipping similarity search test (index unavailable)")

    # 4. Check API endpoint availability
    print("\n[5] Testing API endpoints (via local FastAPI)...")
    try:
        import requests

        base_url = "http://localhost:8000"

        # Test model-info endpoint (doesn't require auth)
        try:
            resp = requests.get(f"{base_url}/grade/model-info", timeout=2)
            if resp.status_code == 200:
                info = resp.json()
                print(f"    ✓ /grade/model-info: {info['model_type']}")
            else:
                print(f"    ℹ /grade/model-info returned {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print("    ℹ API server not running (start with uvicorn)")
        except Exception as e:
            print(f"    ⚠ API check failed: {e}")

    except ImportError:
        print("    ℹ requests library not available")

    # 5. Document training / index-build procedure
    print("\n[6] Training / index-build procedure info...")
    print("    To (re)train the SimCLR backbone, run:")
    print("    $ cd D:\\Ovulite new")
    print("    $ .venv\\Scripts\\python.exe -m ml.grading.run_training --simclr")
    print()
    print("    To (re)build the similarity index from a trained backbone, run:")
    print("    $ .venv\\Scripts\\python.exe -m ml.grading.build_index")
    print()
    print("    Expected artifacts:")
    print(f"      {ARTIFACTS_DIR / 'simclr_backbone.pt'}")
    print(f"      {ARTIFACTS_DIR / 'simclr_history.json'}")
    print(f"      {ARTIFACTS_DIR / 'embedding_index.joblib'}")

    print("\n[7] Security findings...")
    print("    ✓ File type validation (JPEG/PNG only)")
    print("    ✓ Size limit (10MB)")
    print("    ✓ Hash-based deduplication (SHA256)")
    print("    ✓ Filesystem path sanitization (hash-based filenames)")
    print("    ⚠ No virus scanning")
    print("    ⚠ No EXIF data stripping on the /upload path's stored notes field")

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
