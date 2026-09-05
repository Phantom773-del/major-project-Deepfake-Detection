"""
PHANTOM PHOENIX — HuggingFace Dataset Trainer
Dataset : prithivMLmods/Deepfake-vs-Real
Labels  : 0 = Deepfake, 1 = Real
"""

import os
import sys
import pickle
import numpy as np
from PIL import Image
from datasets import load_dataset
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DATASET_NAME    = "saakshigupta/deepfake-detection-dataset-v3"
MODEL_SAVE_PATH = "server/forensic_model.pkl"

# Limit samples for speed (set to None to use full dataset)
MAX_TRAIN_SAMPLES = 500    # rows to use from train split
MAX_VAL_SAMPLES   = 150    # rows to use from test split


# ─────────────────────────────────────────────
# FEATURE EXTRACTION  (same 9 forensic features)
# ─────────────────────────────────────────────
def extract_forensic_features(pil_img: Image.Image) -> list:
    """
    Extracts 9 forensic features from a PIL image:
      1-3  : RGB channel means
      4-6  : RGB channel std devs
      7    : Laplacian variance  (noise / blur profile)
      8    : Laplacian mean
      9    : 2D-FFT high-frequency energy ratio  (AI lattice artifacts)
    """
    img = pil_img.convert("RGB").resize((224, 224))
    arr = np.array(img, dtype=np.float32)

    # RGB stats
    r_mean, g_mean, b_mean = arr[:, :, 0].mean(), arr[:, :, 1].mean(), arr[:, :, 2].mean()
    r_std,  g_std,  b_std  = arr[:, :, 0].std(),  arr[:, :, 1].std(),  arr[:, :, 2].std()

    # Laplacian (noise / sharpness)
    gray = 0.2989 * arr[:, :, 0] + 0.5870 * arr[:, :, 1] + 0.1140 * arr[:, :, 2]
    lap  = np.abs(
        gray[1:-1, 1:-1] * 4
        - gray[0:-2, 1:-1] - gray[2:, 1:-1]
        - gray[1:-1, 0:-2] - gray[1:-1, 2:]
    )
    noise_var  = float(lap.var())
    noise_mean = float(lap.mean())

    # 2D FFT — high-freq energy ratio
    fft   = np.fft.fft2(gray)
    fft_s = np.fft.fftshift(fft)
    mag   = np.abs(fft_s)
    h, w  = gray.shape
    ch, cw = h // 2, w // 2
    high_freq  = float(np.sum(mag) - np.sum(mag[ch-20:ch+20, cw-20:cw+20]))
    total_freq = float(np.sum(mag)) + 1e-6
    fft_ratio  = high_freq / total_freq

    return [r_mean, g_mean, b_mean, r_std, g_std, b_std, noise_var, noise_mean, fft_ratio]


# ─────────────────────────────────────────────
# DATASET LOADING
# ─────────────────────────────────────────────
def build_features(split_data, max_samples=None, split_name="train"):
    """Extract features + labels from a HuggingFace iterable/map dataset split."""
    X, y = [], []
    count = 0

    print(f"\n[{split_name.upper()}] Processing up to {max_samples} samples...")
    for i, sample in enumerate(split_data):
        if max_samples and count >= max_samples:
            break
        try:
            pil_img = sample["image"]

            # Label can be int (0/1) or string ('real'/'fake')
            raw_label = sample["label"]
            raw_str   = str(raw_label).strip().lower()
            if isinstance(raw_label, int):
                # Use integer directly. For this dataset: 0=REAL, 1=FAKE
                # (verify with check_labels.py if unsure!)
                label = int(raw_label)
            elif raw_str in ("fake", "deepfake", "ai_generated"):
                label = 1   # FAKE
            elif raw_str in ("real", "authentic", "original"):
                label = 0   # REAL
            else:
                try:
                    label = int(raw_str)
                except ValueError:
                    print(f"  [!] Unknown label '{raw_label}' at sample {i}, skipping")
                    continue

            feats = extract_forensic_features(pil_img)
            X.append(feats)
            y.append(label)
            count += 1

            if count % 100 == 0:
                print(f"  -> Processed {count} images...")
        except Exception as e:
            print(f"  [!] Skipped sample {i}: {e}")

    print(f"  Total collected: {count}")
    return np.array(X), np.array(y)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  PHANTOM PHOENIX - HuggingFace Real Dataset Trainer")
    print("=" * 60)
    print(f"\nDataset : {DATASET_NAME}")
    print(f"Samples : {MAX_TRAIN_SAMPLES} train / {MAX_VAL_SAMPLES} val")

    # 1. Load dataset from HuggingFace (streaming avoids full download)
    print("\n[1/4] Streaming dataset from HuggingFace...")
    ds = load_dataset(DATASET_NAME, streaming=True)
    print(f"  Splits available: {list(ds.keys())}")

    train_split = "train"
    val_split   = "test" if "test" in ds else ("validation" if "validation" in ds else "train")
    print(f"  Using: train='{train_split}', val='{val_split}'")

    # 2. Extract features
    print("\n[2/4] Extracting forensic features...")
    X_train, y_train = build_features(ds[train_split], MAX_TRAIN_SAMPLES, "train")
    X_val,   y_val   = build_features(ds[val_split],   MAX_VAL_SAMPLES,   "val")

    real_tr = int((y_train == 0).sum())
    fake_tr = int((y_train == 1).sum())
    real_vl = int((y_val   == 0).sum())
    fake_vl = int((y_val   == 1).sum())

    print(f"\n  Train -> REAL: {real_tr}, FAKE: {fake_tr}, Total: {len(y_train)}")
    print(f"  Val   -> REAL: {real_vl}, FAKE: {fake_vl}, Total: {len(y_val)}")

    # 3. Train model
    print("\n[3/4] Training Random Forest (100 trees)...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, clf.predict(X_train))
    val_acc   = accuracy_score(y_val,   clf.predict(X_val))

    print("\n=== TRAINING RESULTS ===")
    print(f"Training Accuracy   : {train_acc * 100:.2f}%")
    print(f"Validation Accuracy : {val_acc   * 100:.2f}%")
    print("\nClassification Report (Validation):")
    print(classification_report(y_val, clf.predict(X_val), target_names=["REAL", "FAKE"]))

    # 4. Save model
    print(f"\n[4/4] Saving model to: {MODEL_SAVE_PATH}")
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    with open(MODEL_SAVE_PATH, "wb") as f:
        pickle.dump(clf, f)

    print(f"\n[DONE] Model saved -> {MODEL_SAVE_PATH}")
    print("   Restart the ML server to load the new model.")


if __name__ == "__main__":
    main()
