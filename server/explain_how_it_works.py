import os
import pickle
import numpy as np
from PIL import Image

def explain_pipeline(filepath, label):
    print("\n" + "="*75)
    print(f" STEP 1: INGESTING IMAGE: {filepath} ({label})")
    print("="*75)
    
    # 1. Read Image
    img = Image.open(filepath).convert("RGB")
    width, height = img.size
    print(f" Image Dimensions        : {width} x {height} px")
    print(f" Color Channels          : RGB (8-bit per channel)")
    
    # 2. Extract Mathematical Features (35 Forensic Descriptors)
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_server import extract_forensic_features, classifier

    features = extract_forensic_features(img)
    
    print("\n STEP 2: EXTRACTING FORENSIC FEATURE VECTOR (35 Features)")
    print(f" - Laplacian Noise Variance (PRNU Sensor Check) : {features[6]:.4f}")
    print(f" - Laplacian Noise Mean Value                     : {features[7]:.4f}")
    print(f" - 2D FFT High-Frequency Energy Ratio             : {features[8]:.4f}")
    print(f" - Gradient Magnitude Mean & Std                  : ({features[9]:.4f}, {features[10]:.4f})")
    print(f" - RGB Channel Mean Values (R, G, B)              : ({features[0]:.1f}, {features[1]:.1f}, {features[2]:.1f})")
    print(f" - Pixel Entropy (Texture Complexity)             : {features[14]:.4f}")
    print(f" - Inter-Channel Correlation (RG, RB, GB)         : ({features[18]:.3f}, {features[19]:.3f}, {features[20]:.3f})")
    print(f" - Block Variance Inconsistency (8x8)             : ({features[21]:.3f}, {features[22]:.3f}, {features[23]:.3f})")
    print(f" - DCT High-Frequency Energy                      : ({features[24]:.4f}, {features[25]:.4f}, {features[26]:.4f})")
    print(f" - Noise Residual Mean & Std                      : ({features[30]:.4f}, {features[31]:.4f})")
    print(f" - HSV Saturation Mean & Hue Std                  : ({features[32]:.4f}, {features[34]:.4f})")
    
    # 3. Model Inference
    probs = classifier.predict_proba([features])[0]
    
    real_prob = probs[0] * 100
    fake_prob = probs[1] * 100
    is_ai = fake_prob >= 50.0
    
    print("\n STEP 3: MACHINE LEARNING MODEL EVALUATION")
    print(f" - Model Pipeline                                 : StandardScaler + Ensemble Voting Classifier")
    print(f" - Authentic Probability                          : {real_prob:.1f}%")
    print(f" - AI Manipulation Probability                     : {fake_prob:.1f}%")
    print(f" - FINAL CLASSIFICATION VERDICT                   : {'AI_GENERATED (FAKE)' if is_ai else 'AUTHENTIC (REAL)'}")
    print(f" - RISK ASSESSMENT LEVEL                          : {'CRITICAL RISK' if is_ai else 'LOW RISK'}")

def main():
    print("==========================================================================")
    print("        PHANTOM PHOENIX: HOW THE DETECTION ENGINE WORKS UNDER THE HOOD   ")
    print("==========================================================================")
    
    explain_pipeline("server/dataset/val/REAL/real_001.jpg", "GENUINE CAMERA PHOTO")
    explain_pipeline("server/dataset/val/FAKE/fake_001.jpg", "AI GENERATED DEEPFAKE PHOTO")

if __name__ == "__main__":
    main()
