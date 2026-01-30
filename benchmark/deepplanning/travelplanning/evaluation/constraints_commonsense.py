"""
Commonsense constraints evaluation for travel plans.
Contains all validation checks for travel plan feasibility and correctness.

Evaluation is organized into 8 dimensions with weighted scoring:
- Route Consistency (12.5%): valid_trip_duration, closed_loop_route_structure, seamless_intercity_transfers
- Sandbox Compliance (12.5%): validated_accommodation, validated_attractions, validated_meals, validated_transportation
- Itinerary Structure (12.5%): traceable_accommodation, ends_with_accommodation, essential_meal_coverage, essential_attraction_coverage
- Time Feasibility (12.5%): no_time_overlaps, reasonable_transfer_time
- Business Hours (12.5%): attraction_visit_within_opening_hours, dining_within_service_hours, avoidance_of_closure_days
- Duration Rationality (12.5%): reasonable_duration_at_attractions, reasonable_meal_duration
- Cost Calculation Accuracy (12.5%): cost_calculation_correctness
- Activity Diversity (12.5%): diverse_meal_options, diverse_attraction_options
"""

import re
import csv
import math
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


# ----------------------
# Evaluation Dimensions Configuration
# ----------------------

EVALUATION_DIMENSIONS = {
    "Route Consistency": {
        "weight": 0.125,  # 1/8
        "checks": [
            "valid_trip_duration",
            "closed_loop_route_structure",
            "seamless_intercity_transfers"
        ]
    },
    "Sandbox Compliance": {
        "weight": 0.125,  # 1/8
        "checks": [
            "validated_accommodation",
            "validated_attractions",
            "validated_meals",
            "validated_transportation"
        ]
    },
    "Itinerary Structure": {
        "weight": 0.125,  # 1/8
        "checks": [
            "traceable_accommodation",
            "ends_with_accommodation",
            "essential_meal_coverage",
            "essential_attraction_coverage"
        ]
    },
    "Time Feasibility": {
        "weight": 0.125,  # 1/8
        "checks": [
            "no_time_overlaps",
            "reasonable_transfer_time"
        ]
    },
    "Business Hours": {
        "weight": 0.125,  # 1/8
        "checks": [
            "attraction_visit_within_opening_hours",
            "dining_within_service_hours",
            "avoidance_of_closure_days"
        ]
    },
    "Duration Rationality": {
        "weight": 0.125,  # 1/8
        "checks": [
            "reasonable_duration_at_attractions",
            "reasonable_meal_duration"
        ]
    },
    "Cost Calculation Accuracy": {
        "weight": 0.125,  # 1/8
        "checks": [
            "cost_calculation_correctness"
        ]
    },
    "Activity Diversity": {
        "weight": 0.125,  # 1/8
        "checks": [
            "diverse_meal_options",
            "diverse_attraction_options"
        ]
    }
}

from .utils import (
    # String parsing
    extract_from_to,
    normalize_city,
    # Time parsing
    parse_time_hhmm,
    parse_time_slot,
    is_within_business_hours,
    slot_to_minutes,
    parse_duration_hours,
    is_all_day,
    # Date and weekday utilities
    calculate_day_of_week,
    is_attraction_closed_on_day,
    # Path utilities
    get_base_dir,
    get_database_dir,
    # Data loading
    load_restaurant_index,
    load_hotel_index,
    load_attraction_index,
    load_locations_index,
    load_flights_index,
    load_trains_index,
    # Location utilities
    extract_city_from_location,
    resolve_name_coords,
    # Activity iteration helpers
    day_cities,
    iter_meal_acts,
    iter_hotel_acts,
    iter_attraction_acts,
    iter_intercity_public_acts,
    end_city_of_day,
    get_day_accommodation_city,
    iter_accommodation_entries,
    get_intercity_arrival_time,
    get_intercity_departure_time,
)


# ----------------------
# Database Path Setup
# ----------------------

_BASE_DIR = get_base_dir()
_DATABASE_DIR = get_database_dir()

RESTAURANTS_CSV_PATH = str(_DATABASE_DIR / "restaurants" / "restaurants.csv")
HOTELS_CSV_PATH = str(_DATABASE_DIR / "hotels" / "hotels.csv")
ATTRACTIONS_CSV_PATH = str(_DATABASE_DIR / "attractions" / "attractions.csv")
LOCATIONS_COORDS_CSV_PATH = str(_DATABASE_DIR / "locations" / "locations_coords.csv")

# Note: Path validation removed - actual database paths are passed during evaluation


# ==============================================================================
# DIMENSION 1: Route Consistency (12.5%)
# Checks: valid_trip_duration, closed_loop_route_structure, seamless_intercity_transfers
# ==============================================================================

def check_valid_days(daily_plans: List[Dict[str, Any]], meta: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check if the number of days matches expected."""
    expected_days = int(meta.get("days") or 0)
    is_days_valid = len(daily_plans) == expected_days and expected_days > 0
    return is_days_valid, None if is_days_valid else f"Plan has {len(daily_plans)} days, expected {expected_days}"


def check_route_closed_loop(daily_plans: List[Dict[str, Any]], meta: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check if first day starts from org and last day returns to org (for intercity days)."""
    org = normalize_city(meta.get("org"))
    start_from, start_to = extract_from_to(daily_plans[0].get("current_city", "")) if daily_plans else (None, None)
    end_from, end_to = extract_from_to(daily_plans[-1].get("current_city", "")) if daily_plans else (None, None)

    is_closed_loop = True
    reason = None
    if start_from and normalize_city(start_from) != org:
        is_closed_loop = False
        reason = f"First day departure should be from {org}"
    if is_closed_loop and end_to and normalize_city(end_to) != org:
        is_closed_loop = False
        reason = f"Last day destination should return to {org}"
    return is_closed_loop, reason


def check_intercity_transportation_consistency(daily_plans: List[Dict[str, Any]], meta: Dict[str, Any], database_dir: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
    """
    Track location changes by time order, check intercity transportation completeness.
    
    Logic:
    1. Initial location = org
    2. Iterate through each day:
       - If current_city = "from A to B":
         * Check if A equals current location
         * Check if there's corresponding travel_intercity_public activity
         * Update current location = B
       - If current_city = "some city":
         * Check if this city equals current location
         * If not equal, indicates missing intercity transportation info
    """
    violations: List[str] = []
    
    # Initial location
    current_location = normalize_city(meta.get("org"))
    if not current_location:
        return False, "Missing org info, cannot track location"
    
    for day_idx, day in enumerate(daily_plans, start=1):
        current_city = day.get("current_city", "")
        from_city, to_city = extract_from_to(current_city)
        
        if from_city and to_city:
            # Case 1: current_city = "from A to B"
            from_city_norm = normalize_city(from_city)
            to_city_norm = normalize_city(to_city)
            
            # Check if from equals current location
            if from_city_norm != current_location:
                violations.append(
                    f"D{day_idx}: current_city shows 'from {from_city} to {to_city}', "
                    f"but from city ({from_city}) does not match current location ({current_location})"
                )
            
            # Check if there's corresponding intercity transportation activity
            intercity_acts = []
            for act in day.get("activities", []) or []:
                if act.get("type") == "travel_intercity_public":
                    intercity_acts.append(act)
            
            if not intercity_acts:
                violations.append(
                    f"D{day_idx}: current_city shows '{from_city}→{to_city}' but missing travel_intercity_public activity"
                )
            else:
                # Check if intercity transportation route matches
                matched = False
                for act in intercity_acts:
                    details = act.get("details") or {}
                    act_from = (details.get("from") or "").strip()
                    act_to = (details.get("to") or "").strip()
                    
                    if not act_from or not act_to:
                        continue
                    
                    # Extract city name from airport/station
                    act_from_city = extract_city_from_location(act_from, database_dir)
                    act_to_city = extract_city_from_location(act_to, database_dir)
                    
                    # Check if matches
                    if (act_from_city and act_to_city and
                        normalize_city(act_from_city) == from_city_norm and
                        normalize_city(act_to_city) == to_city_norm):
                        matched = True
                        break
                
                if not matched:
                    # List all intercity transportation routes
                    routes = []
                    for act in intercity_acts:
                        details = act.get("details") or {}
                        act_from = details.get("from", "")
                        act_to = details.get("to", "")
                        routes.append(f"{act_from}→{act_to}")
                    
                    violations.append(
                        f"D{day_idx}: current_city is '{from_city}→{to_city}' but intercity transportation route does not match (actual: {routes})"
                    )
            
            # Update current location
            current_location = to_city_norm
            
        else:
            # Case 2: current_city = "some city" (single city)
            city_norm = normalize_city(current_city)
            
            if not city_norm:
                violations.append(f"D{day_idx}: current_city is empty or invalid")
                continue
            
            # Check if this city equals current location
            if city_norm != current_location:
                violations.append(
                    f"D{day_idx}: current_city is '{current_city}' but current location should be '{current_location}', "
                    f"missing intercity transportation info (should be written as 'from {current_location} to {current_city}')"
                )
                # Note: Don't update current_location here, as this is an error state
    
    if violations:
        return False, f"Location tracking inconsistent: {violations}"
    return True, None


# ==============================================================================
# DIMENSION 2: Sandbox Compliance (12.5%)
# Checks: validated_accommodation, validated_attractions, validated_meals, validated_transportation
# ==============================================================================

def check_hotels_from_search(daily_plans: List[Dict[str, Any]], hotels_index: Dict[str, Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if all hotels are from search results and prices match."""
    if not hotels_index:
        return False, "Hotel database failed to load or is empty"
    not_found: List[str] = []
    price_mismatch: List[str] = []
    
    # 1. Check accommodation field: check name and price
    for idx, day in enumerate(daily_plans):
        accom = day.get("accommodation")
        if isinstance(accom, dict):
            name = (accom.get("name") or "").strip()
            # Last day's name if "-" then skip
            if idx == len(daily_plans) - 1 and name == "-":
                continue
            if not name:
                continue
            # Check if name is in database
            if name not in hotels_index:
                not_found.append(name)
                continue
            # Check price
            price_val = accom.get("price") or accom.get("cost") or accom.get("price_per_night")
            price_str = hotels_index[name].get("price_per_night")
            if price_str:
                try:
                    price_num = float(str(price_str))
                    price_rounded = int(round(price_num))
                    if isinstance(price_val, (int, float)):
                        if int(round(float(price_val))) != price_rounded:
                            price_mismatch.append(f"{name}: plan has {price_val} ≠ database {price_rounded}")
                    else:
                        price_mismatch.append(f"{name}: plan missing valid price/cost")
                except Exception:
                    pass
    
    # 2. Check hotel activities: only check name (not price)
    for idx, day in enumerate(daily_plans[:-1]):  # Except last day
        for act, details, name in iter_hotel_acts([day]):
            name = (name or "").strip()
            if not name:
                continue
            # Only check if name is in database
            if name not in hotels_index:
                not_found.append(name)
    
    if not_found:
        return False, f"Hotels not in database: {sorted(set(not_found))}"
    if price_mismatch:
        return False, f"Hotel price mismatch: {price_mismatch}"
    return True, None


def check_attractions_from_search(daily_plans: List[Dict[str, Any]], attractions_index: Dict[str, Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if all attractions are from search results and prices match."""
    if not attractions_index:
        return False, "Attraction database failed to load or is empty"
    not_found: List[str] = []
    cost_mismatch: List[str] = []
    for _act, details, name in iter_attraction_acts(daily_plans):
        if not name or name not in attractions_index:
            not_found.append(name or "<empty>")
            continue
        ticket_price = attractions_index[name].get("ticket_price")
        plan_cost = details.get("cost")
        if ticket_price is None or ticket_price == "":
            continue
        try:
            db_price = int(round(float(ticket_price)))
            if isinstance(plan_cost, (int, float)):
                if int(round(float(plan_cost))) != db_price:
                    cost_mismatch.append(f"{name}: plan has {plan_cost} ≠ database {db_price}")
            else:
                cost_mismatch.append(f"{name}: plan missing valid cost")
        except Exception:
            pass
    if not_found:
        return False, f"Attractions not in database: {sorted(set(not_found))}"
    if cost_mismatch:
        return False, f"Attraction price mismatch: {cost_mismatch}"
    return True, None


def check_meals_from_search(daily_plans: List[Dict[str, Any]], restaurants_index: Dict[str, Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if all meals are from search results and prices match."""
    if not restaurants_index:
        return False, "Restaurant database failed to load or is empty"

    not_found: List[str] = []
    cost_mismatch: List[str] = []

    for _act, details, name in iter_meal_acts(daily_plans):
        cost_val = details.get("cost")

        if not name or name not in restaurants_index:
            not_found.append(name or "<empty>")
            continue

        price_str = restaurants_index[name].get("price_per_person")
        if not price_str:
            continue
        try:
            price_num = float(str(price_str))
            price_rounded = int(round(price_num))
            if isinstance(cost_val, (int, float)):
                if int(round(float(cost_val))) != price_rounded:
                    cost_mismatch.append(f"{name}: plan has {cost_val} ≠ database {price_rounded}")
            else:
                cost_mismatch.append(f"{name}: plan missing valid cost")
        except Exception:
            # Unable to parse database price, skip price consistency check
            pass

    if not_found:
        return False, f"Restaurants not in database: {sorted(set(not_found))}"
    if cost_mismatch:
        return False, f"Restaurant price per person mismatch: {cost_mismatch}"
    return True, None


def check_intercity_public_from_search(
    daily_plans: List[Dict[str, Any]], 
    flights_index: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    trains_index: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if intercity public transport data is valid and comes from database.
    
    Validates:
    1. Required fields exist (number, from, to, cost)
    2. Flight/train number exists in database (flights.csv or trains.csv)
    3. Price matches database (with tolerance)
    """
    intercity_missing: List[str] = []
    not_found: List[str] = []
    price_mismatch: List[str] = []
    
    required_fields = ("number", "from", "to", "cost")
    
    for act, details in iter_intercity_public_acts(daily_plans):
        # Step 1: Check required fields exist
        missing = [k for k in required_fields if details.get(k) in (None, "")]
        if missing:
            intercity_missing.append(f"{act.get('time_slot') or '<no time_slot>'}: missing {missing}")
            continue
        
        number = str(details.get("number")).strip()
        
        try:
            plan_cost = float(details.get("cost"))
        except (ValueError, TypeError):
            plan_cost = None
        
        # Step 2: Check if number exists in database (if indices provided)
        if flights_index is None and trains_index is None:
            # No database provided, skip database validation
            continue
        
        found_in_flights = flights_index and number in flights_index
        found_in_trains = trains_index and number in trains_index
        
        if not found_in_flights and not found_in_trains:
            not_found.append(number)
            continue
        
        # Step 3: Verify price matches ANY record (same train number may have different prices for different routes)
        if plan_cost is not None:
            # Get all matching records
            if found_in_flights:
                records = flights_index[number]
            else:
                records = trains_index[number]
            
            if records:
                # Check if plan price matches ANY record's price
                plan_cost_rounded = int(round(plan_cost))
                price_matched = False
                db_prices = []
                
                for record in records:
                    db_price = record.get("price")
                    if db_price is not None:
                        try:
                            db_price_float = float(db_price)
                            db_prices.append(db_price_float)
                            if plan_cost_rounded == int(round(db_price_float)):
                                price_matched = True
                                break
                        except (ValueError, TypeError):
                            pass
                
                if not price_matched and db_prices:
                    price_mismatch.append(
                        f"{number}: plan has ¥{plan_cost} ≠ database prices {db_prices}"
                    )

    # Compile error message
    error_parts = []
    if intercity_missing:
        error_parts.append(f"Missing fields: {intercity_missing}")
    if not_found:
        error_parts.append(f"Not found in database: {sorted(set(not_found))}")
    if price_mismatch:
        error_parts.append(f"Price mismatch: {price_mismatch}")
    
    if error_parts:
        return False, "; ".join(error_parts)
    return True, None


# ==============================================================================
# DIMENSION 3: Itinerary Structure (12.5%)
# Checks: traceable_accommodation, ends_with_accommodation, essential_meal_coverage, essential_attraction_coverage
# ==============================================================================

def check_accommodation_traceable(daily_plans: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if accommodation is traceable (both hotel activity and accommodation field present)."""
    if not daily_plans:
        return False, "Missing daily_plans"
    missing_days: List[int] = []
    for i, day in enumerate(daily_plans[:-1]):  # Except last day, must have accommodation
        has_hotel_act = any(True for _ in iter_hotel_acts([day]))
        accom = day.get("accommodation")
        has_accom_field = bool(accom)
        if not (has_hotel_act and has_accom_field):
            missing_days.append(i + 1)
    # Last day: allow accommodation field, but name must be "-" (indicating no accommodation) or empty
    last_day = daily_plans[-1]
    last_accom = last_day.get("accommodation")
    if last_accom:
        # If accommodation is a dict, check if name is "-" or empty
        if isinstance(last_accom, dict):
            last_accom_name = (last_accom.get("name") or "").strip()
            # Only report error when name exists and is not "-"
            if last_accom_name and last_accom_name != "-":
                if missing_days:
                    return False, f"Accommodation not traceable on days: {missing_days}; last day accommodation.name should be '-' or empty, actual '{last_accom_name}'"
                return False, f"Last day accommodation.name should be '-' or empty, actual '{last_accom_name}'"
        else:
            # If accommodation is not a dict, consider it invalid
            if missing_days:
                return False, f"Accommodation not traceable on days: {missing_days}; last day accommodation should be empty or name '-'"
            return False, "Last day accommodation should be empty or name '-'"

    if missing_days:
        return False, f"Accommodation not traceable on days: {missing_days}"
    return True, None


def check_last_activity_is_hotel(daily_plans: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if last activity of each day (except last day) is hotel."""
    if not daily_plans:
        return False, "Missing daily_plans"
    invalid_days: List[int] = []
    for i, day in enumerate(daily_plans[:-1]):  # Except last day
        activities = day.get("activities", []) or []
        if not activities:
            invalid_days.append(i + 1)
            continue
        last_act = activities[-1]
        if last_act.get("type") != "hotel":
            invalid_days.append(i + 1)
    if invalid_days:
        return False, f"Last activity not hotel on days: {invalid_days}"
    return True, None


def check_meal_necessity(daily_plans: List[Dict[str, Any]], meta: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if daily meal arrangements comply with meal rules.
    Returns ratio of days with correct meal arrangements (scored per day).

    Rules:
    1. Non-intercity days: Must arrange 2 meals with gap >= 180 minutes
    2. Intercity day arriving at tourist destination (non-org):
       - Arrive < 10:00: must have 2 meals, gap >= 180 minutes
       - Arrive 10:00–16:00: at least 1 meal; if 2 meals then gap >= 180 minutes
       - Arrive > 16:00: 0-1 meal
    3. Intercity day leaving tourist city (non-org):
       - Leave < 10:00: 0 meals
       - Leave 10:00–15:00: 0-1 meal
       - Leave 15:00+: at least 1 meal; if 2 meals then gap >= 180 minutes
    """
    violations: List[str] = []
    total_days = len(daily_plans)
    correct_days = 0

    def _get_start_time_minutes(act: Dict[str, Any]) -> Optional[int]:
        """Get activity start time (in minutes)."""
        start_time = act.get("start_time")
        if not start_time:
            ts = act.get("time_slot", "")
            if ts and "-" in ts:
                start_time = ts.split("-")[0]
        if not start_time:
            return None
        try:
            h, m = map(int, start_time.split(":"))
            return h * 60 + m
        except:
            return None

    def _get_end_time_minutes(act: Dict[str, Any]) -> Optional[int]:
        """Get activity end time (in minutes)."""
        end_time = act.get("end_time")
        if not end_time:
            ts = act.get("time_slot", "")
            if ts and "-" in ts:
                end_time = ts.split("-")[1]
        if not end_time:
            return None
        try:
            h, m = map(int, end_time.split(":"))
            return h * 60 + m
        except:
            return None

    def _check_two_meal_gap(meal_times: List[Tuple[int, int]], day_idx: int) -> None:
        """Check if gap between two meals is >= 120 minutes."""
        if len(meal_times) >= 2:
            meal_times.sort(key=lambda x: x[0])
            prev_start, prev_end = meal_times[0]
            next_start, _ = meal_times[1]
            gap = next_start - prev_end
            if gap < 120:
                violations.append(f"D{day_idx}: Gap between two meals less than 2 hours (gap {gap} minutes)")

    # Get org city
    org_city = normalize_city(meta.get("org"))
    if not org_city:
        return False, "Missing org info, cannot determine meal necessity"

    current_location = org_city

    # Check each day
    for day_idx, day in enumerate(daily_plans, start=1):
        current_city = day.get("current_city", "")
        from_city, to_city = extract_from_to(current_city)
        
        # Collect meals for the day
        meal_times: List[Tuple[int, int]] = []
        for act in day.get("activities", []) or []:
            if act.get("type") == "meal":
                st_min = _get_start_time_minutes(act)
                ed_min = _get_end_time_minutes(act)
                if st_min is not None and ed_min is not None:
                    meal_times.append((st_min, ed_min))
        
        is_intercity_day = bool(from_city and to_city)
        day_violations_before = len(violations)
        
        if is_intercity_day:
            from_city_norm = normalize_city(from_city)
            to_city_norm = normalize_city(to_city)
            is_departure = (from_city_norm == current_location)
            is_from_org = (from_city_norm == org_city)
            is_to_org = (to_city_norm == org_city)
            
            # Leaving tourist city (non-org)
            if is_departure and not is_from_org:
                departure_time = get_intercity_departure_time(day)
                if departure_time is not None:
                    if departure_time < 9:
                        if meal_times:
                            violations.append(f"D{day_idx}: Departure <10:00, should not arrange any meals")
                    elif departure_time < 15.0:
                        if len(meal_times) > 1:
                            violations.append(f"D{day_idx}: Departure 10:00-15:00, should not arrange two meals")
                    else:
                        if not meal_times:
                            violations.append(f"D{day_idx}: Departure >15:00, must arrange at least one meal")
                        if len(meal_times) > 1:
                            _check_two_meal_gap(meal_times, day_idx)
            
            # Arriving at tourist destination (non-org)
            if not is_to_org:
                arrival_time = get_intercity_arrival_time(day)
                if arrival_time is not None:
                    if arrival_time < 10:
                        if len(meal_times) < 2:
                            violations.append(f"D{day_idx}: Arrival <10:00, must arrange two meals")
                        if len(meal_times) >= 2:
                            _check_two_meal_gap(meal_times, day_idx)
                    elif arrival_time < 15.0:
                        if not meal_times:
                            violations.append(f"D{day_idx}: Arrival 10:00-16:00, must arrange at least one meal")
                        if len(meal_times) >= 2:
                            _check_two_meal_gap(meal_times, day_idx)
                    else:
                        if len(meal_times) > 1:
                            violations.append(f"D{day_idx}: Arrival >16:00, should not arrange two meals")
            
            current_location = to_city_norm
        else:
            # Non-intercity day
            if len(meal_times) < 2:
                violations.append(f"D{day_idx}: Non-intercity day must arrange two meals")
            if len(meal_times) >= 2:
                _check_two_meal_gap(meal_times, day_idx)
        
        # Check if this day is correct (no new violations)
        if len(violations) == day_violations_before:
            correct_days += 1

    # Calculate score
    if total_days == 0:
        return True, None
    
    ratio = correct_days / total_days
    
    if ratio == 1.0:
        return True, None
    
    error_msg = f"Meal necessity: {correct_days}/{total_days} days correct; Violations: {'; '.join(violations)}"
    return False, error_msg


def check_attraction_necessity(daily_plans: List[Dict[str, Any]], meta: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if daily attraction arrangements are reasonable.
    
    Rules:
    1. Calculate total duration of attraction-related activities (including attraction visits, travel to/from attractions)
    2. Judge based on available time in destination city:
       - Non-intercity days (full day available): attraction-related duration ≥ 4 hours or ≥2 attractions
       - Intercity day arrival (arrival < 14:00): ≥1 attraction
       - Intercity day arrival (arrival ≥ 14:00): no mandatory requirement
       - Intercity day departure (departure > 14:00): must have at least 1 attraction
       - Other cases: no mandatory requirement
    
    Note: Intercity days departing from or returning to org only check tourist destination city's attractions.
    """
    violations: List[str] = []
    
    def _parse_time_to_hours(time_str: str) -> Optional[float]:
        """Convert time string to hours (float)."""
        if not time_str:
            return None
        try:
            hour, minute = map(int, time_str.split(":"))
            return hour + minute / 60.0
        except:
            return None
    
    def _calculate_duration_minutes(start_str: str, end_str: str) -> int:
        """Calculate duration between two times (in minutes)."""
        start_h = _parse_time_to_hours(start_str)
        end_h = _parse_time_to_hours(end_str)
        if start_h is None or end_h is None:
            return 0
        duration_hours = end_h - start_h
        if duration_hours < 0:
            duration_hours += 24  # Handle day crossover
        return int(duration_hours * 60)
    
    def _get_activity_duration(act: Dict[str, Any]) -> int:
        """Get activity duration (in minutes)."""
        # Priority: use start_time and end_time
        start_time = act.get("start_time", "")
        end_time = act.get("end_time", "")
        
        if not start_time or not end_time:
            # Try to extract from time_slot
            time_slot = act.get("time_slot", "")
            if time_slot and "-" in time_slot:
                parts = time_slot.split("-")
                start_time = parts[0]
                end_time = parts[1] if len(parts) > 1 else ""
        
        if start_time and end_time:
            return _calculate_duration_minutes(start_time, end_time)
        return 0
    
    def _get_attraction_related_duration(day: Dict[str, Any]) -> int:
        """
        Calculate total duration of attraction-related activities for the day (in minutes).
        Includes:
        1. Attraction visit time (type="attraction")
        2. Travel to/from attractions (type="travel_city", from or to is attraction name)
        """
        total_minutes = 0
        activities = day.get("activities", []) or []
        
        # Collect all attraction names
        attraction_names = set()
        for act in activities:
            if act.get("type") == "attraction":
                details = act.get("details") or {}
                name = (details.get("name") or "").strip()
                if name:
                    attraction_names.add(name)
        
        # Calculate attraction-related duration
        for act in activities:
            act_type = act.get("type")
            
            if act_type == "attraction":
                # Attraction visit time
                total_minutes += _get_activity_duration(act)
            
            elif act_type == "travel_city":
                # Check if it's travel to/from attraction
                details = act.get("details") or {}
                from_loc = (details.get("from") or "").strip()
                to_loc = (details.get("to") or "").strip()
                
                # If from or to is an attraction, count in attraction-related time
                if from_loc in attraction_names or to_loc in attraction_names:
                    total_minutes += _get_activity_duration(act)
        
        return total_minutes
    
    # Initial location (departure city)
    org_city = normalize_city(meta.get("org"))
    if not org_city:
        return False, "Missing org info, cannot determine attraction necessity"
    
    current_location = org_city
    
    for day_idx, day in enumerate(daily_plans, start=1):
        current_city = day.get("current_city", "")
        from_city, to_city = extract_from_to(current_city)
        
        # Calculate attraction-related duration for the day
        attraction_minutes = _get_attraction_related_duration(day)
        attraction_hours = attraction_minutes / 60.0
        
        # Count number of attractions for the day
        attraction_count = sum(1 for act in day.get("activities", []) or [] if act.get("type") == "attraction")
        
        # Determine if it's an intercity day
        is_intercity_day = bool(from_city and to_city)
        
        if is_intercity_day:
            from_city_norm = normalize_city(from_city)
            to_city_norm = normalize_city(to_city)
            
            is_departure = (from_city_norm == current_location)
            is_from_org = (from_city_norm == org_city)
            is_to_org = (to_city_norm == org_city)
            
            # Departing from org: only check after arrival
            # Returning to org: only check before departure
            # Between tourist cities: need to check both before departure and after arrival
            
            if is_departure and not is_from_org:
                # Leaving tourist city (non-org)
                departure_time = get_intercity_departure_time(day)
                if departure_time is not None:
                    if departure_time > 16.0:
                        # Departure > 14:00: must have at least 1 attraction
                        if attraction_count < 1:
                            violations.append(
                                f"D{day_idx}: Departure time later than 14:00, must arrange at least 1 attraction (current: {attraction_count})"
                            )
            
            if not is_to_org:
                # Arriving at tourist destination city (non-org)
                arrival_time = get_intercity_arrival_time(day)
                if arrival_time is not None:
                    if arrival_time < 12.0:
                        # Arrival < 14:00: ≥1 attraction
                        if attraction_count < 1:
                            violations.append(
                                f"D{day_idx}: Arrival time earlier than 14:00, must arrange at least 1 attraction (current: {attraction_count})"
                            )
                    # Arrival ≥ 14:00: no mandatory requirement
            
            # Update current location
            current_location = to_city_norm
            
        else:
            # Non-intercity day: attraction-related duration ≥ 4 hours or ≥2 attractions
            if attraction_hours < 4.0 and attraction_count < 2:
                violations.append(
                    f"D{day_idx}: Non-intercity day requires attraction-related duration ≥ 4 hours or ≥2 attractions (current: {attraction_hours:.1f} hours, {attraction_count} attractions)"
                )
    
    if violations:
        return False, f"Attraction arrangements unreasonable: {'; '.join(violations)}"
    return True, None


# ==============================================================================
# DIMENSION 4: Time Feasibility (12.5%)
# Checks: no_time_overlaps, reasonable_transfer_time
# ==============================================================================

def check_time_no_overlap(daily_plans: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if activities have time overlaps."""
    conflicts: List[str] = []
    for day_idx, day in enumerate(daily_plans, start=1):
        ranges: List[Tuple[int, int, str]] = []
        for act in day.get("activities", []) or []:
            slot = act.get("time_slot")
            if not slot:
                continue
            s, e = slot_to_minutes(slot)
            if s is None or e is None:
                continue
            ranges.append((s, e, act.get("type") or ""))
        ranges.sort(key=lambda x: x[0])
        for i in range(1, len(ranges)):
            prev = ranges[i - 1]
            curr = ranges[i]
            if curr[0] < prev[1]:
                conflicts.append(f"D{day_idx}: {prev[2]} and {curr[2]} have time overlap")
    if conflicts:
        return False, f"Time overlaps exist: {conflicts}"
    return True, None


def check_transfer_time_reasonable(daily_plans: List[Dict[str, Any]], locations_index: Optional[Dict[str, Dict[str, Any]]] = None, database_dir: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
    """Check if transfer times between anchor activities are reasonable."""
    violations: List[str] = []
    skipped: List[str] = []
    anchor_types = {"hotel", "attraction", "meal", "travel_intercity_public"}

    def _coord_key(lat_str: str, lon_str: str) -> str:
        """Generate coordinate key, format 'latitude,longitude', directly use string concatenation to preserve original precision."""
        return f"{lat_str},{lon_str}"

    def _lookup_duration_minutes_in_matrix(olon_str: str, olat_str: str, dlon_str: str, dlat_str: str, mode: str) -> Optional[float]:
        # Note: Database format is "latitude,longitude"
        key_o = _coord_key(olat_str, olon_str)
        key_d = _coord_key(dlat_str, dlon_str)
        
        # Use passed database_dir (if any), otherwise use default global path
        if database_dir is not None:
            db_dir = get_database_dir(database_dir)
            distance_matrix_path = db_dir / "transportation" / "distance_matrix.csv"
        else:
            distance_matrix_path = _DATABASE_DIR / "transportation" / "distance_matrix.csv"
        
        try:
            with open(str(distance_matrix_path), "r", encoding="utf-8-sig") as f:  # Use utf-8-sig to handle BOM
                reader = csv.DictReader(f)
                for row in reader:
                    if (row.get("origin") == key_o and row.get("destination") == key_d):
                        dur = row.get("duration_minutes")
                        try:
                            return float(dur)
                        except Exception:
                            return None
        except Exception:
            return None
        return None
    
    for day_idx, day in enumerate(daily_plans, start=1):
        anchors: List[Tuple[int, int, Dict[str, Any]]] = []
        activities = day.get("activities", []) or []
        for act in activities:
            if act.get("type") not in anchor_types:
                continue
            s, e = slot_to_minutes(act.get("time_slot"))
            if s is None or e is None:
                continue
            anchors.append((s, e, act))
        
        for i in range(1, len(anchors)):
            prev_s, prev_e, prev_act = anchors[i - 1]
            curr_s, curr_e, curr_act = anchors[i]
            gap_min = curr_s - prev_e

            if prev_e > curr_s:
                # This case includes both time overlap and day crossover, we need to distinguish
                if (prev_e - curr_s) > 12 * 60:  # If time difference exceeds 12 hours, consider it day crossover
                    gap_min += 24 * 60
                else:  # Otherwise consider it time overlap, handled by check_time_no_overlap
                    # We can also ignore here, as another function will check
                    continue

            if gap_min < 0:
                # Non-overlap already handled by check_time_no_overlap, ignore here
                continue
            
            # Calculate buffer time and subtract from gap
            buffer_duration = 0.0
            for act_buf in activities:
                act_type = act_buf.get("type", "").strip()
                if act_type == "buffer":
                    s_buf, e_buf = slot_to_minutes(act_buf.get("time_slot"))

                    if s_buf is None or e_buf is None:
                        continue

                    # ====== Handle day crossover ======
                    # If buffer start time is less than previous anchor end time, it's next day
                    if s_buf < prev_e:
                        s_buf += 1440
                        e_buf += 1440
                    # Similarly, if buffer end time is less than previous anchor end time, add a day
                    elif e_buf < prev_e:
                        e_buf += 1440

                    # If current anchor is early morning next day, also add offset
                    if curr_s < prev_e:
                        curr_s += 1440

                    # Check if buffer is between the two anchors
                    if prev_e <= s_buf and e_buf <= curr_s:
                        buffer_duration += (e_buf - s_buf)

            
            # Subtract buffer time from gap, get actual time interval to verify
            gap_min_without_buffer = gap_min - buffer_duration
            
            # Anchor location names:
            # - Normal anchor (hotel/attraction/meal): use details.name
            # - Intercity anchor (travel_intercity_public):
            #   * As previous anchor, take arrival airport (details.to)
            #   * As next anchor, take departure airport (details.from)
            prev_details = (prev_act.get("details") or {})
            curr_details = (curr_act.get("details") or {})
            if prev_act.get("type") == "travel_intercity_public":
                prev_name = (prev_details.get("to") or prev_act.get("type") or "").strip()
            else:
                prev_name = (prev_details.get("name") or prev_act.get("type") or "").strip()
            if curr_act.get("type") == "travel_intercity_public":
                curr_name = (curr_details.get("from") or curr_act.get("type") or "").strip()
            else:
                curr_name = (curr_details.get("name") or curr_act.get("type") or "").strip()

            # Only when both names can be resolved to coordinates, look up distance_matrix; otherwise skip (record)
            if prev_name and curr_name:
                if prev_name == curr_name:
                    # Same name, skip directly, don't record as error or skipped item, corresponds to transit type
                    continue
                lat1, lon1 = resolve_name_coords(prev_name, locations_index)
                lat2, lon2 = resolve_name_coords(curr_name, locations_index)
                if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
                    skipped.append(f"D{day_idx}:{prev_name}->{curr_name}")
                    print(f"D{day_idx}:{prev_name}->{curr_name} missing coordinates")
                    continue
                taxi_min = _lookup_duration_minutes_in_matrix(lon1, lat1, lon2, lat2, "taxi")
                if taxi_min is None:
                    skipped.append(f"D{day_idx}:{prev_name}->{curr_name}")
                    print(f"D{day_idx}:{prev_name}->{curr_name} missing distance matrix (query: {lat1},{lon1} -> {lat2},{lon2})")
                    continue
                
                # Calculate allowed time range (no longer add extra buffer time, as already excluded from gap)
                # min round down to multiple of 10, max round up to multiple of 10
                min_allowed = min(max(0.0, taxi_min-5),(taxi_min // 10) * 10)
                max_allowed = max(taxi_min+5,math.ceil(taxi_min / 10) * 10)
                
                if not (min_allowed <= gap_min_without_buffer <= max_allowed):
                    violations.append(
                        f"D{day_idx}:{prev_name}->{curr_name} query got commute time {taxi_min:.0f}min, plan shows gap {gap_min_without_buffer:.0f}min (after excluding buffer {buffer_duration:.0f}min) not in [{min_allowed:.0f},{max_allowed:.0f}]min\nD{day_idx}:{prev_name}({lat1},{lon1})->{curr_name}({lat2},{lon2}) "
                    )
            else:
                skipped.append(f"D{day_idx}:{prev_name}->{curr_name}")

    if violations:
        reason = f"Anchor transfer time unreasonable: {violations}"
        if skipped:
            reason += f"; Unable to evaluate pairs: {skipped}"
        return False, reason
    # If no evaluable pairs and no violations, consider pass, but can prompt skipped items
    if skipped:
        return True, f"Some pairs missing coordinates, skipped: {skipped}"
    return True, None


# ==============================================================================
# DIMENSION 5: Business Hours (12.5%)
# Checks: attraction_visit_within_opening_hours, dining_within_service_hours, avoidance_of_closure_days
# ==============================================================================

def check_attractions_in_opening_hours(daily_plans: List[Dict[str, Any]], attractions_index: Dict[str, Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if attractions are visited within opening hours."""
    if not attractions_index:
        return False, "Attraction database failed to load or is empty"
    out_of_hours: List[str] = []
    missing_time_info: List[str] = []
    for act, _details, name in iter_attraction_acts(daily_plans):
        if not name or name not in attractions_index:
            # Handled by authenticity validation
            continue
        idx = attractions_index[name]
        slot = act.get("time_slot")
        slot_start, slot_end = parse_time_slot(slot)
        open_str = (idx.get("opening_time") or "").strip()
        close_str = (idx.get("closing_time") or "").strip()
        if is_all_day(open_str, close_str):
            continue
        open_t = parse_time_hhmm(open_str)
        close_t = parse_time_hhmm(close_str)
        if not slot_start or not slot_end or not open_t or not close_t:
            missing_time_info.append(name)
            continue
        if not is_within_business_hours(slot_start, slot_end, open_t, close_t):
            out_of_hours.append(f"{name}({slot} not within {open_str}-{close_str})")
    if out_of_hours:
        return False, f"Attraction opening hours mismatch: {out_of_hours}"
    if missing_time_info:
        return False, f"Missing opening hours or invalid time_slot: {sorted(set(missing_time_info))}"
    return True, None


def check_meals_in_business_hours(daily_plans: List[Dict[str, Any]], restaurants_index: Dict[str, Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if meals are scheduled within restaurant business hours."""
    if not restaurants_index:
        return False, "Restaurant database failed to load or is empty"

    out_of_hours: List[str] = []
    missing_slot: List[str] = []

    for act, _details, name in iter_meal_acts(daily_plans):
        if not name or name not in restaurants_index:
            # Name not in database, handled by source validation, skip here
            continue

        slot = act.get("time_slot")
        slot_start, slot_end = parse_time_slot(slot)
        open_str = (restaurants_index[name].get("opening_time") or "").strip()
        close_str = (restaurants_index[name].get("closing_time") or "").strip()
        open_t = parse_time_hhmm(open_str)
        close_t = parse_time_hhmm(close_str)

        # If time_slot is missing, record as error
        if not slot_start or not slot_end:
            missing_slot.append(name)
            continue

        # If business hours are missing, skip this restaurant's check
        if not open_t or not close_t:
            continue

        if not is_within_business_hours(slot_start, slot_end, open_t, close_t):
            out_of_hours.append(f"{name}({slot} not within {open_str}-{close_str})")

    if missing_slot:
        return False, f"Missing time_slot: {sorted(set(missing_slot))}"
    if out_of_hours:
        return False, f"Meal time not within business hours: {out_of_hours}"
    return True, None


def check_attractions_not_closed(
    daily_plans: List[Dict[str, Any]], 
    attractions_index: Dict[str, Dict[str, Any]],
    meta: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Check if attractions are not visited on their closing dates (e.g., closed on Mondays).
    
    Args:
        daily_plans: Daily plan list
        attractions_index: Attraction database index
        meta: Metadata containing depart_weekday
    
    Returns:
        (True, None) if all attractions are visited on open days
        (False, error_message) if any attraction is visited on a closed day
    """
    if not attractions_index:
        return False, "Attraction database failed to load or is empty"
    
    # Get departure weekday from meta (1=Monday, 7=Sunday)
    depart_weekday = meta.get("depart_weekday")
    if not depart_weekday:
        # If depart_weekday is not provided, skip this check
        return True, None
    
    try:
        depart_weekday = int(depart_weekday)
    except (ValueError, TypeError):
        return False, f"Invalid depart_weekday value: {depart_weekday}"
    
    closed_attractions = []
    
    for day_index, day in enumerate(daily_plans):
        # Calculate the weekday for this day
        current_weekday = calculate_day_of_week(depart_weekday, day_index)
        
        # Check all attractions in this day
        for act in day.get("activities", []) or []:
            if act.get("type") != "attraction":
                continue
            
            details = act.get("details") or {}
            name = (details.get("name") or "").strip()
            
            if not name or name not in attractions_index:
                # Not in database, handled by authenticity validation
                continue
            
            attraction_info = attractions_index[name]
            closing_dates_str = attraction_info.get("closing_dates")
            
            # Check if attraction is closed on this weekday
            if is_attraction_closed_on_day(closing_dates_str, current_weekday):
                # Map weekday number to name for error message
                weekday_names = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 
                                4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
                weekday_name = weekday_names.get(current_weekday, str(current_weekday))
                
                closed_attractions.append(
                    f"{name} on Day {day_index + 1} ({weekday_name}), "
                    f"but closed on: {closing_dates_str}"
                )
    
    if closed_attractions:
        return False, f"Attractions visited on closing dates: {'; '.join(closed_attractions)}"
    
    return True, None


# ==============================================================================
# DIMENSION 6: Duration Rationality (12.5%)
# Checks: reasonable_duration_at_attractions, reasonable_meal_duration
# ==============================================================================

def check_attractions_duration_reasonable(daily_plans: List[Dict[str, Any]], attractions_index: Dict[str, Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if attraction visit durations are within reasonable ranges."""
    if not attractions_index:
        return False, "Attraction database failed to load or is empty"
    duration_invalid: List[str] = []
    for _act, details, name in iter_attraction_acts(daily_plans):
        if not name or name not in attractions_index:
            # Handled by authenticity validation
            continue
        idx = attractions_index[name]
        # Use activity's time_slot to parse actual visit duration
        time_slot = _act.get("time_slot")
        start_m, end_m = slot_to_minutes(time_slot)
        plan_duration = None
        if start_m is not None and end_m is not None and end_m >= start_m:
            plan_duration = (end_m - start_m) / 60.0
        min_hours = parse_duration_hours(idx.get("min_visit_hours"))
        max_hours = parse_duration_hours(idx.get("max_visit_hours"))
        if plan_duration is None or min_hours is None or max_hours is None:
            duration_invalid.append(f"{name}: Missing duration")
            continue
        if not (min_hours <= plan_duration <= max_hours):
            duration_invalid.append(f"{name}: plan has {plan_duration}h not in recommended {min_hours}-{max_hours}h")
    if duration_invalid:
        return False, f"Attraction visit duration unreasonable: {duration_invalid}"
    return True, None


def check_meal_duration_reasonable(daily_plans: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Check if meal durations are within reasonable ranges.
    
    Args:
        daily_plans: List of daily plans
    
    Rules:
    - A meal should take at least 30 minutes (too short is unrealistic)
    - A meal should not exceed 120 minutes (too long blocks other activities)
    """
    # Duration constraints (in minutes)
    MIN_MEAL_MINUTES = 30
    MAX_MEAL_MINUTES = 150
    
    duration_invalid: List[str] = []
    
    for act, details, name in iter_meal_acts(daily_plans):
        if not name:
            continue
        
        # Use activity's time_slot to parse actual meal duration
        time_slot = act.get("time_slot")
        start_m, end_m = slot_to_minutes(time_slot)
        
        if start_m is None or end_m is None:
            duration_invalid.append(f"{name}: Missing time_slot or invalid format")
            continue
        
        # Calculate duration in minutes
        duration_minutes = end_m - start_m
        if duration_minutes < 0:
            duration_minutes += 24 * 60  # Handle midnight crossover
        
        if duration_minutes < MIN_MEAL_MINUTES:
            duration_invalid.append(
                f"{name}: meal duration {duration_minutes}min < minimum {MIN_MEAL_MINUTES}min"
            )
        elif duration_minutes > MAX_MEAL_MINUTES:
            duration_invalid.append(
                f"{name}: meal duration {duration_minutes}min > maximum {MAX_MEAL_MINUTES}min"
            )
    
    if duration_invalid:
        return False, f"Meal duration unreasonable: {duration_invalid}"
    return True, None


# ==============================================================================
# DIMENSION 7: Cost Calculation Accuracy (12.5%)
# Checks: cost_calculation_correctness
# ==============================================================================

def check_budget_accuracy(plan: Dict[str, Any], daily_plans: List[Dict[str, Any]], meta: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if budget summary is accurate compared to calculated costs from daily plans.
    
    Rules:
    1. travel_intercity_public: Count transit transfers (same day multiple flights) only once, consider people_number
    2. accommodation: price_per_night * nights * room_number
    3. meal: price_per_person * people_number
    4. attraction: ticket_price * people_number
    5. travel_city: count by taxi, ≤4 people = 1 taxi
    
    Allow 10% margin of error.
    """
    # Get plan's budget summary
    budget_summary = plan.get("budget_summary", {})
    if not budget_summary:
        return False, "Missing budget_summary in plan"
    
    plan_total = budget_summary.get("total_estimated_budget")
    if plan_total is None:
        return False, "Missing total_estimated_budget in budget_summary"
    
    try:
        plan_total = float(plan_total)
    except:
        return False, f"Invalid total_estimated_budget: {plan_total}"
    
    # Get meta info
    people_number = int(meta.get("people_number", 1))
    room_number = int(meta.get("room_number", 1))
    
    # Calculate actual costs
    transportation_cost = 0.0
    accommodation_cost = 0.0
    meals_cost = 0.0
    attractions_cost = 0.0
    
    # 1. Calculate transportation costs (intercity)
    for day_idx, day in enumerate(daily_plans):
        # For transfers (multiple intercity in same day), each segment shows total price
        # So we only count the FIRST one to avoid double counting
        day_intercity_cost = 0.0
        found_first = False
        for act in day.get("activities", []) or []:
            if act.get("type") == "travel_intercity_public" and not found_first:
                details = act.get("details") or {}
                cost = details.get("cost", 0)
                try:
                    day_intercity_cost = float(cost)
                    found_first = True
                except:
                    pass
        
        # Multiply by people number
        if day_intercity_cost > 0:
            transportation_cost += day_intercity_cost * people_number
    
    # 2. Calculate accommodation costs
    # Count nights (days - 1, as last day doesn't need accommodation)
    nights = len(daily_plans) - 1 if len(daily_plans) > 1 else 0
    for day_idx, day in enumerate(daily_plans[:-1]):  # Except last day
        accom = day.get("accommodation")
        if isinstance(accom, dict):
            price = accom.get("price") or accom.get("price_per_night") or accom.get("cost")
            if price:
                try:
                    accommodation_cost += float(price) * room_number
                except:
                    pass
    
    # 3. Calculate meals costs
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") == "meal":
                details = act.get("details") or {}
                cost = details.get("cost")
                if cost:
                    try:
                        meals_cost += float(cost) * people_number
                    except:
                        pass
    
    # 4. Calculate attraction costs
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") == "attraction":
                details = act.get("details") or {}
                cost = details.get("cost")
                if cost:
                    try:
                        attractions_cost += float(cost) * people_number
                    except:
                        pass
    
    # 5. Calculate city transportation costs (taxis)
    # ≤4 people = 1 taxi, >4 people = need more taxis
    taxis_needed = max(1, (people_number + 3) // 4)  # Round up division
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") == "travel_city":
                details = act.get("details") or {}
                cost = details.get("cost")
                if cost:
                    try:
                        transportation_cost += float(cost) * taxis_needed
                    except:
                        pass
    
    # Calculate total
    calculated_total = transportation_cost + accommodation_cost + meals_cost + attractions_cost
    
    # Check if within 10% margin
    if plan_total == 0:
        if calculated_total == 0:
            return True, None
        else:
            return False, f"Plan shows 0 budget but calculated {calculated_total:.2f}"
    
    error_rate = abs(calculated_total - plan_total) / plan_total
    
    if error_rate <= 0.10:
        return True, None
    else:
        breakdown = (
            f"Budget accuracy failed: Plan total={plan_total:.2f}, "
            f"Calculated total={calculated_total:.2f} "
            f"(Transportation={transportation_cost:.2f}, "
            f"Accommodation={accommodation_cost:.2f}, "
            f"Meals={meals_cost:.2f}, "
            f"Attractions={attractions_cost:.2f}), "
            f"Error rate={error_rate:.2%} (exceeds 10% threshold)"
        )
        return False, breakdown


# ==============================================================================
# DIMENSION 8: Activity Diversity (12.5%)
# Checks: diverse_meal_options, diverse_attraction_options
# ==============================================================================

def check_diverse_restaurants(daily_plans: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Check restaurant diversity - no duplicate restaurants across all days.
    """
    restaurant_names: set[str] = set()
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") == "meal":
                name = (act.get("details") or {}).get("name")
                if name and name in restaurant_names:
                    return False, f"Duplicate restaurant: {name}"
                if name:
                    restaurant_names.add(name)
    return True, None


def check_diverse_attractions(daily_plans: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Check if all attractions are unique (no duplicates)."""
    attraction_names: set[str] = set()
    for day in daily_plans:
        for act in day.get("activities", []) or []:
            if act.get("type") == "attraction":
                name = (act.get("details") or {}).get("name")
                if name and name in attraction_names:
                    return False, f"Duplicate attraction: {name}"
                if name:
                    attraction_names.add(name)
    return True, None



# ==============================================================================
# Dimension Score Calculation
# ==============================================================================

def calculate_dimension_scores(check_results: Dict[str, Tuple[bool, Optional[str]]]) -> Dict[str, Any]:
    """
    Calculate scores for each dimension based on check results.
    
    Args:
        check_results: Dictionary of {check_name: (passed, error_message)}
    
    Returns:
        Dictionary containing:
        - dimension_scores: {dimension_name: score} (0.0-1.0 for each dimension)
        - dimension_details: {dimension_name: {checks: [...], passed: int, total: int}}
        - total_weighted_score: weighted sum of all dimension scores (0.0-1.0)
        - total_checks_passed: total number of checks passed
        - total_checks: total number of checks
    """
    dimension_scores = {}
    dimension_details = {}
    total_weighted_score = 0.0
    total_checks_passed = 0
    total_checks = 0
    
    for dim_name, dim_config in EVALUATION_DIMENSIONS.items():
        weight = dim_config["weight"]
        checks = dim_config["checks"]
        
        passed_count = 0
        check_details = []
        
        for check_name in checks:
            if check_name in check_results:
                passed, msg = check_results[check_name]
                check_details.append({
                    "name": check_name,
                    "passed": passed,
                    "message": msg
                })
                if passed:
                    passed_count += 1
                total_checks += 1
            else:
                # Check not found in results, consider as not evaluated
                check_details.append({
                    "name": check_name,
                    "passed": False,
                    "message": "Check not evaluated"
                })
                total_checks += 1
        
        # Calculate dimension score (all-or-nothing: 1 if all passed, 0 otherwise)
        dim_score = 1.0 if (checks and passed_count == len(checks)) else 0.0
        dimension_scores[dim_name] = dim_score
        
        dimension_details[dim_name] = {
            "checks": check_details,
            "passed": passed_count,
            "total": len(checks),
            "weight": weight,
            "weighted_score": dim_score * weight
        }
        
        total_weighted_score += dim_score * weight
        total_checks_passed += passed_count
    
    return {
        "dimension_scores": dimension_scores,
        "dimension_details": dimension_details,
        "total_weighted_score": total_weighted_score,
        "total_checks_passed": total_checks_passed,
        "total_checks": total_checks
    }


def get_dimension_summary(dimension_result: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of dimension scores.
    
    Args:
        dimension_result: Result from calculate_dimension_scores()
    
    Returns:
        Formatted string summary
    """
    lines = []
    lines.append("=" * 60)
    lines.append("COMMONSENSE EVALUATION SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Total Weighted Score: {dimension_result['total_weighted_score']:.2%}")
    lines.append(f"Checks Passed: {dimension_result['total_checks_passed']}/{dimension_result['total_checks']}")
    lines.append("-" * 60)
    lines.append("DIMENSION BREAKDOWN:")
    lines.append("-" * 60)
    
    for dim_name, details in dimension_result["dimension_details"].items():
        score = dimension_result["dimension_scores"][dim_name]
        lines.append(f"\n{dim_name} (weight: {details['weight']:.0%}):")
        lines.append(f"  Score: {score:.2%} ({details['passed']}/{details['total']} checks passed)")
        lines.append(f"  Weighted contribution: {details['weighted_score']:.4f}")
        
        for check in details["checks"]:
            status = "✓" if check["passed"] else "✗"
            lines.append(f"    {status} {check['name']}")
            if not check["passed"] and check["message"]:
                # Truncate long messages
                msg = check["message"][:100] + "..." if len(check["message"]) > 100 else check["message"]
                lines.append(f"      └─ {msg}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


# ==============================================================================
# Main Evaluation Function
# ==============================================================================

def eval_commonsense(plan: Dict[str, Any], meta: Dict[str, Any], database_dir: Optional[Path] = None) -> Dict[str, Tuple[bool, Optional[str]]]:
    """
    Evaluate commonsense constraints.
    
    Args:
        plan: Travel plan dictionary
        meta: Metadata dictionary
        database_dir: Database directory path (if specified, will use that sample's database)
    """
    res: Dict[str, Tuple[bool, Optional[str]]] = {}
    daily_plans: List[Dict[str, Any]] = plan.get("daily_plans", []) or []
    
    # If daily_plans is missing, all checks that depend on itinerary will be False with unified reason
    if not daily_plans:
        reason = "Missing daily_plans"
        res["valid_trip_duration"] = (False, reason)
        res["closed_loop_route_structure"] = (False, reason)
        res["seamless_intercity_transfers"] = (False, reason)
        res["validated_accommodation"] = (False, reason)
        res["validated_attractions"] = (False, reason)
        res["validated_meals"] = (False, reason)
        res["validated_transportation"] = (False, reason)
        res["traceable_accommodation"] = (False, reason)
        res["ends_with_accommodation"] = (False, reason)
        res["essential_meal_coverage"] = (False, reason)
        res["essential_attraction_coverage"] = (False, reason)
        res["no_time_overlaps"] = (False, reason)
        res["reasonable_transfer_time"] = (False, reason)
        res["attraction_visit_within_opening_hours"] = (False, reason)
        res["dining_within_service_hours"] = (False, reason)
        res["reasonable_duration_at_attractions"] = (False, reason)
        res["reasonable_meal_duration"] = (False, reason)
        res["cost_calculation_correctness"] = (False, reason)
        res["diverse_meal_options"] = (False, reason)
        res["diverse_attraction_options"] = (False, reason)
        return res
    
    # ==================== Load all database indices ====================
    if database_dir is not None:
        db_dir = get_database_dir(database_dir)
        hotels_csv_path = str(db_dir / "hotels" / "hotels.csv")
        attractions_csv_path = str(db_dir / "attractions" / "attractions.csv")
        restaurants_csv_path = str(db_dir / "restaurants" / "restaurants.csv")
        flights_csv_path = str(db_dir / "flights" / "flights.csv")
        trains_csv_path = str(db_dir / "trains" / "trains.csv")
        locations_coords_path = str(db_dir / "locations" / "locations_coords.csv")
    else:
        hotels_csv_path = HOTELS_CSV_PATH
        attractions_csv_path = ATTRACTIONS_CSV_PATH
        restaurants_csv_path = RESTAURANTS_CSV_PATH
        flights_csv_path = str(_DATABASE_DIR / "flights" / "flights.csv")
        trains_csv_path = str(_DATABASE_DIR / "trains" / "trains.csv")
        locations_coords_path = LOCATIONS_COORDS_CSV_PATH
    
    hotels_index = load_hotel_index(hotels_csv_path)
    attractions_index = load_attraction_index(attractions_csv_path)
    restaurants_index = load_restaurant_index(restaurants_csv_path)
    flights_index = load_flights_index(flights_csv_path)
    trains_index = load_trains_index(trains_csv_path)
    locations_index = load_locations_index(locations_coords_path)

    # ==================== DIMENSION 1: Route Consistency ====================
    res["valid_trip_duration"] = check_valid_days(daily_plans, meta)
    res["closed_loop_route_structure"] = check_route_closed_loop(daily_plans, meta)
    res["seamless_intercity_transfers"] = check_intercity_transportation_consistency(daily_plans, meta, database_dir)

    # ==================== DIMENSION 2: Sandbox Compliance ====================
    res["validated_accommodation"] = check_hotels_from_search(daily_plans, hotels_index)
    res["validated_attractions"] = check_attractions_from_search(daily_plans, attractions_index)
    res["validated_meals"] = check_meals_from_search(daily_plans, restaurants_index)
    res["validated_transportation"] = check_intercity_public_from_search(daily_plans, flights_index, trains_index)

    # ==================== DIMENSION 3: Itinerary Structure ====================
    res["traceable_accommodation"] = check_accommodation_traceable(daily_plans)
    res["ends_with_accommodation"] = check_last_activity_is_hotel(daily_plans)
    res["essential_meal_coverage"] = check_meal_necessity(daily_plans, meta)
    res["essential_attraction_coverage"] = check_attraction_necessity(daily_plans, meta)

    # ==================== DIMENSION 4: Time Feasibility ====================
    res["no_time_overlaps"] = check_time_no_overlap(daily_plans)
    res["reasonable_transfer_time"] = check_transfer_time_reasonable(daily_plans, locations_index, database_dir)

    # ==================== DIMENSION 5: Business Hours ====================
    res["attraction_visit_within_opening_hours"] = check_attractions_in_opening_hours(daily_plans, attractions_index)
    res["dining_within_service_hours"] = check_meals_in_business_hours(daily_plans, restaurants_index)
    res["avoidance_of_closure_days"] = check_attractions_not_closed(daily_plans, attractions_index, meta)

    # ==================== DIMENSION 6: Duration Rationality ====================
    res["reasonable_duration_at_attractions"] = check_attractions_duration_reasonable(daily_plans, attractions_index)
    res["reasonable_meal_duration"] = check_meal_duration_reasonable(daily_plans)

    # ==================== DIMENSION 7: Cost Calculation Accuracy ====================
    res["cost_calculation_correctness"] = check_budget_accuracy(plan, daily_plans, meta)

    # ==================== DIMENSION 8: Activity Diversity ====================
    res["diverse_meal_options"] = check_diverse_restaurants(daily_plans)
    res["diverse_attraction_options"] = check_diverse_attractions(daily_plans)

    return res


def eval_commonsense_with_dimensions(
    plan: Dict[str, Any], 
    meta: Dict[str, Any], 
    database_dir: Optional[Path] = None,
    print_summary: bool = False
) -> Dict[str, Any]:
    """
    Evaluate commonsense constraints with dimension-based scoring.
    
    This is an enhanced version of eval_commonsense that also calculates
    dimension scores based on the EVALUATION_DIMENSIONS configuration.
    
    Args:
        plan: Travel plan dictionary
        meta: Metadata dictionary
        database_dir: Database directory path (if specified, will use that sample's database)
        print_summary: If True, prints a human-readable summary to stdout
    
    Returns:
        Dictionary containing:
        - check_results: Original check results {check_name: (passed, error_message)}
        - dimension_scores: {dimension_name: score} (0.0-1.0 for each dimension)
        - dimension_details: {dimension_name: {checks: [...], passed: int, total: int}}
        - total_weighted_score: weighted sum of all dimension scores (0.0-1.0)
        - total_checks_passed: total number of checks passed
        - total_checks: total number of checks
    """
    # Run all checks
    check_results = eval_commonsense(plan, meta, database_dir)
    
    # Calculate dimension scores
    dimension_result = calculate_dimension_scores(check_results)
    
    # Combine results
    result = {
        "check_results": check_results,
        **dimension_result
    }
    
    # Optionally print summary
    if print_summary:
        print(get_dimension_summary(dimension_result))
    
    return result


def get_all_check_names() -> List[str]:
    """
    Get all check names from EVALUATION_DIMENSIONS.
    
    Returns:
        List of all check names across all dimensions
    """
    all_checks = []
    for dim_config in EVALUATION_DIMENSIONS.values():
        all_checks.extend(dim_config["checks"])
    return all_checks
