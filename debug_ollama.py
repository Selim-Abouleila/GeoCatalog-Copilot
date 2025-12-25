import requests

try:
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "qwen2.5:1.5b", "prompt": "hi", "stream": False},
        timeout=10
    )
    print(f"Status Code: {resp.status_code}")
    print(f"Response Text: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
