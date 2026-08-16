import requests
import json

url = "http://127.0.0.1:8000/api/v1/analyze"

def test_image(image_path, label):
    print(f"\n==========================================")
    print(f" TESTING IMAGE: {image_path} (Expected: {label})")
    print(f"==========================================")
    
    with open(image_path, "rb") as f:
        files = {"file": (image_path.split("/")[-1], f, "image/jpeg")}
        response = requests.post(url, files=files)
        
    if response.status_code == 200:
        res = response.json()
        report = res["report"]
        print(f"HTTP Status      : 200 OK")
        print(f"File Name        : {report['fileName']}")
        print(f"VERDICT          : {report['verdict']}")
        print(f"Risk Level       : {report['riskLevel']}")
        print(f"Authenticity     : {report['authenticityScore']}%")
        print(f"Manipulation Prob: {report['manipulationProbability']}%")
        print(f"Confidence Score : {report['confidenceScore']}%")
        print(f"Recommendations  : {report['recommendations'][0]}")
    else:
        print(f"Failed with status code: {response.status_code}, body: {response.text}")

if __name__ == "__main__":
    test_image("server/dataset/val/REAL/real_001.jpg", "AUTHENTIC / REAL")
    test_image("server/dataset/val/FAKE/fake_001.jpg", "AI_GENERATED / FAKE")
