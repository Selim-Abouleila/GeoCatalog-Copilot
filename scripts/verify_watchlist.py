
import sys
import os
import uuid
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.storage.duckdb_client import ensure_db_initialized, upsert_watchlist_item, remove_watchlist_item, list_watchlist_items

def verify_watchlist():
    print("Initializing DB...")
    ensure_db_initialized()
    
    test_id = f"test_{uuid.uuid4().hex}"
    test_item = {
        'id': test_id,
        'url': f'https://example.com/{test_id}',
        'title': 'Test Item Watchlist',
        'type': 'Feature Layer',
        'owner': 'tester'
    }
    
    print(f"Upserting item {test_id}...")
    upsert_watchlist_item(test_item)
    
    print("Listing items...")
    items = list_watchlist_items()
    found = next((i for i in items if i['id'] == test_id), None)
    
    if not found:
        print("❌ Item not found in watchlist!")
        sys.exit(1)
        
    print(f"✅ Found item: {found['title']}")
    
    print("Removing item...")
    remove_watchlist_item(test_id)
    
    items_after = list_watchlist_items()
    found_after = next((i for i in items_after if i['id'] == test_id), None)
    
    if found_after:
        print("❌ Item still present after removal!")
        sys.exit(1)
        
    print("✅ Item removed successfully.")
    
if __name__ == "__main__":
    try:
        verify_watchlist()
        print("✅ Watchlist verification passed.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)
