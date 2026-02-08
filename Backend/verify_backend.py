import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_backend():
    print("Fetching authors...")
    try:
        resp = requests.get(f"{BASE_URL}/authors")
        resp.raise_for_status()
        authors = resp.json().get("authors", [])
        print(f"Authors found: {authors}")
        if not authors:
            print("No authors found! Cannot test continuation.")
            return
        
        test_author = authors[0]
        print(f"Using author: {test_author}")
    except Exception as e:
        print(f"Error fetching authors: {e}")
        return

    test_text = "The morning sun rose over the mountains, casting a golden glow."

    # Test Continue
    print("\n[TEST] Testing /continue endpoint...")
    try:
        payload = {"text": test_text, "author": test_author}
        start = time.time()
        resp = requests.post(f"{BASE_URL}/continue", json=payload)
        resp.raise_for_status()
        data = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Continuation: {data.get('continuation')[:100]}...")
        print(f"Time taken: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"Error testing /continue: {e}")
        if hasattr(e, 'response') and e.response:
             print(e.response.text)

    # Test Analysis
    print("\n[TEST] Testing /analyze endpoint...")
    try:
        payload = {"text": test_text}
        start = time.time()
        resp = requests.post(f"{BASE_URL}/analyze", json=payload)
        resp.raise_for_status()
        data = resp.json()
        print(f"Status: {resp.status_code}")
        print("Analysis Keys:", data.keys())
        if "qualitative_analysis" in data:
            print(f"Qualitative Analysis: {data['qualitative_analysis'][:100]}...")
        if "local_metrics" in data:
            print("Local Metrics:", data["local_metrics"])
        if "stylometric_profile" in data:
            print(f"Closest Match: {data['stylometric_profile'].get('closest_match')}")
        print(f"Time taken: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"Error testing /analyze: {e}")
        if hasattr(e, 'response') and e.response:
             print(e.response.text)

if __name__ == "__main__":
    test_backend()
