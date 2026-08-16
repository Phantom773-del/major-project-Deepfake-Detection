import requests
import json

url = "http://127.0.0.1:8000/api/v1/analyze"

def display_full_output(filepath):
    print("\n" + "="*80)
    print(f" INPUT FILE: {filepath}")
    print("="*80)
    
    with open(filepath, "rb") as f:
        files = {"file": (filepath.split("/")[-1], f, "image/jpeg")}
        res = requests.post(url, files=files)
        
    if res.status_code == 200:
        json_output = res.json()
        print("\n--- RAW JSON API RESPONSE FROM FASTAPI BACKEND ---")
        print(json.dumps(json_output, indent=2))
    else:
        print(f"Error {res.status_code}: {res.text}")

print("################################################################################")
print("               PHANTOM PHOENIX BACKEND FORENSIC API RAW OUTPUT                  ")
print("################################################################################")

# 1. Output for REAL photo
display_full_output("server/dataset/val/REAL/real_001.jpg")

# 2. Output for AI GENERATED / FAKE photo
display_full_output("server/dataset/val/FAKE/fake_001.jpg")
