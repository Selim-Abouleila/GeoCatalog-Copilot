from src.services.arcgis_client import get_gis

def search_items(query, item_type="Feature Layer", max_items=5):
    """
    Searches for items in ArcGIS Online.
    
    Args:
        query (str): The search query string.
        item_type (str): The type of item to search for (default: "Feature Layer").
        max_items (int): The maximum number of items to return (default: 5).
        
    Returns:
        list: A list of dictionaries containing item details.
    """
    gis = get_gis()
    items = gis.content.search(query, item_type=item_type, max_items=max_items)
    
    results = []
    for item in items:
        # Handle potential missing attributes gracefully
        results.append({
            "title": item.title,
            "id": item.id,
            "type": item.type,
            "owner": item.owner,
            "modified": item.modified, # Unix timestamp usually
            "tags": item.tags,
            "url": item.url,
            "snippet": item.snippet, # Added for scoring
            "description": item.description # Added for scoring
        })
    
    return results
