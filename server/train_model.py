import os
import glob
import pickle
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

def extract_forensic_features(filepath):
    """
    Extracts forensic features from an image:
    1. RGB Color Histogram (Color distributions)
    2. Spatial Laplacian Variance (Noise & Blur profile)
    3. 2D Fast Fourier Transform (FFT) High-Frequency Energy Ratio (AI Lattice Artifacts)
    """
    img = Image.open(filepath).convert("RGB")
    arr = np.array(img, dtype=np.float32)
    
    # Feature 1: RGB Channel Mean & Std Dev
    r_mean, g_mean, b_mean = arr[:, :, 0].mean(), arr[:, :, 1].mean(), arr[:, :, 2].mean()
    r_std, g_std, b_std = arr[:, :, 0].std(), arr[:, :, 1].std(), arr[:, :, 2].std()
    
    # Feature 2: High Pass Filter Noise / Laplacian Variance (Camera PRNU vs AI Smoothness)
    gray = 0.2989 * arr[:, :, 0] + 0.5870 * arr[:, :, 1] + 0.1140 * arr[:, :, 2]
    laplacian = np.abs(gray[1:-1, 1:-1] * 4 - gray[0:-2, 1:-1] - gray[2:, 1:-1] - gray[1:-1, 0:-2] - gray[1:-1, 2:])
    noise_variance = float(laplacian.var())
    noise_mean = float(laplacian.mean())
    
    # Feature 3: 2D FFT Frequency Artifact Energy Ratio (Synthetic Grid Signals)
    fft = np.fft.fft2(gray)
    fft_shift = np.fft.fftshift(fft)
    magnitude_spectrum = np.abs(fft_shift)
    h, w = gray.shape
    center_h, center_w = h // 2, w // 2
    
    # Energy in outer (high) frequencies vs inner (low) frequencies
    high_freq_energy = float(np.sum(magnitude_spectrum) - np.sum(magnitude_spectrum[center_h-20:center_h+20, center_w-20:center_w+20]))
    total_energy = float(np.sum(magnitude_spectrum)) + 1e-6
    fft_ratio = high_freq_energy / total_energy
    
    return [r_mean, g_mean, b_mean, r_std, g_std, b_std, noise_variance, noise_mean, fft_ratio]

def load_dataset(split):
    X, y = [], []
    # 0 = REAL, 1 = FAKE
    classes = {"REAL": 0, "FAKE": 1}
    
    for cls_name, label in classes.items():
        pattern = f"server/dataset/{split}/{cls_name}/*.jpg"
        files = glob.glob(pattern)
        print(f"Loading {split} {cls_name}: {len(files)} files...")
        for f in files:
            feats = extract_forensic_features(f)
            X.append(feats)
            y.append(label)
            
    return np.array(X), np.array(y)

def main():
    print("=== STARTING ML FORENSIC MODEL TRAINING ===")
    
    X_train, y_train = load_dataset("train")
    X_val, y_val = load_dataset("val")
    
    print("\nTraining Random Forest Classifier on Forensic Feature Space...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # Training Accuracy
    train_preds = clf.predict(X_train)
    train_acc = accuracy_score(y_train, train_preds)
    
    # Validation Accuracy
    val_preds = clf.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    
    print("\n=== TRAINING RESULTS ===")
    print(f"Training Accuracy   : {train_acc * 100:.2f}%")
    print(f"Validation Accuracy : {val_acc * 100:.2f}%")
    print("\nClassification Report (Validation Dataset):")
    print(classification_report(y_val, val_preds, target_names=["REAL", "FAKE"]))
    
    # Save Model
    model_path = "server/forensic_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)
        
    print(f"Trained model saved successfully to: {model_path}")

if __name__ == "__main__":
    main()
