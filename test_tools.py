from src.tools.content_search import search_items
from src.tools.geocode import geocode_place
from src.tools.scoring import quality_score
from dotenv import load_dotenv

load_dotenv()

def run_tests():
    print("=== Testing Core Tools ===\n")

    # 1. Test Content Search
    print("1. Testing content_search...")
    try:
        results = search_items("wildfire", max_items=2)
        print(f"   Found {len(results)} items.")
        for item in results:
            print(f"   - {item['title']} (Score: {quality_score(item)})")
    except Exception as e:
        print(f"   FAILED: {e}")
    print()

    # 2. Test Geocoding
    print("2. Testing geocode_place...")
    try:
        place = geocode_place("New York, NY")
        if place:
            print(f"   Found: {place['name']}")
            print(f"   Coordinates: {place['lat']}, {place['lon']}")
        else:
            print("   No results found.")
    except Exception as e:
        print(f"   FAILED: {e}")
    print()

    print("=== Tests Complete ===")

if __name__ == "__main__":
    run_tests()
