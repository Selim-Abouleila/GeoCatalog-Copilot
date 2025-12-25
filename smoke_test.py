# smoke_test.py
from arcgis.gis import GIS
import requests
import os
from dotenv import load_dotenv

load_dotenv()

print("1) Testing ArcGIS Online (anonymous) search...")
gis = GIS()  # anonymous ArcGIS Online
items = gis.content.search("wildfire", item_type="Feature Layer", max_items=5)
for i, it in enumerate(items, 1):
    print(f"{i}. {it.title}")

print("\n2) Testing Ollama local API...")
resp = requests.post(
    os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate",
    json={"model": os.getenv("OLLAMA_MODEL", "llama3.2:1b"), "prompt": "Say hello in one short sentence.", "stream": False},
    timeout=60,
)
resp.raise_for_status()
print(resp.json()["response"])
