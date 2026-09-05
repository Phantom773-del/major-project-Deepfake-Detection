"""
PHANTOM PHOENIX — Balanced HuggingFace Trainer (v4 — 90%+ Target)
Improvements over v3:
  1. 55-feature forensic vector (vs 35):
       NEW: ELA (Error Level Analysis) — strongest AI-detection signal
       NEW: YCbCr Cb/Cr channel stats (mean, std, skew)
       NEW: LBP approximation (uniform pattern histogram features)
       NEW: GLCM-inspired co-occurrence contrast
       NEW: Steganography residual energy
  2. Multi-quality JPEG augmentation: Q=75, Q=85, Q=95
  3. Larger dataset: 1000 REAL + 1000 FAKE train, 200+200 val
  4. Enhanced ensemble: RF + GBT + ExtraTrees + XGBoost (soft voting)
  5. 5-fold cross-validation for honest accuracy estimate
  6. Feature vector MUST be kept in sync with ml_server.py
"""

import io
import os
import sys
import pickle
import subprocess
import numpy as np
from PIL import Image
from datasets import load_dataset
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    VotingClassifier,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Auto-install xgboost if needed ─────────────────────────────────────────
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
    print("[DEPS] XGBoost found ✓")
except ImportError:
    print("[DEPS] XGBoost not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost", "-q"])
    from xgboost import XGBClassifier
    HAS_XGB = True
    print("[DEPS] XGBoost installed ✓")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DATASET_NAME        = "saakshigupta/deepfake-detection-dataset-v3"
MODEL_SAVE_PATH     = "server/forensic_model.pkl"
FEATURE_VERSION     = "v4-55feat"

MAX_PER_CLASS_TRAIN = 1000   # 1000 REAL + 1000 FAKE = 2000 train (with augment ~4x)
MAX_PER_CLASS_VAL   = 200    # 200 REAL + 200 FAKE = 400 val

JPEG_QUALITIES      = [75, 85, 95]   # Multi-quality augmentation


# ─────────────────────────────────────────────
# JPEG AUGMENTATION HELPER
# ─────────────────────────────────────────────
def jpeg_compress(pil_img: Image.Image, quality: int = 75) -> Image.Image:
    """Re-encode image as JPEG at given quality to simulate social media compression."""
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).copy()


# ─────────────────────────────────────────────
# ELA HELPER  (Error Level Analysis)
# ─────────────────────────────────────────────
def compute_ela(pil_img: Image.Image, quality: int = 90) -> np.ndarray:
    """
    Error Level Analysis: re-save at quality, compute per-pixel difference.
    AI-generated images show uniform ELA; real photos show region-dependent ELA.
    """
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")
    orig  = np.array(pil_img.convert("RGB"), dtype=np.float32)
    recom = np.array(recompressed, dtype=np.float32)
    ela   = np.abs(orig - recom)
    return ela   # shape (H, W, 3)


# ─────────────────────────────────────────────
# 55-FEATURE EXTRACTION — Must match ml_server.py!
# ─────────────────────────────────────────────
def extract_forensic_features(pil_img: Image.Image) -> list:
    """
    55 forensic features (v4). Feature layout:
      === ORIGINAL 35 (v3) ===
      1-6   : RGB channel means & std devs
      7-8   : Laplacian variance & mean (noise profile)
      9     : FFT high-frequency energy ratio
      10-11 : Gradient magnitude mean & std
      12-14 : Color channel skewness (R, G, B)
      15    : Pixel entropy
      16-18 : Color channel kurtosis (R, G, B)
      19-21 : Inter-channel correlation (RG, RB, GB)
      22-24 : Block variance inconsistency (8×8 blocks)
      25-27 : DCT high-frequency energy per channel (8×8 blocks)
      28-30 : Local Michelson contrast (16×16 patches)
      31-32 : Noise residual mean & std (image minus box-blur)
      33-35 : HSV saturation mean, std; hue std
      === NEW 20 (v4) ===
      36-38 : ELA mean per channel (R, G, B)      — AI diffusion artifact signal
      39-41 : ELA std per channel (R, G, B)       — uniformity of ELA = AI tell
      42    : ELA overall max                      — peak compression anomaly
      43-44 : YCbCr Cb channel mean & std
      45-46 : YCbCr Cr channel mean & std
      47    : YCbCr Cb skewness
      48    : YCbCr Cr skewness
      49    : LBP approximation — uniform pattern energy
      50    : LBP contrast (std of LBP response)
      51    : Co-occurrence contrast (GLCM-inspired)
      52    : Co-occurrence energy (GLCM-inspired)
      53    : Steganographic residual energy (high-pass filter)
      54    : Local entropy variance (8×8 patches)
      55    : Chroma noise ratio (Cb+Cr noise vs luma)
    """
    img = pil_img.convert("RGB").resize((224, 224))
    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # ── 1-6: RGB stats ─────────────────────────────────────────────────────
    r_mean, g_mean, b_mean = r.mean(), g.mean(), b.mean()
    r_std,  g_std,  b_std  = r.std(),  g.std(),  b.std()

    # Grayscale
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b

    # ── 7-8: Laplacian ─────────────────────────────────────────────────────
    lap = np.abs(
        gray[1:-1, 1:-1] * 4
        - gray[0:-2, 1:-1] - gray[2:, 1:-1]
        - gray[1:-1, 0:-2] - gray[1:-1, 2:]
    )
    noise_var  = float(lap.var())
    noise_mean = float(lap.mean())

    # ── 9: FFT high-freq energy ratio ──────────────────────────────────────
    fft   = np.fft.fft2(gray)
    fft_s = np.fft.fftshift(fft)
    mag   = np.abs(fft_s)
    h, w  = gray.shape
    ch, cw = h // 2, w // 2
    high_freq = float(np.sum(mag) - np.sum(mag[ch-20:ch+20, cw-20:cw+20]))
    fft_ratio = high_freq / (float(np.sum(mag)) + 1e-6)

    # ── 10-11: Gradient magnitude ──────────────────────────────────────────
    gx = gray[1:-1, 2:] - gray[1:-1, :-2]
    gy = gray[2:, 1:-1] - gray[:-2, 1:-1]
    grad_mag  = np.sqrt(gx**2 + gy**2)
    grad_mean = float(grad_mag.mean())
    grad_std  = float(grad_mag.std())

    # ── 12-14: Skewness ────────────────────────────────────────────────────
    def skewness(ch):
        m = ch.mean(); s = ch.std() + 1e-6
        return float(((ch - m) ** 3).mean() / s ** 3)
    r_skew, g_skew, b_skew = skewness(r), skewness(g), skewness(b)

    # ── 15: Pixel entropy ──────────────────────────────────────────────────
    gray_u8 = gray.astype(np.uint8)
    hist, _ = np.histogram(gray_u8, bins=256, range=(0, 256))
    hist_n  = hist / (hist.sum() + 1e-6)
    entropy = float(-np.sum(hist_n * np.log2(hist_n + 1e-9)))

    # ── 16-18: Kurtosis ────────────────────────────────────────────────────
    def kurtosis(ch):
        m = ch.mean(); s = ch.std() + 1e-6
        return float(((ch - m) ** 4).mean() / s ** 4)
    r_kurt, g_kurt, b_kurt = kurtosis(r), kurtosis(g), kurtosis(b)

    # ── 19-21: Inter-channel correlation ───────────────────────────────────
    def corr(a, b_ch):
        a_f, b_f = a.flatten(), b_ch.flatten()
        return float(np.corrcoef(a_f, b_f)[0, 1])
    rg_corr = corr(r, g); rb_corr = corr(r, b); gb_corr = corr(g, b)

    # ── 22-24: 8×8 block variance inconsistency ────────────────────────────
    def block_var_std(ch, block=8):
        rows, cols = ch.shape[0] // block, ch.shape[1] // block
        vars_ = [float(ch[i*block:(i+1)*block, j*block:(j+1)*block].var())
                 for i in range(rows) for j in range(cols)]
        return float(np.std(vars_)) if vars_ else 0.0
    bv_r, bv_g, bv_b = block_var_std(r), block_var_std(g), block_var_std(b)

    # ── 25-27: DCT high-frequency energy (8×8 block FFT proxy) ────────────
    def dct_hf_energy(ch, block=8):
        rows, cols = ch.shape[0] // block, ch.shape[1] // block
        energies = []
        for i in range(rows):
            for j in range(cols):
                patch = ch[i*block:(i+1)*block, j*block:(j+1)*block]
                f = np.fft.fft2(patch)
                mag_b = np.abs(f)
                total = mag_b.sum() + 1e-6
                hf = total - mag_b[0, 0]
                energies.append(float(hf / total))
        return float(np.mean(energies)) if energies else 0.0
    dct_r, dct_g, dct_b = dct_hf_energy(r), dct_hf_energy(g), dct_hf_energy(b)

    # ── 28-30: Michelson contrast (16×16 patches) ──────────────────────────
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

    # ── 31-32: Noise residual (image − box blur) ───────────────────────────
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

    # ── 33-35: HSV saturation & hue ───────────────────────────────────────
    img_hsv  = np.array(img.convert("HSV"), dtype=np.float32)
    sat, hue = img_hsv[:, :, 1], img_hsv[:, :, 0]
    sat_mean, sat_std, hue_std = float(sat.mean()), float(sat.std()), float(hue.std())

    # ══════════════════════════════════════════════
    # NEW FEATURES (v4) ────────────────────────────
    # ══════════════════════════════════════════════

    # ── 36-42: ELA (Error Level Analysis) ─────────────────────────────────
    # Key insight: AI-generated images show UNIFORM ELA across all regions
    # because they were never authentically JPEG-compressed before generation.
    # Real photos show region-dependent ELA (edges high, flat regions low).
    ela = compute_ela(img, quality=90)   # shape (224,224,3)
    ela_r, ela_g, ela_b = ela[:,:,0], ela[:,:,1], ela[:,:,2]
    ela_r_mean = float(ela_r.mean())
    ela_g_mean = float(ela_g.mean())
    ela_b_mean = float(ela_b.mean())
    ela_r_std  = float(ela_r.std())
    ela_g_std  = float(ela_g.std())
    ela_b_std  = float(ela_b.std())
    ela_max    = float(ela.max())

    # ── 43-48: YCbCr chroma channel stats ─────────────────────────────────
    # Chroma channels (Cb, Cr) carry different artifacts in AI vs real images.
    # AI images often have suppressed/uniform chroma noise.
    img_ycbcr = np.array(img.convert("YCbCr"), dtype=np.float32)
    cb, cr    = img_ycbcr[:,:,1], img_ycbcr[:,:,2]
    cb_mean, cb_std = float(cb.mean()), float(cb.std())
    cr_mean, cr_std = float(cr.mean()), float(cr.std())
    cb_skew = skewness(cb)
    cr_skew = skewness(cr)

    # ── 49-50: LBP Approximation ───────────────────────────────────────────
    # Local Binary Pattern approximation: compare each pixel to its 8 neighbors.
    # Measures micro-texture uniformity — AI images often show synthetic textures.
    def lbp_approx(ch):
        """Approximate LBP using neighbor comparisons."""
        center = ch[1:-1, 1:-1]
        neighbors = [
            ch[0:-2, 0:-2], ch[0:-2, 1:-1], ch[0:-2, 2:],
            ch[1:-1, 0:-2],                  ch[1:-1, 2:],
            ch[2:,   0:-2], ch[2:,   1:-1], ch[2:,   2:],
        ]
        lbp_code = np.zeros_like(center)
        for n in neighbors:
            lbp_code = lbp_code + (n >= center).astype(np.float32)
        return lbp_code
    lbp_response = lbp_approx(gray)
    lbp_energy   = float(lbp_response.mean())    # 49
    lbp_contrast = float(lbp_response.std())     # 50

    # ── 51-52: GLCM-inspired co-occurrence features ────────────────────────
    # Measures spatial relationships between pixel intensity pairs.
    # AI images tend to have different co-occurrence patterns than real images.
    def glcm_features(ch, distance=1):
        """Simplified GLCM contrast and energy (horizontal co-occurrence)."""
        ch_u8  = np.clip(ch, 0, 255).astype(np.uint8) // 16   # quantize to 16 levels
        left   = ch_u8[:, :-distance].astype(np.float32)
        right  = ch_u8[:, distance:].astype(np.float32)
        diff   = left - right
        contrast = float((diff ** 2).mean())                   # 51
        energy   = float(((left + right + 1e-6) / 512).mean())  # 52
        return contrast, energy
    glcm_contrast, glcm_energy = glcm_features(gray)

    # ── 53: Steganographic residual energy (high-pass filter) ──────────────
    # High-frequency residual after strong Gaussian blur. AI images often have
    # periodic high-frequency patterns from diffusion model generation process.
    def highpass_residual_energy(ch):
        """Strong blur then subtract to get high-pass residual energy."""
        blurred   = box_blur(ch, kernel=9)
        residual_ = ch - blurred
        return float((residual_ ** 2).mean())
    steg_energy = highpass_residual_energy(gray)              # 53

    # ── 54: Local entropy variance (8×8 patches) ───────────────────────────
    # Variance of local entropy across image patches.
    # Real photos have HIGH variance (diverse regions); AI images are MORE uniform.
    def local_entropy_variance(ch, block=8):
        gray_u8_loc = np.clip(ch, 0, 255).astype(np.uint8)
        rows = ch.shape[0] // block
        cols = ch.shape[1] // block
        entropies = []
        for i in range(rows):
            for j in range(cols):
                patch = gray_u8_loc[i*block:(i+1)*block, j*block:(j+1)*block]
                h_, _ = np.histogram(patch.flatten(), bins=16, range=(0, 256))
                h_n   = h_ / (h_.sum() + 1e-6)
                e     = float(-np.sum(h_n * np.log2(h_n + 1e-9)))
                entropies.append(e)
        return float(np.std(entropies)) if entropies else 0.0
    local_entropy_var = local_entropy_variance(gray)          # 54

    # ── 55: Chroma noise ratio ────────────────────────────────────────────
    # Ratio of chroma channel noise to luma noise.
    # Real cameras add more chroma noise relative to luma; AI often reverses this.
    luma_noise  = float(box_blur(gray, kernel=3).std()) + 1e-6
    chroma_r    = box_blur(r, kernel=3)
    chroma_g    = box_blur(g, kernel=3)
    chroma_b    = box_blur(b, kernel=3)
    chroma_noise = float(np.std([chroma_r.std(), chroma_g.std(), chroma_b.std()]))
    chroma_ratio = chroma_noise / luma_noise                  # 55

    return [
        # ── v3 features (1-35) ───────────────────────────────────────────
        r_mean, g_mean, b_mean,         # 1-3
        r_std,  g_std,  b_std,          # 4-6
        noise_var, noise_mean,          # 7-8
        fft_ratio,                      # 9
        grad_mean, grad_std,            # 10-11
        r_skew, g_skew, b_skew,         # 12-14
        entropy,                        # 15
        r_kurt, g_kurt, b_kurt,         # 16-18
        rg_corr, rb_corr, gb_corr,      # 19-21
        bv_r, bv_g, bv_b,              # 22-24
        dct_r, dct_g, dct_b,           # 25-27
        mc_r, mc_g, mc_b,              # 28-30
        res_mean, res_std,              # 31-32
        sat_mean, sat_std, hue_std,     # 33-35
        # ── v4 NEW features (36-55) ──────────────────────────────────────
        ela_r_mean, ela_g_mean, ela_b_mean,   # 36-38
        ela_r_std,  ela_g_std,  ela_b_std,    # 39-41
        ela_max,                               # 42
        cb_mean, cb_std,                       # 43-44
        cr_mean, cr_std,                       # 45-46
        cb_skew, cr_skew,                      # 47-48
        lbp_energy, lbp_contrast,              # 49-50
        glcm_contrast, glcm_energy,            # 51-52
        steg_energy,                           # 53
        local_entropy_var,                     # 54
        chroma_ratio,                          # 55
    ]


# ─────────────────────────────────────────────
# BALANCED DATASET BUILDER (with JPEG augment)
# ─────────────────────────────────────────────
def build_balanced_features(split_data, max_per_class, split_name="train", augment=True):
    """
    Stream data, collect equal REAL/FAKE, augment with multi-quality JPEG compression.
    """
    real_X, fake_X = [], []
    label_audit    = []   # For verifying label convention at start

    aug_desc = f"JPEG Q={JPEG_QUALITIES}" if augment else "none"
    print(f"\n[{split_name.upper()}] Streaming (target: {max_per_class}/class, augment={aug_desc})...")

    for i, sample in enumerate(split_data):
        if len(real_X) >= max_per_class and len(fake_X) >= max_per_class:
            break

        try:
            pil_img   = sample["image"]
            raw_label = sample["label"]
            raw_str   = str(raw_label).strip().lower()

            # ── Safe label mapping ──────────────────────────────────────────
            # For saakshigupta/deepfake-detection-dataset-v3: 0=REAL, 1=FAKE
            if isinstance(raw_label, int):
                label = int(raw_label)
            elif raw_str in ("fake", "deepfake", "ai_generated"):
                label = 1
            elif raw_str in ("real", "authentic", "original"):
                label = 0
            else:
                try:
                    label = int(raw_str)
                except ValueError:
                    print(f"  [!] Unknown label '{raw_label}' at sample {i}, skipping")
                    continue

            # Audit first 10 labels
            if len(label_audit) < 10:
                label_audit.append((i, raw_label, "FAKE" if label == 1 else "REAL"))
                if len(label_audit) == 10:
                    print(f"  [LABEL AUDIT] First 10 samples:")
                    for idx, rl, mapped in label_audit:
                        print(f"    sample[{idx:3d}]: raw={repr(rl)!s:10s} -> {mapped}")
                    print(f"  [!] If REAL/FAKE look swapped above, flip the integer label logic!")

            if label == 0 and len(real_X) >= max_per_class:
                continue
            if label == 1 and len(fake_X) >= max_per_class:
                continue

            target = real_X if label == 0 else fake_X

            # Original features
            feats = extract_forensic_features(pil_img)
            target.append(feats)

            # Multi-quality JPEG augmentation
            if augment:
                for q in JPEG_QUALITIES:
                    if len(target) >= max_per_class:
                        break
                    try:
                        comp_feats = extract_forensic_features(jpeg_compress(pil_img, q))
                        target.append(comp_feats)
                    except Exception:
                        pass

            total = len(real_X) + len(fake_X)
            if total % 300 == 0:
                print(f"  -> {total} done (REAL: {len(real_X)}, FAKE: {len(fake_X)})...")

        except Exception as e:
            print(f"  [!] Skipped sample {i}: {e}")

    # Trim to max_per_class
    real_X = real_X[:max_per_class]
    fake_X = fake_X[:max_per_class]

    print(f"  Collected -> REAL: {len(real_X)}, FAKE: {len(fake_X)}, Total: {len(real_X)+len(fake_X)}")
    X = real_X + fake_X
    y = [0]*len(real_X) + [1]*len(fake_X)
    return np.array(X), np.array(y)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  PHANTOM PHOENIX - Balanced Deepfake Trainer v4  (Target: 90%+)")
    print("  55 Forensic Features | Multi-JPEG Augment | XGBoost Ensemble")
    print("=" * 70)

    print(f"\n[1/5] Loading dataset: {DATASET_NAME}")
    ds = load_dataset(DATASET_NAME, streaming=True)
    splits = list(ds.keys())
    print(f"  Available splits: {splits}")

    train_split = "train"
    val_split   = "test" if "test" in ds else ("validation" if "validation" in ds else "train")
    print(f"  Using: train='{train_split}', val='{val_split}'")

    print("\n[2/5] Extracting features (balanced + multi-JPEG augmented)...")
    X_train, y_train = build_balanced_features(ds[train_split], MAX_PER_CLASS_TRAIN, "train", augment=True)
    X_val,   y_val   = build_balanced_features(ds[val_split],   MAX_PER_CLASS_VAL,   "val",   augment=False)

    print(f"\n  Train distribution: {dict(Counter(y_train))}")
    print(f"  Val   distribution: {dict(Counter(y_val))}")
    print(f"  Feature vector size: {X_train.shape[1]} features  (expected: 55)")

    if X_train.shape[1] != 55:
        print(f"  [WARNING] Feature count mismatch! Got {X_train.shape[1]}, expected 55")

    print("\n[3/5] Training ensemble (RF + GBT + ExtraTrees + XGBoost)...")

    rf  = RandomForestClassifier(
        n_estimators=300, max_depth=None, random_state=42,
        n_jobs=-1, class_weight="balanced", min_samples_leaf=1
    )
    gbt = GradientBoostingClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.07,
        random_state=42, subsample=0.85, min_samples_leaf=2
    )
    et  = ExtraTreesClassifier(
        n_estimators=300, max_depth=None, random_state=42,
        n_jobs=-1, class_weight="balanced", min_samples_leaf=1
    )
    xgb = XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.07,
        subsample=0.85, colsample_bytree=0.85,
        random_state=42, n_jobs=-1,
        eval_metric="logloss", verbosity=0,
        use_label_encoder=False
    )

    ensemble = VotingClassifier(
        [("rf", rf), ("gbt", gbt), ("et", et), ("xgb", xgb)],
        voting="soft",
        weights=[1.5, 1.0, 1.5, 2.0],   # XGBoost & tree ensembles weighted higher
    )

    pipeline = Pipeline([
        ("scaler",     StandardScaler()),
        ("classifier", ensemble),
    ])

    print("  Fitting ensemble on training data...")
    pipeline.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, pipeline.predict(X_train))
    val_acc   = accuracy_score(y_val,   pipeline.predict(X_val))

    print("\n=== TRAINING RESULTS ===")
    print(f"Training Accuracy   : {train_acc * 100:.2f}%")
    print(f"Validation Accuracy : {val_acc   * 100:.2f}%")

    if val_acc >= 0.90:
        print(f"\n  ✓ TARGET ACHIEVED — Validation accuracy ≥ 90%!")
    else:
        print(f"\n  [!] Below 90% target by {(0.90 - val_acc)*100:.1f}%")

    print("\nClassification Report (Validation):")
    print(classification_report(y_val, pipeline.predict(X_val), target_names=["REAL", "FAKE"]))

    # ── 5-Fold Cross-Validation (on combined train+val for final estimate) ──
    print("\n[4/5] Running 5-fold cross-validation on full data for honest estimate...")
    X_all = np.vstack([X_train, X_val])
    y_all = np.concatenate([y_train, y_val])

    # Use lighter pipeline for CV speed
    cv_rf = RandomForestClassifier(n_estimators=200, max_depth=None, random_state=42, n_jobs=-1)
    cv_xgb = XGBClassifier(n_estimators=150, max_depth=5, learning_rate=0.08,
                            random_state=42, n_jobs=-1, eval_metric="logloss",
                            verbosity=0, use_label_encoder=False)
    cv_ensemble = VotingClassifier([("rf", cv_rf), ("xgb", cv_xgb)], voting="soft")
    cv_pipeline = Pipeline([("scaler", StandardScaler()), ("clf", cv_ensemble)])

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(cv_pipeline, X_all, y_all, cv=skf, scoring="accuracy", n_jobs=-1)
    print(f"\n  5-Fold CV Scores  : {[f'{s*100:.1f}%' for s in cv_scores]}")
    print(f"  CV Mean Accuracy  : {cv_scores.mean()*100:.2f}%  ± {cv_scores.std()*100:.2f}%")

    print(f"\n[5/5] Saving model -> {MODEL_SAVE_PATH}")
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    with open(MODEL_SAVE_PATH, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"[DONE] Model saved -> {MODEL_SAVE_PATH}")
    print(f"  Feature version : {FEATURE_VERSION}")
    print(f"  Features        : {X_train.shape[1]}")
    print(f"  Val Accuracy    : {val_acc * 100:.2f}%")
    print(f"  CV Accuracy     : {cv_scores.mean()*100:.2f}%")
    print("\n  IMPORTANT: Restart the ML server after training to load the new model!")


if __name__ == "__main__":
    main()
