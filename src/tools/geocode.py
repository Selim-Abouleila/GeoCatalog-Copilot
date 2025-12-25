from arcgis.geocoding import geocode
from src.services.arcgis_client import get_gis

def geocode_place(place_text):
    """
    Geocodes a place name to coordinates and bounding box.
    
    Args:
        place_text (str): The place name to geocode.
        
    Returns:
        dict: A dictionary containing lat, lon, bbox, and name. Returns None if no result found.
    """
    # Ensure GIS context is initialized, though geocode() often works anonymously by default on standard geocoders
    # We call get_gis() to ensure any env configuration is respected if needed for premium geocoders later
    _ = get_gis() 
    
    results = geocode(place_text, max_locations=1)
    
    if not results:
        return None
        
    location = results[0]
    return {
        "lat": location['location']['y'],
        "lon": location['location']['x'],
        "bbox": location['extent'], # {'xmin': ..., 'ymin': ..., 'xmax': ..., 'ymax': ...}
        "name": location['address']
    }
