"""
PHANTOM PHOENIX — Local Dataset Trainer
Uses images already in server/dataset/ (no internet required)
  train/REAL/, train/FAKE/, val/REAL/, val/FAKE/
Same 35-feature ensemble as train_balanced.py
"""

import io
import os
import sys
import glob
import pickle
import numpy as np
from PIL import Image
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    VotingClassifier,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_DIR        = os.path.join("server", "dataset")
MODEL_SAVE_PATH = os.path.join("server", "forensic_model.pkl")
JPEG_AUGMENT_Q  = 75


# ─────────────────────────────────────────────
# JPEG AUGMENTATION
# ─────────────────────────────────────────────
def jpeg_compress(pil_img, quality=75):
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).copy()


# ─────────────────────────────────────────────
# 35-FEATURE EXTRACTION  (matches ml_server.py)
# ─────────────────────────────────────────────
def extract_forensic_features(pil_img):
    img = pil_img.convert("RGB").resize((224, 224))
    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    r_mean, g_mean, b_mean = r.mean(), g.mean(), b.mean()
    r_std,  g_std,  b_std  = r.std(),  g.std(),  b.std()

    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b

    lap = np.abs(gray[1:-1, 1:-1] * 4 - gray[0:-2, 1:-1]
                 - gray[2:, 1:-1] - gray[1:-1, 0:-2] - gray[1:-1, 2:])
    noise_var  = float(lap.var())
    noise_mean = float(lap.mean())

    fft   = np.fft.fft2(gray)
    fft_s = np.fft.fftshift(fft)
    mag   = np.abs(fft_s)
    h, w  = gray.shape
    ch, cw = h // 2, w // 2
    high_freq = float(np.sum(mag) - np.sum(mag[ch-20:ch+20, cw-20:cw+20]))
    fft_ratio = high_freq / (float(np.sum(mag)) + 1e-6)

    gx = gray[1:-1, 2:] - gray[1:-1, :-2]
    gy = gray[2:, 1:-1] - gray[:-2, 1:-1]
    grad_mag  = np.sqrt(gx**2 + gy**2)
    grad_mean = float(grad_mag.mean())
    grad_std  = float(grad_mag.std())

    def skewness(ch):
        m = ch.mean(); s = ch.std() + 1e-6
        return float(((ch - m) ** 3).mean() / s ** 3)
    r_skew, g_skew, b_skew = skewness(r), skewness(g), skewness(b)

    gray_u8 = gray.astype(np.uint8)
    hist, _ = np.histogram(gray_u8, bins=256, range=(0, 256))
    hist_n  = hist / (hist.sum() + 1e-6)
    entropy = float(-np.sum(hist_n * np.log2(hist_n + 1e-9)))

    def kurtosis(ch):
        m = ch.mean(); s = ch.std() + 1e-6
        return float(((ch - m) ** 4).mean() / s ** 4)
    r_kurt, g_kurt, b_kurt = kurtosis(r), kurtosis(g), kurtosis(b)

    def corr(a, b_ch):
        a_f, b_f = a.flatten(), b_ch.flatten()
        return float(np.corrcoef(a_f, b_f)[0, 1])
    rg_corr = corr(r, g); rb_corr = corr(r, b); gb_corr = corr(g, b)

    def block_var_std(ch, block=8):
        rows, cols = ch.shape[0] // block, ch.shape[1] // block
        vars_ = [float(ch[i*block:(i+1)*block, j*block:(j+1)*block].var())
                 for i in range(rows) for j in range(cols)]
        return float(np.std(vars_)) if vars_ else 0.0
    bv_r, bv_g, bv_b = block_var_std(r), block_var_std(g), block_var_std(b)

    def dct_hf_energy(ch, block=8):
        rows, cols = ch.shape[0] // block, ch.shape[1] // block
        energies = []
        for i in range(rows):
            for j in range(cols):
                patch = ch[i*block:(i+1)*block, j*block:(j+1)*block]
                f = np.fft.fft2(patch)
                mag_b = np.abs(f)
                total = mag_b.sum() + 1e-6
                energies.append(float((total - mag_b[0, 0]) / total))
        return float(np.mean(energies)) if energies else 0.0
    dct_r, dct_g, dct_b = dct_hf_energy(r), dct_hf_energy(g), dct_hf_energy(b)

    def michelson_contrast(ch, block=16):
        rows, cols = ch.shape[0] // block, ch.shape[1] // block
        contrasts = []
        for i in range(rows):
            for j in range(cols):
                patch = ch[i*block:(i+1)*block, j*block:(j+1)*block]
                mn, mx = patch.min(), patch.max()
                contrasts.append(float((mx - mn) / (mx + mn + 1e-6)))
        return float(np.mean(contrasts)) if contrasts else 0.0
    mc_r, mc_g, mc_b = michelson_contrast(r), michelson_contrast(g), michelson_contrast(b)

    def box_blur(ch, kernel=5):
        from numpy.lib.stride_tricks import as_strided
        pad = kernel // 2
        padded = np.pad(ch, pad, mode='reflect')
        view_shape = (ch.shape[0], ch.shape[1], kernel, kernel)
        strides = padded.strides + padded.strides
        patches = as_strided(padded, shape=view_shape, strides=strides)
        return patches.mean(axis=(2, 3))
    residual = gray - box_blur(gray, kernel=5)
    res_mean, res_std = float(residual.mean()), float(residual.std())

    img_hsv  = np.array(img.convert("HSV"), dtype=np.float32)
    sat, hue = img_hsv[:, :, 1], img_hsv[:, :, 0]
    sat_mean, sat_std, hue_std = float(sat.mean()), float(sat.std()), float(hue.std())

    return [
        r_mean, g_mean, b_mean, r_std,  g_std,  b_std,
        noise_var, noise_mean, fft_ratio,
        grad_mean, grad_std,
        r_skew, g_skew, b_skew,
        entropy,
        r_kurt, g_kurt, b_kurt,
        rg_corr, rb_corr, gb_corr,
        bv_r, bv_g, bv_b,
        dct_r, dct_g, dct_b,
        mc_r, mc_g, mc_b,
        res_mean, res_std,
        sat_mean, sat_std, hue_std,
    ]


# ─────────────────────────────────────────────
# LOAD FROM LOCAL FOLDER
# ─────────────────────────────────────────────
def load_split(split_name, augment=False):
    X, y = [], []
    split_dir = os.path.join(BASE_DIR, split_name)
    
    for label_name, label_val in [("REAL", 0), ("FAKE", 1)]:
        folder = os.path.join(split_dir, label_name)
        files  = sorted(glob.glob(os.path.join(folder, "*.jpg")) +
                        glob.glob(os.path.join(folder, "*.png")) +
                        glob.glob(os.path.join(folder, "*.jpeg")))
        print(f"  [{split_name}/{label_name}] {len(files)} images found")

        for i, fpath in enumerate(files):
            try:
                img  = Image.open(fpath).convert("RGB")
                feat = extract_forensic_features(img)
                X.append(feat)
                y.append(label_val)

                if augment:
                    aug_feat = extract_forensic_features(jpeg_compress(img, JPEG_AUGMENT_Q))
                    X.append(aug_feat)
                    y.append(label_val)

                if (i + 1) % 20 == 0:
                    print(f"    -> {i+1}/{len(files)} done")
            except Exception as e:
                print(f"    [!] Skipped {fpath}: {e}")

    print(f"  [{split_name}] Total: {len(X)} samples | Distribution: {dict(Counter(y))}")
    return np.array(X), np.array(y)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  PHANTOM PHOENIX - Local Dataset Trainer")
    print("  35 Forensic Features | JPEG Augmentation | Ensemble")
    print("=" * 65)

    print(f"\n[1/4] Loading local dataset from: {BASE_DIR}")
    print("\nExtracting TRAIN features...")
    X_train, y_train = load_split("train", augment=True)

    print("\nExtracting VAL features...")
    X_val, y_val = load_split("val", augment=False)

    print(f"\n  Train shape: {X_train.shape}  | Labels: {dict(Counter(y_train))}")
    print(f"  Val   shape: {X_val.shape}    | Labels: {dict(Counter(y_val))}")
    print(f"  Feature vector size: {X_train.shape[1]}")

    print("\n[3/4] Training ensemble (RF + GBT + ExtraTrees + StandardScaler)...")
    rf  = RandomForestClassifier(
        n_estimators=300, max_depth=25, random_state=42,
        n_jobs=-1, class_weight="balanced", min_samples_leaf=2
    )
    gbt = GradientBoostingClassifier(
        n_estimators=150, max_depth=6, learning_rate=0.08,
        random_state=42, subsample=0.8
    )
    et  = ExtraTreesClassifier(
        n_estimators=300, max_depth=25, random_state=42,
        n_jobs=-1, class_weight="balanced", min_samples_leaf=2
    )
    ensemble = VotingClassifier([("rf", rf), ("gbt", gbt), ("et", et)], voting="soft")
    pipeline = Pipeline([("scaler", StandardScaler()), ("classifier", ensemble)])

    print("  Fitting model (this may take 2–5 minutes)...")
    pipeline.fit(X_train, y_train)

    train_preds = pipeline.predict(X_train)
    val_preds   = pipeline.predict(X_val)
    train_acc   = accuracy_score(y_train, train_preds)
    val_acc     = accuracy_score(y_val,   val_preds)

    print("\n" + "=" * 65)
    print("  TRAINING RESULTS")
    print("=" * 65)
    print(f"  Training Accuracy   : {train_acc * 100:.2f}%")
    print(f"  Validation Accuracy : {val_acc   * 100:.2f}%")
    print("\nClassification Report (Validation):")
    print(classification_report(y_val, val_preds, target_names=["REAL", "FAKE"]))

    print(f"\n[4/4] Saving model -> {MODEL_SAVE_PATH}")
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    with open(MODEL_SAVE_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"[DONE] Model saved -> {MODEL_SAVE_PATH}")
    print("  Restart ml_server.py to load the new model.")


if __name__ == "__main__":
    main()
