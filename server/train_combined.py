"""
PHANTOM PHOENIX — Combined Dataset Trainer
Trains on BOTH:
  1. HuggingFace real face dataset (saakshigupta/deepfake-detection-dataset-v3)
  2. Locally generated synthetic pattern images (prepare_dataset.py output)
This ensures the model generalizes across all image types.
"""

import os
import sys
import glob
import pickle
import numpy as np
from PIL import Image
from datasets import load_dataset
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DATASET_NAME    = "saakshigupta/deepfake-detection-dataset-v3"
MODEL_SAVE_PATH = "server/forensic_model.pkl"
MAX_HF_TRAIN    = 600   # HuggingFace images for train
MAX_HF_VAL      = 100   # HuggingFace images for val


# ─────────────────────────────────────────────
# FEATURE EXTRACTION (extended — 15 features)
# ─────────────────────────────────────────────
def extract_forensic_features(pil_img: Image.Image) -> list:
    """
    Extracts 15 forensic features from a PIL image:
      1-3  : RGB channel means
      4-6  : RGB channel std devs
      7    : Laplacian variance       (noise / blur profile)
      8    : Laplacian mean
      9    : FFT high-freq energy ratio (AI lattice artifacts)
      10   : Gradient magnitude mean  (edge sharpness)
      11   : Gradient magnitude std
      12   : Color skewness R
      13   : Color skewness G
      14   : Color skewness B
      15   : Pixel entropy (texture complexity)
    """
    img = pil_img.convert("RGB").resize((224, 224))
    arr = np.array(img, dtype=np.float32)

    # 1-6: RGB stats
    r_mean, g_mean, b_mean = arr[:, :, 0].mean(), arr[:, :, 1].mean(), arr[:, :, 2].mean()
    r_std,  g_std,  b_std  = arr[:, :, 0].std(),  arr[:, :, 1].std(),  arr[:, :, 2].std()

    # 7-8: Laplacian
    gray = 0.2989 * arr[:, :, 0] + 0.5870 * arr[:, :, 1] + 0.1140 * arr[:, :, 2]
    lap  = np.abs(
        gray[1:-1, 1:-1] * 4
        - gray[0:-2, 1:-1] - gray[2:, 1:-1]
        - gray[1:-1, 0:-2] - gray[1:-1, 2:]
    )
    noise_var  = float(lap.var())
    noise_mean = float(lap.mean())

    # 9: FFT high-freq energy ratio
    fft   = np.fft.fft2(gray)
    fft_s = np.fft.fftshift(fft)
    mag   = np.abs(fft_s)
    h, w  = gray.shape
    ch, cw = h // 2, w // 2
    high_freq  = float(np.sum(mag) - np.sum(mag[ch-20:ch+20, cw-20:cw+20]))
    fft_ratio  = high_freq / (float(np.sum(mag)) + 1e-6)

    # 10-11: Gradient magnitude (Sobel-like)
    gx = gray[1:-1, 2:] - gray[1:-1, :-2]
    gy = gray[2:, 1:-1] - gray[:-2, 1:-1]
    grad_mag = np.sqrt(gx**2 + gy**2)
    grad_mean = float(grad_mag.mean())
    grad_std  = float(grad_mag.std())

    # 12-14: Color channel skewness
    def skewness(ch):
        m = ch.mean()
        s = ch.std() + 1e-6
        return float(((ch - m) ** 3).mean() / s**3)

    r_skew = skewness(arr[:, :, 0])
    g_skew = skewness(arr[:, :, 1])
    b_skew = skewness(arr[:, :, 2])

    # 15: Pixel entropy (texture complexity)
    gray_uint8 = gray.astype(np.uint8)
    hist, _ = np.histogram(gray_uint8, bins=256, range=(0, 256))
    hist_norm = hist / (hist.sum() + 1e-6)
    entropy = float(-np.sum(hist_norm * np.log2(hist_norm + 1e-9)))

    return [
        r_mean, g_mean, b_mean,
        r_std,  g_std,  b_std,
        noise_var, noise_mean, fft_ratio,
        grad_mean, grad_std,
        r_skew, g_skew, b_skew,
        entropy
    ]


# ─────────────────────────────────────────────
# LOAD LOCAL SYNTHETIC IMAGES
# ─────────────────────────────────────────────
def load_local_dataset(split):
    """Load locally generated synthetic images from prepare_dataset.py output."""
    X, y = [], []
    for cls_name, label in [("REAL", 0), ("FAKE", 1)]:
        pattern = f"server/dataset/{split}/{cls_name}/*.jpg"
        files   = glob.glob(pattern)
        print(f"  [Local {split}] {cls_name}: {len(files)} files")
        for fpath in files:
            try:
                img   = Image.open(fpath)
                feats = extract_forensic_features(img)
                X.append(feats)
                y.append(label)
            except Exception as e:
                print(f"  [!] Skipped {fpath}: {e}")
    return X, y


# ─────────────────────────────────────────────
# LOAD HUGGINGFACE STREAMING DATASET
# ─────────────────────────────────────────────
def load_hf_dataset(split_data, max_samples, split_name):
    """Stream and extract features from HuggingFace dataset split."""
    X, y = [], []
    count = 0
    print(f"  [HuggingFace {split_name}] Streaming up to {max_samples} samples...")
    for i, sample in enumerate(split_data):
        if count >= max_samples:
            break
        try:
            pil_img   = sample["image"]
            raw_label = str(sample["label"]).strip().lower()
            label = 1 if raw_label in ("fake", "1", "deepfake", "ai_generated") else 0
            feats = extract_forensic_features(pil_img)
            X.append(feats)
            y.append(label)
            count += 1
            if count % 150 == 0:
                print(f"    -> {count} done...")
        except Exception as e:
            print(f"  [!] Skipped HF sample {i}: {e}")
    print(f"  [HuggingFace {split_name}] Collected: {count}")
    return X, y


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  PHANTOM PHOENIX - Combined Dataset Trainer")
    print("  Sources: HuggingFace + Local Synthetic")
    print("=" * 60)

    # ── 1. Load local synthetic images ─────────────────────────
    print("\n[1/5] Loading local synthetic dataset...")
    X_loc_tr, y_loc_tr = load_local_dataset("train")
    X_loc_vl, y_loc_vl = load_local_dataset("val")

    # ── 2. Load HuggingFace real-face dataset ──────────────────
    print("\n[2/5] Streaming HuggingFace dataset...")
    ds = load_dataset(DATASET_NAME, streaming=True)
    X_hf_tr, y_hf_tr = load_hf_dataset(ds["train"], MAX_HF_TRAIN, "train")
    val_key = "test" if "test" in ds else "validation"
    X_hf_vl, y_hf_vl = load_hf_dataset(ds[val_key], MAX_HF_VAL,   "val")

    # ── 3. Combine ─────────────────────────────────────────────
    print("\n[3/5] Combining datasets...")
    X_train = np.array(X_loc_tr + X_hf_tr)
    y_train = np.array(y_loc_tr + y_hf_tr)
    X_val   = np.array(X_loc_vl + X_hf_vl)
    y_val   = np.array(y_loc_vl + y_hf_vl)

    print(f"  Train -> REAL: {(y_train==0).sum()}, FAKE: {(y_train==1).sum()}, Total: {len(y_train)}")
    print(f"  Val   -> REAL: {(y_val==0).sum()},   FAKE: {(y_val==1).sum()},   Total: {len(y_val)}")

    # ── 4. Train ensemble model ────────────────────────────────
    print("\n[4/5] Training ensemble model (RandomForest + GradientBoosting)...")
    rf  = RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1)
    gb  = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42)
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("model",  VotingClassifier(
            estimators=[("rf", rf), ("gb", gb)],
            voting="soft"
        ))
    ])
    clf.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, clf.predict(X_train))
    val_acc   = accuracy_score(y_val,   clf.predict(X_val))

    print("\n=== TRAINING RESULTS ===")
    print(f"Training Accuracy   : {train_acc * 100:.2f}%")
    print(f"Validation Accuracy : {val_acc   * 100:.2f}%")
    print("\nClassification Report (Validation):")
    print(classification_report(y_val, clf.predict(X_val), target_names=["REAL", "FAKE"]))

    # ── 5. Save ────────────────────────────────────────────────
    print(f"[5/5] Saving model to: {MODEL_SAVE_PATH}")
    with open(MODEL_SAVE_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"[DONE] Model saved -> {MODEL_SAVE_PATH}")
    print("  Restart the ML server to load the new model.")


if __name__ == "__main__":
    main()
