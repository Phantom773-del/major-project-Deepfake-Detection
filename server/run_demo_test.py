import requests
import json
import os

API_URL = "http://127.0.0.1:8000/api/v1/analyze"

def run_test(filepath, expected_type):
    print("\n" + "="*60)
    print(f" TESTING FILE: {filepath}")
    print(f" EXPECTED CLASS: {expected_type}")
    print("="*60)
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found!")
        return

    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "image/jpeg")}
        response = requests.post(API_URL, files=files)
        
    if response.status_code == 200:
        data = response.json()
        report = data["report"]
        
        print(f" Status Code             : 200 OK")
        print(f" Report ID               : {report['id']}")
        print(f" File Name               : {report['fileName']}")
        print(f" Final Verdict           : {report['verdict']}")
        print(f" Risk Assessment         : {report['riskLevel']}")
        print(f" Authenticity Score      : {report['authenticityScore']}%")
        print(f" Manipulation Score      : {report['manipulationProbability']}%")
        print(f" AI Confidence Score     : {report['confidenceScore']}%")
        print(f" Frequency Anomalies     : {report['frequencyAnalysis']['anomaliesDetected']} ({report['frequencyAnalysis']['dominantFrequency']})")
        print(f" Recommendation          : {report['recommendations'][0]}")
    else:
        print(f" Request Failed! Status Code: {response.status_code}")

def main():
    print("==================================================================")
    print("        PHANTOM PHOENIX ML FORENSIC ENGINE LIVE EXECUTION TEST    ")
    print("==================================================================")
    
    # Test Real Camera Images
    run_test("server/dataset/val/REAL/real_001.jpg", "REAL (AUTHENTIC)")
    run_test("server/dataset/val/REAL/real_015.jpg", "REAL (AUTHENTIC)")
    
    # Test AI Generated / DeepFake Images
    run_test("server/dataset/val/FAKE/fake_001.jpg", "FAKE (AI_GENERATED)")
    run_test("server/dataset/val/FAKE/fake_025.jpg", "FAKE (AI_GENERATED)")

if __name__ == "__main__":
    main()
