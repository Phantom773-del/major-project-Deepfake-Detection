import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def create_real_camera_image(filepath, seed):
    """
    Generates a simulated genuine camera photograph:
    - Natural lighting gradients
    - Physical camera sensor noise (PRNU)
    - Realistic RGB color distribution
    - Lens blur / optical depth
    """
    np.random.seed(seed)
    width, height = 300, 300
    
    # 1. Base gradient scene (nature / indoor light)
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    
    r = (np.sin(xx * 3.0 + seed) * 127 + 128).astype(np.uint8)
    g = (np.cos(yy * 2.5 + seed * 2) * 127 + 128).astype(np.uint8)
    b = (np.sin((xx + yy) * 2.0) * 127 + 128).astype(np.uint8)
    
    img_arr = np.stack([r, g, b], axis=2)
    
    # 2. Add Camera Sensor Noise (Gaussian & PRNU Profile)
    sensor_noise = np.random.normal(0, 8, img_arr.shape)
    img_arr = np.clip(img_arr + sensor_noise, 0, 255).astype(np.uint8)
    
    img = Image.fromarray(img_arr)
    img = img.filter(ImageFilter.SMOOTH_MORE)
    img.save(filepath, "JPEG", quality=92)

def create_ai_fake_image(filepath, seed):
    """
    Generates a simulated AI-generated / DeepFake image:
    - High-frequency synthetic grid/checkerboard noise (Diffusion artifact)
    - Over-smoothed latent textures without physical sensor noise
    - Unnatural color saturations
    """
    np.random.seed(seed + 1000)
    width, height = 300, 300
    
    # 1. Synthetic latent noise pattern
    x = np.linspace(-2, 2, width)
    y = np.linspace(-2, 2, height)
    xx, yy = np.meshgrid(x, y)
    
    # AI Lattice / Grid artifacts
    r = (np.sin(xx**2 + yy**2 + seed) * 127 + 128).astype(np.uint8)
    g = (np.sin(xx * 10.0) * np.cos(yy * 10.0) * 127 + 128).astype(np.uint8)
    b = (np.cos(xx * 15.0) * 127 + 128).astype(np.uint8)
    
    img_arr = np.stack([r, g, b], axis=2)
    
    # 2. AI Diffusion Latent Artifacts (Zero camera sensor noise, ultra-sharp synthetic edges)
    img = Image.fromarray(img_arr)
    img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
    img.save(filepath, "JPEG", quality=98)

def main():
    base_dir = "server/dataset"
    for split in ["train", "val"]:
        for cls in ["REAL", "FAKE"]:
            os.makedirs(os.path.join(base_dir, split, cls), exist_ok=True)
            
    print("Generating Dataset...")
    
    # Generate 100 Train Real, 100 Train Fake
    for i in range(100):
        create_real_camera_image(f"{base_dir}/train/REAL/real_{i:03d}.jpg", seed=i)
        create_ai_fake_image(f"{base_dir}/train/FAKE/fake_{i:03d}.jpg", seed=i)
        
    # Generate 30 Val Real, 30 Val Fake
    for i in range(30):
        create_real_camera_image(f"{base_dir}/val/REAL/real_{i:03d}.jpg", seed=i + 500)
        create_ai_fake_image(f"{base_dir}/val/FAKE/fake_{i:03d}.jpg", seed=i + 500)
        
    print("Dataset generation complete!")
    print(f"- Train REAL: 100 images")
    print(f"- Train FAKE: 100 images")
    print(f"- Val REAL: 30 images")
    print(f"- Val FAKE: 30 images")

if __name__ == "__main__":
    main()
