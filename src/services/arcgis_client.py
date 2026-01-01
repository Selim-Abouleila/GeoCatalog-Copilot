import os
from arcgis.gis import GIS
from dotenv import load_dotenv

load_dotenv()

def get_gis():
    """
    Returns a GIS object.
    
    Order of precedence:
    1. ARCGIS_TOKEN (if present)
    2. ARCGIS_USERNAME + ARCGIS_PASSWORD (if present)
    3. Anonymous (default)
    
    Also respects ARCGIS_URL (default: https://www.arcgis.com)
    and ARCGIS_VERIFY_SSL (default: True)
    """
    url = os.getenv("ARCGIS_URL", "https://www.arcgis.com")
    username = os.getenv("ARCGIS_USERNAME")
    password = os.getenv("ARCGIS_PASSWORD")
    token = os.getenv("ARCGIS_TOKEN")
    verify_cert = os.getenv("ARCGIS_VERIFY_SSL", "true").lower() == "true"
    
    try:
        if token:
            # Token authentication
            # Note: For many portals/AGOL, passing token directly requires GIS(url=..., token=...)
            # or sometimes verify_cert manipulation if it's self-signed.
            return GIS(url=url, token=token, verify_cert=verify_cert)
        elif username and password:
            # User/Pass authentication
            return GIS(url, username, password, verify_cert=verify_cert)
        else:
            # Anonymous authentication
            return GIS(url, verify_cert=verify_cert)
    except Exception as e:
        # Fallback handling or re-raise with clear context
        raise RuntimeError(f"Failed to connect to ArcGIS at {url}: {e}")
