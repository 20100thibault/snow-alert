"""
Snow Removal Checker Module
Checks Quebec City's API for snow removal operations.
"""

import requests
import math
from typing import Optional, Dict, Any, List, Tuple
from config import Config

# Headers to avoid rate limiting
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


def geocode_postal_code(postal_code: str) -> Optional[Dict[str, Any]]:
    """
    Convert a postal code to latitude/longitude coordinates.
    Uses ArcGIS World Geocoder (free, reliable).
    Returns dict with lat, lon, or None if geocoding fails.
    """
    # Normalize postal code
    normalized = postal_code.upper().replace(' ', '')
    formatted = f"{normalized[:3]} {normalized[3:]}"  # Format as "G1R 2K8"

    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    params = {
        "SingleLine": f"{formatted}, Quebec, Canada",
        "f": "json",
        "outFields": "*"
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        candidates = data.get('candidates', [])
        if candidates:
            best = candidates[0]
            return {
                "lat": best['location']['y'],
                "lon": best['location']['x'],
            }
        return None

    except Exception:
        return None


def reverse_geocode(lat: float, lon: float) -> str:
    """
    Get street name from coordinates using ArcGIS reverse geocoding.
    Returns street name or 'Unknown' if it fails.
    """
    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/reverseGeocode"
    params = {
        "location": f"{lon},{lat}",
        "f": "json",
        "outSR": "4326"
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()

        address = data.get('address', {})
        street = address.get('Address', '')
        if street:
            return street
        street = address.get('Match_addr', '')
        if street:
            return street.split(',')[0]
        return 'Unknown'

    except Exception:
        return 'Unknown'


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two coordinates using Haversine formula."""
    R = 6371000  # Earth radius in meters

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def check_snow_removal(lat: float, lon: float, buffer_meters: int = None) -> Dict[str, Any]:
    """
    Check snow removal status for a location using Quebec City's ArcGIS API.
    Returns dict with status information.
    """
    if buffer_meters is None:
        buffer_meters = Config.SEARCH_RADIUS_METERS

    base_url = "https://carte.ville.quebec.qc.ca/arcgis/rest/services/CI/Deneigement/MapServer/2/query"

    # Try with initial buffer, expand if nothing found
    search_radius = buffer_meters
    max_radius = 500

    while search_radius <= max_radius:
        params = {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "distance": search_radius,
            "units": "esriSRUnit_Meter",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json"
        }

        try:
            response = requests.get(base_url, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                return {
                    "success": False,
                    "error": data['error'].get('message', 'Unknown API error')
                }

            features = data.get('features', [])

            if not features:
                if search_radius < max_radius:
                    search_radius += 100
                    continue
                return {
                    "success": True,
                    "found": False,
                    "search_radius": search_radius,
                    "message": f"No flashing lights found within {search_radius}m."
                }

            # Analyze the flashing lights found
            results = []
            has_active_operation = False

            for feature in features:
                attrs = feature.get('attributes', {})
                geom = feature.get('geometry', {})

                status = attrs.get('STATUT', 'Unknown')
                station = attrs.get('STATION_NO', 'Unknown')

                # Get station coordinates
                station_lon = geom.get('x')
                station_lat = geom.get('y')

                # Calculate distance from search location
                distance = None
                if station_lat and station_lon:
                    distance = calculate_distance(lat, lon, station_lat, station_lon)

                # Reverse geocode to get street name
                street = 'Unknown'
                if station_lat and station_lon:
                    street = reverse_geocode(station_lat, station_lon)

                if status == "En fonction":
                    has_active_operation = True

                results.append({
                    "station": station,
                    "status": status,
                    "street": street,
                    "distance": distance
                })

            # Sort by distance
            results.sort(key=lambda x: x.get('distance') or 9999)

            return {
                "success": True,
                "found": True,
                "search_radius": search_radius,
                "has_active_operation": has_active_operation,
                "lights": results
            }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Network error: {e}"
            }
        except ValueError as e:
            return {
                "success": False,
                "error": f"Error parsing response: {e}"
            }

    return {
        "success": True,
        "found": False,
        "search_radius": max_radius,
        "message": f"No flashing lights found within {max_radius}m."
    }


def check_postal_code(postal_code: str) -> Tuple[bool, List[str]]:
    """
    Main function to check if there's a snow removal operation for a postal code.

    Returns:
        Tuple of (has_operation: bool, streets_affected: list of street names)
    """
    # Geocode the postal code
    location = geocode_postal_code(postal_code)
    if not location:
        return (False, [])

    # Check snow removal status
    result = check_snow_removal(location['lat'], location['lon'])

    if not result.get('success') or not result.get('found'):
        return (False, [])

    has_operation = result.get('has_active_operation', False)

    # Get list of affected streets (only those with active operations)
    streets = []
    if has_operation:
        for light in result.get('lights', []):
            if light.get('status') == 'En fonction':
                streets.append(light.get('street', 'Unknown'))

    return (has_operation, streets)
