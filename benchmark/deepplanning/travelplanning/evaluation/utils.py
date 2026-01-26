"""
Utility functions for travel planning evaluation.
Contains common helper functions for parsing, validation, and data loading.
"""

import re
import csv
import math
import os
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


# ----------------------
# String Parsing Utilities
# ----------------------

def extract_from_to(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract 'from' and 'to' cities from text like 'from CityA to CityB'."""
    if not isinstance(text, str):
        return None, None
    m = re.search(r"from\s+(.+?)\s+to\s+([^,]+)(?=[,\s]|$)", text)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, None)


def normalize_city(text: Optional[str]) -> Optional[str]:
    """Normalize city name by removing parentheses and content inside."""
    if text is None:
        return None
    return re.sub(r"[（(].*?[)）]", "", text).strip()


def parse_lonlat_string(text: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """Parse coordinate string in format 'latitude,longitude', returns (lat, lon)."""
    if not text or not isinstance(text, str):
        return None, None
    m = re.match(r"\s*([\-0-9\.]+)\s*,\s*([\-0-9\.]+)\s*$", text)
    if not m:
        return None, None
    try:
        # Database format is "latitude,longitude"
        lat = float(m.group(1))
        lon = float(m.group(2))
        return lat, lon
    except Exception:
        return None, None


# ----------------------
# Time Parsing Utilities
# ----------------------

def parse_time_hhmm(t: Optional[str]) -> Optional[time]:
    """
    Parse time string to time object.
    Special case: "24:00" is treated as end of day and mapped to 23:59.
    """
    if not t or not isinstance(t, str):
        return None
    t = t.strip()
    if t == "24:00":
        # Map 24:00 to 23:59 (end of day)
        return time(23, 59)
    try:
        dt = datetime.strptime(t, "%H:%M")
        return time(dt.hour, dt.minute)
    except Exception:
        return None


def parse_time_slot(slot: Optional[str]) -> Tuple[Optional[time], Optional[time]]:
    """Parse time slot string (e.g., '09:00-17:00') to time objects."""
    if not slot or not isinstance(slot, str):
        return None, None
    m = re.match(r"\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*", slot)
    if not m:
        return None, None
    start = parse_time_hhmm(m.group(1))
    end = parse_time_hhmm(m.group(2))
    return start, end


def is_within_business_hours(slot_start: time, slot_end: time, open_t: time, close_t: time) -> bool:
    """
    Check if activity time slot is within business hours.
    Handles midnight crossover (e.g., 16:30-03:00).
    """
    slot_crosses_midnight = slot_end < slot_start
    if open_t <= close_t:
        # Normal same-day interval: activity time must be fully within business hours
        if slot_crosses_midnight:
            # Activity crosses midnight but business hours don't: invalid
            return False
        return (slot_start >= open_t) and (slot_end <= close_t)
    # Crosses midnight: business hours are [open, 24:00) ∪ [00:00, close]
    if slot_crosses_midnight:
        # Both activity and business hours cross midnight: must start in night segment and end in morning segment
        return (slot_start >= open_t) and (slot_end <= close_t)
    # Activity doesn't cross midnight, but business hours do: can be in night segment or morning segment
    in_night = (slot_start >= open_t) and (slot_end >= open_t)
    in_morning = (slot_start <= close_t) and (slot_end <= close_t)
    return in_night or in_morning


def slot_to_minutes(slot: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Convert time slot to minutes since midnight."""
    start_t, end_t = parse_time_slot(slot)
    if not start_t or not end_t:
        return None, None
    start_m = start_t.hour * 60 + start_t.minute
    end_m = end_t.hour * 60 + end_t.minute
    if end_m < start_m:
        end_m += 24 * 60  # Handle midnight crossover
    return start_m, end_m


# ----------------------
# Geographic Utilities
# ----------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers using Haversine formula."""
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


# ----------------------
# Database Path Management
# ----------------------

def get_base_dir() -> Path:
    """Get TravelBench root directory."""
    
    # Method 0: Read from environment variable (for evaluation with specific sample database)
    env_db_path = os.environ.get('EVAL_DATABASE_PATH')
    if env_db_path:
        db_path = Path(env_db_path)
        if db_path.exists():
            # EVAL_DATABASE_PATH points to database/id_x/, need to return TravelBench root directory
            # Since we use _BASE_DIR / "database" / ... format later, need special handling
            # Example: /path/to/TravelBench/database/id_0 -> /path/to/TravelBench
            return db_path.parent.parent
    
    # Method 1: Parse from __file__ (most reliable)
    try:
        current_file = Path(__file__).resolve()
        base_dir = current_file.parent.parent  # evaluation -> TravelBench
        if (base_dir / "database").exists():
            return base_dir
    except (NameError, AttributeError):
        pass
    
    # Method 2: Search from current working directory
    cwd = Path.cwd()
    # Check current directory
    if (cwd / "database").exists():
        return cwd
    # Check parent directory
    if (cwd.parent / "database").exists():
        return cwd.parent
    # Check parent's parent directory (if running from evaluation directory)
    if (cwd.parent.parent / "database").exists():
        return cwd.parent.parent
    
    # Method 3: If not found, try from common locations
    # Default: return result parsed from __file__ (if available)
    try:
        return Path(__file__).resolve().parent.parent
    except (NameError, AttributeError):
        # Last fallback: return current directory
        return cwd


def get_database_dir(database_dir: Optional[Path] = None) -> Path:
    """
    Get database directory, supports reading specific sample database path from environment variable or parameter.
    
    Args:
        database_dir: Directly specified database directory path (highest priority)
    """
    
    # 1. Use directly passed parameter first
    if database_dir is not None:
        if isinstance(database_dir, str):
            database_dir = Path(database_dir)
        if database_dir.exists():
            return database_dir
    
    # 2. Read from environment variable (for evaluation with specific sample database)
    env_db_path = os.environ.get('EVAL_DATABASE_PATH')
    if env_db_path:
        db_path = Path(env_db_path)
        if db_path.exists():
            # EVAL_DATABASE_PATH already points to database/id_x/, return directly
            return db_path
    
    # 3. Default to _BASE_DIR / "database" / "id_0"
    return get_base_dir() / "database" / "id_0"


# ----------------------
# Data Loading Utilities
# ----------------------

def load_restaurant_index(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """Load restaurant index from CSV file."""
    index: Dict[str, Dict[str, Any]] = {}
    path_obj = Path(csv_path)
    if not path_obj.exists():
        # If file doesn't exist, return empty index; upper layer checks will provide failure reason
        return {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:  # Use utf-8-sig to handle BOM
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("restaurant_name") or "").strip()
                if not name:
                    continue
                index[name] = {
                    "price_per_person": row.get("price_per_person"),
                    "opening_time": row.get("opening_time"),
                    "closing_time": row.get("closing_time"),
                }
    except Exception as e:
        # If loading fails, return empty index; upper layer checks will provide failure reason
        return {}
    return index


def load_hotel_index(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """Load hotel index from CSV file."""
    index: Dict[str, Dict[str, Any]] = {}
    path_obj = Path(csv_path)
    if not path_obj.exists():
        return {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:  # Use utf-8-sig to handle BOM
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                index[name] = {
                    "price_per_night": row.get("price"),
                    "city": row.get("city"),
                }
    except Exception:
        return {}
    return index


def load_attraction_index(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """Load attraction index from CSV file."""
    index: Dict[str, Dict[str, Any]] = {}
    path_obj = Path(csv_path)
    if not path_obj.exists():
        return {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:  # Use utf-8-sig to handle BOM
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("attraction_name") or "").strip()
                if not name:
                    continue
                index[name] = {
                    "opening_time": row.get("opening_time"),
                    "closing_time": row.get("closing_time"),
                    "min_visit_hours": row.get("min_visit_hours"),
                    "max_visit_hours": row.get("max_visit_hours"),
                    "ticket_price": row.get("ticket_price"),
                    "latitude": row.get("latitude"),
                    "longitude": row.get("longitude"),
                    "closing_dates": row.get("closing_dates"),  # Add closing_dates field
                }
    except Exception:
        return {}
    return index


def load_locations_index(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load locations_coords.csv, which contains coordinate information for all POIs (attractions, restaurants, hotels, etc.).
    
    Note: Keep coordinates in original string format to match format in distance_matrix.csv.
    """
    index: Dict[str, Dict[str, Any]] = {}
    path_obj = Path(csv_path)
    if not path_obj.exists():
        return {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:  # Use utf-8-sig to handle BOM
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("poi_name") or "").strip()
                if not name:
                    continue
                # Keep original string format, don't convert to float
                index[name] = {
                    "latitude": (row.get("latitude") or "").strip(),
                    "longitude": (row.get("longitude") or "").strip(),
                    "poi_type": (row.get("poi_type") or "").strip(),
                }
    except Exception:
        return {}
    return index


def load_flights_index(csv_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load flights index from CSV file.
    
    Returns:
        Dictionary with flight_no as key, list of flight records as value.
        (A flight number may have multiple records for different dates/segments)
    """
    index: Dict[str, List[Dict[str, Any]]] = {}
    path_obj = Path(csv_path)
    if not path_obj.exists():
        return {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                flight_no = (row.get("flight_no") or "").strip()
                if not flight_no:
                    continue
                record = {
                    "origin_city": (row.get("origin_city") or "").strip(),
                    "destination_city": (row.get("destination_city") or "").strip(),
                    "dep_station_name": (row.get("dep_station_name") or "").strip(),
                    "arr_station_name": (row.get("arr_station_name") or "").strip(),
                    "dep_datetime": (row.get("dep_datetime") or "").strip(),
                    "arr_datetime": (row.get("arr_datetime") or "").strip(),
                    "price": row.get("price"),
                    "airline": (row.get("airline") or "").strip(),
                    "segment_index": row.get("segment_index"),
                    "route_index": row.get("route_index"),
                }
                if flight_no not in index:
                    index[flight_no] = []
                index[flight_no].append(record)
    except Exception:
        return {}
    return index


def load_trains_index(csv_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load trains index from CSV file.
    
    Returns:
        Dictionary with train_no as key, list of train records as value.
        (A train number may have multiple records for different dates/segments)
    """
    index: Dict[str, List[Dict[str, Any]]] = {}
    path_obj = Path(csv_path)
    if not path_obj.exists():
        return {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                train_no = (row.get("train_no") or "").strip()
                if not train_no:
                    continue
                record = {
                    "origin_city": (row.get("origin_city") or "").strip(),
                    "destination_city": (row.get("destination_city") or "").strip(),
                    "dep_station_name": (row.get("dep_station_name") or "").strip(),
                    "arr_station_name": (row.get("arr_station_name") or "").strip(),
                    "dep_datetime": (row.get("dep_datetime") or "").strip(),
                    "arr_datetime": (row.get("arr_datetime") or "").strip(),
                    "price": row.get("price"),
                    "train_type": (row.get("train_type") or "").strip(),
                    "segment_index": row.get("segment_index"),
                    "route_index": row.get("route_index"),
                }
                if train_no not in index:
                    index[train_no] = []
                index[train_no].append(record)
    except Exception:
        return {}
    return index


# ----------------------
# Station/Airport Mapping
# ----------------------

# Global cache: airport/station name to city mapping
_STATION_TO_CITY_MAP: Optional[Dict[str, str]] = None


def load_station_to_city_mapping(database_dir: Optional[Path] = None) -> Dict[str, str]:
    """
    Load airport/station to city mapping from flights.csv and trains.csv.
    
    Args:
        database_dir: Database directory path (if specified, will use that sample's database)
    
    Returns: Dictionary of {station_name: city_name}
    Example: {"Xiaoshan International Airport": "Hangzhou", "Hangzhou East Station": "Hangzhou"}
    """
    mapping: Dict[str, str] = {}
    
    # Determine database directory
    if database_dir is not None:
        db_dir = get_database_dir(database_dir)
    else:
        db_dir = get_database_dir()
    
    # Load airport mapping from flights.csv
    flights_path = db_dir / "flights" / "flights.csv"
    if flights_path.exists():
        try:
            with open(str(flights_path), "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Departure airport
                    dep_station = (row.get("dep_station_name") or "").strip()
                    origin_city = (row.get("origin_city") or "").strip()
                    if dep_station and origin_city:
                        mapping[dep_station] = normalize_city(origin_city)
                    
                    # Arrival airport
                    arr_station = (row.get("arr_station_name") or "").strip()
                    dest_city = (row.get("destination_city") or "").strip()
                    if arr_station and dest_city:
                        mapping[arr_station] = normalize_city(dest_city)
        except Exception:
            pass
    
    # Load station mapping from trains.csv
    trains_path = db_dir / "trains" / "trains.csv"
    if trains_path.exists():
        try:
            with open(str(trains_path), "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Departure station
                    dep_station = (row.get("dep_station_name") or "").strip()
                    origin_city = (row.get("origin_city") or "").strip()
                    if dep_station and origin_city:
                        mapping[dep_station] = normalize_city(origin_city)
                    
                    # Arrival station
                    arr_station = (row.get("arr_station_name") or "").strip()
                    dest_city = (row.get("destination_city") or "").strip()
                    if arr_station and dest_city:
                        mapping[arr_station] = normalize_city(dest_city)
        except Exception:
            pass
    
    return mapping


def get_station_to_city_map(database_dir: Optional[Path] = None) -> Dict[str, str]:
    """
    Get airport/station to city mapping.
    
    Args:
        database_dir: Database directory path (if specified, will use that sample's database)
    
    Note: In multi-threaded environments, global cache is not used; reloads on each call.
    """
    # If database_dir is specified, don't use cache (avoid multi-threading conflicts)
    if database_dir is not None:
        return load_station_to_city_mapping(database_dir)
    
    # Otherwise use global cache
    global _STATION_TO_CITY_MAP
    if _STATION_TO_CITY_MAP is None:
        _STATION_TO_CITY_MAP = load_station_to_city_mapping()
    return _STATION_TO_CITY_MAP


def extract_city_from_location(location: str, database_dir: Optional[Path] = None) -> Optional[str]:
    """
    Extract city name from airport/station name.
    
    Args:
        location: Airport/station name
        database_dir: Database directory path (if specified, will use that sample's database)
    
    Strategy:
    1. Look up directly in flights.csv and trains.csv mapping table
    2. Fallback: Extract first 2 Chinese characters
    
    Examples:
    - "Xiaoshan International Airport" -> "Hangzhou" (from flights.csv)
    - "Hangzhou East Station" -> "Hangzhou" (from trains.csv)
    - "Beijing Daxing International Airport" -> "Beijing"
    """
    if not location:
        return None
    
    # Strategy 1: Look up in mapping table (most accurate)
    station_map = get_station_to_city_map(database_dir)
    if location in station_map:
        return station_map[location]
    
    # Strategy 2: Fallback - directly extract first 2 Chinese characters
    # This works for most cities (Beijing, Shanghai, Hangzhou, Chengdu, etc.)
    match = re.match(r'^([\u4e00-\u9fa5]{2})', location)
    if match:
        return match.group(1)
    
    return None


# ----------------------
# Coordinate Resolution
# ----------------------

def get_location_coords(name: str, locations_index: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    """Get coordinates from locations_index (string format, preserving original precision)."""
    if not name or name not in locations_index:
        return None, None
    lat_str = locations_index[name].get("latitude")
    lon_str = locations_index[name].get("longitude")
    # Verify if valid numbers (but return string)
    if not lat_str or not lon_str:
        return None, None
    try:
        float(lat_str)  # Verify convertible to number
        float(lon_str)
        return lat_str, lon_str
    except Exception:
        return None, None


def resolve_name_coords(name: str, locations_index: Optional[Dict[str, Dict[str, Any]]] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve location name to coordinates (string format, preserving original precision).
    
    Returns (lat_str, lon_str) or (None, None)
    """
    # 1) Look up directly in locations_coords.csv (contains all POI types: attractions, restaurants, hotels, etc.)
    if locations_index is not None:
        lat_str, lon_str = get_location_coords(name, locations_index)
        if lat_str is not None and lon_str is not None:
            return lat_str, lon_str
    # 2) Parse as "latitude,longitude" string
    lat_float, lon_float = parse_lonlat_string(name)
    if lat_float is not None and lon_float is not None:
        # Convert back to string (maintain reasonable precision)
        return str(lat_float), str(lon_float)
    return None, None


# ----------------------
# Weekday Calculation
# ----------------------

# ----------------------
# Duration Parsing
# ----------------------

def parse_duration_hours(val: Any) -> Optional[float]:
    """Parse duration value to hours."""
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def is_all_day(opening: Optional[str], closing: Optional[str]) -> bool:
    """Check if opening hours are all day."""
    opening = (opening or "").strip()
    closing = (closing or "").strip()
    # Support both Chinese and English formats for 24-hour opening
    all_day_patterns = ["全天开放", "Open 24 Hours"]
    return opening in all_day_patterns and closing in all_day_patterns


# ----------------------
# Date and Day of Week Utilities
# ----------------------

def calculate_day_of_week(depart_weekday: int, day_index: int) -> int:
    """
    Calculate the day of week for a given day in the trip.
    
    Args:
        depart_weekday: Day of week for departure day (1=Monday, 7=Sunday)
        day_index: Day index in the trip (0-based, 0 = first day)
    
    Returns:
        Day of week (1=Monday, 7=Sunday)
    
    Example:
        If departure is Wednesday (3), and we want day_index=1 (second day):
        calculate_day_of_week(3, 1) = 4 (Thursday)
    """
    result = depart_weekday + day_index
    # Handle wraparound: if result > 7, wrap to 1-7
    while result > 7:
        result -= 7
    return result


def parse_closing_dates(closing_dates_str: Optional[str]) -> List[int]:
    """
    Parse closing_dates string to list of day-of-week integers.
    
    Based on actual data analysis:
    - Formats found: "Monday", "Tuesday", "周一", "周二", "周一,周日"
    - Delimiter: Only English comma (,)
    - Only full day names (no abbreviations)
    
    Returns:
        List of integers where 1=Monday, 7=Sunday
    
    Examples:
        "Monday" -> [1]
        "周一,周日" -> [1, 7]
        "" -> []
    """
    if not closing_dates_str or not isinstance(closing_dates_str, str):
        return []
    
    # Day name mappings (1=Monday, 7=Sunday)
    # Based on actual data: only full names, no abbreviations
    day_map = {
        # English (full names only)
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 7,
        # Chinese (周X format only, most common)
        "周一": 1,
        "周二": 2,
        "周三": 3,
        "周四": 4,
        "周五": 5,
        "周六": 6,
        "周日": 7,
    }
    
    closing_days = []
    # Split by comma (only delimiter found in actual data)
    parts = closing_dates_str.split(',')
    
    for part in parts:
        part_stripped = part.strip()
        # Try case-insensitive match for English
        part_lower = part_stripped.lower()
        
        if part_lower in day_map:
            closing_days.append(day_map[part_lower])
        elif part_stripped in day_map:  # Try exact match for Chinese
            closing_days.append(day_map[part_stripped])
    
    return sorted(list(set(closing_days)))  # Remove duplicates and sort


def is_attraction_closed_on_day(closing_dates: Optional[str], weekday: int) -> bool:
    """
    Check if an attraction is closed on a specific day of week.
    
    Args:
        closing_dates: Closing dates string from CSV (e.g., "Monday,Wednesday")
        weekday: Day of week to check (1=Monday, 7=Sunday)
    
    Returns:
        True if attraction is closed on that day, False otherwise
    """
    closed_days = parse_closing_dates(closing_dates)
    return weekday in closed_days


# ----------------------
# Activity Iteration Helpers
# ----------------------

def day_cities(current_city: str) -> List[str]:
    """Get list of cities for a given day."""
    a, b = extract_from_to(current_city)
    if a and b:
        return [normalize_city(a), normalize_city(b)]
    return [normalize_city(current_city)]


def iter_meal_acts(daily_plans: List[Dict[str, Any]]):
    """Iterate through all meal activities in daily plans."""
    results = []
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") != "meal":
                continue
            details = act.get("details") or {}
            name = (details.get("name") or "").strip()
            results.append((act, details, name))
    return results


def iter_hotel_acts(daily_plans: List[Dict[str, Any]]):
    """Iterate through all hotel activities in daily plans."""
    results = []
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") != "hotel":
                continue
            details = act.get("details") or {}
            name = (details.get("name") or "").strip()
            results.append((act, details, name))
    return results


def iter_attraction_acts(daily_plans: List[Dict[str, Any]]):
    """Iterate through all attraction activities in daily plans."""
    results = []
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") != "attraction":
                continue
            details = act.get("details") or {}
            name = (details.get("name") or "").strip()
            results.append((act, details, name))
    return results


def iter_intercity_public_acts(daily_plans: List[Dict[str, Any]]):
    """Iterate through all intercity public transport activities in daily plans."""
    results = []
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") != "travel_intercity_public":
                continue
            details = act.get("details") or {}
            results.append((act, details))
    return results


def end_city_of_day(current_city: str) -> Optional[str]:
    """Get the ending city of a day."""
    a, b = extract_from_to(current_city)
    if a and b:
        return normalize_city(b)
    return normalize_city(current_city)


def get_day_accommodation_city(day: Dict[str, Any], hotels_index: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[str]:
    """Get the accommodation city for a given day."""
    # Priority 1: Read city from hotel activity
    for act, details, _name in iter_hotel_acts([day]):
        city = (details.get("city") or "").strip()
        if city:
            return normalize_city(city)
    # Priority 2: Read from day.accommodation field, look up city by hotel name in hotels.csv
    accom = day.get("accommodation")
    if isinstance(accom, dict):
        hotel_name = (accom.get("name") or "").strip()
        if hotel_name and hotels_index and hotel_name in hotels_index:
            city_str = hotels_index[hotel_name].get("city")
            if city_str:
                return normalize_city(str(city_str).strip())
    return None


def iter_accommodation_entries(daily_plans: List[Dict[str, Any]]):
    """Iterate through all accommodation entries: hotel activities + day.accommodation."""
    for idx, day in enumerate(daily_plans):
        # Hotel activities (except last day, as it may have checkout activity)
        if idx < len(daily_plans) - 1:
            for act, details, name in iter_hotel_acts([day]):
                yield idx, {
                    "name": name,
                    "price": details.get("price") or details.get("cost"),
                    "city": (details.get("city") or "").strip(),
                    "source": "activity",
                }
        # day.accommodation field
        accom = day.get("accommodation")
        if isinstance(accom, dict):
            yield idx, {
                "name": (accom.get("name") or "").strip(),
                "price": accom.get("price") or accom.get("cost") or accom.get("price_per_night"),
                "city": (accom.get("city") or "").strip(),
                "source": "field",
            }


def get_intercity_arrival_time(day: Dict[str, Any]) -> Optional[float]:
    """Get the arrival time of intercity transportation for a given day (in hours)."""
    for act in day.get("activities", []) or []:
        if act.get("type") == "travel_intercity_public":
            # Priority: use end_time, if not available extract from time_slot
            end_time = act.get("end_time", "")
            if not end_time:
                time_slot = act.get("time_slot", "")
                if time_slot and "-" in time_slot:
                    end_time = time_slot.split("-")[1]
            
            if end_time:
                try:
                    hour, minute = map(int, end_time.split(":"))
                    return hour + minute / 60.0
                except:
                    pass
    return None


def get_intercity_departure_time(day: Dict[str, Any]) -> Optional[float]:
    """Get the departure time of intercity transportation for a given day (in hours)."""
    for act in day.get("activities", []) or []:
        if act.get("type") == "travel_intercity_public":
            # Priority: use start_time, if not available extract from time_slot
            start_time = act.get("start_time", "")
            if not start_time:
                time_slot = act.get("time_slot", "")
                if time_slot and "-" in time_slot:
                    start_time = time_slot.split("-")[0]
            
            if start_time:
                try:
                    hour, minute = map(int, start_time.split(":"))
                    return hour + minute / 60.0
                except:
                    pass
    return None

