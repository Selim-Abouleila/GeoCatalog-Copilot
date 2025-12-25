import os
from arcgis.gis import GIS
from dotenv import load_dotenv

load_dotenv()

def get_gis():
    """
    Returns an authenticated GIS object if credentials are provided in environment variables,
    otherwise returns an anonymous GIS object.
    """
    url = os.getenv("ARCGIS_URL", "https://www.arcgis.com")
    username = os.getenv("ARCGIS_USERNAME")
    password = os.getenv("ARCGIS_PASSWORD")

    if username and password:
        return GIS(url, username, password)
    else:
        return GIS()
