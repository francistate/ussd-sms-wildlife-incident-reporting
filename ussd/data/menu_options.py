"""
Menu options and constants for USSD flows
"""

# Emergency incident types
INCIDENT_TYPES = {
    "1": {"code": "crop_damage", "name": "Crop Damage"},
    "2": {"code": "livestock_attack", "name": "Livestock Attack"},
    "3": {"code": "property_damage", "name": "Property Damage"},
    "4": {"code": "human_injury", "name": "Human Injury/Threat"},
    "5": {"code": "dangerous_behavior", "name": "Dangerous Animal"}
}

# Animal species (9 + Other)
SPECIES = {
    "1": "Elephant",
    "2": "Lion",
    "3": "Leopard",
    "4": "Buffalo",
    "5": "Hyena",
    "6": "Baboon",
    "7": "Warthog",
    "8": "Giraffe",
    "9": "Zebra"
}

# Locations (9 + Other)
LOCATIONS = {
    "1": "Location 1",
    "2": "Location 2",
    "3": "Location 3",
    "4": "Location 4",
    "5": "Location 5",
    "6": "Location 6",
    "7": "Location 7",
    "8": "Location 8",
    "9": "Location 9"
}

# Animal count options
COUNT_OPTIONS = {
    "1": "1",
    "2": "2-5",
    "3": "6-10",
    "4": "10+"
}

# Severity options
SEVERITY_OPTIONS = {
    "1": "minor",
    "2": "moderate",
    "3": "severe"
}

# Livestock types
LIVESTOCK_TYPES = {
    "1": "cattle",
    "2": "goats",
    "3": "sheep",
    "4": "donkeys",
    "5": "chickens"
}

# Property damage types
PROPERTY_TYPES = {
    "1": "fence",
    "2": "building",
    "3": "water_system",
    "4": "crops_storage"
}

# Behavior options (for sightings)
BEHAVIOR_OPTIONS = {
    "1": "grazing",
    "2": "moving",
    "3": "resting",
    "4": "drinking",
    "5": "unknown"
}

# Weather options (for sightings)
WEATHER_OPTIONS = {
    "1": "clear",
    "2": "rainy",
    "3": "cloudy",
    "4": "skip"
}

# Time occurrence for past incidents
WHEN_OPTIONS = {
    "1": "yesterday",
    "2": "2-7_days",
    "3": "over_week"
}
