"""
USSD Menu Handlers
Handles the different reporting flows: emergency, sighting, past incident
"""
from typing import Dict, Any
from datetime import datetime

from data.menu_options import (
    INCIDENT_TYPES, SPECIES, LOCATIONS, COUNT_OPTIONS,
    SEVERITY_OPTIONS, LIVESTOCK_TYPES, PROPERTY_TYPES,
    BEHAVIOR_OPTIONS, WEATHER_OPTIONS
)
from ussd_services.helpers import validate_text_input


def show_main_menu() -> str:
    """Display the main menu"""
    response = "CON Wildlife Conservation\n"
    response += "1. Report Emergency NOW\n"
    response += "2. Wildlife Sighting\n"
    response += "3. Past Incident\n"
    response += "4. Help"
    return response


def show_help() -> str:
    """Display help information"""
    response = "END Wildlife Conservation Help\n\n"
    response += "Report wildlife incidents:\n"
    response += "- Emergencies (happening now)\n"
    response += "- Wildlife sightings\n"
    response += "- Past incidents\n\n"
    response += "Dial again to start."
    return response


def handle_invalid_input() -> str:
    """Handle invalid menu selections"""
    return "END Invalid selection.\nPlease dial again."


def handle_emergency_incident(session: Dict[str, Any], user_input: list) -> str:
    """
    Handle emergency incident reporting flow
    Path: Main > What happened? > Animal > Count > Location > [Context-specific] > Severity > Confirm
    """

    def rebuild_from_path():
        """Rebuild session data from user_input path"""
        data = session["data"].copy()

        # Level 2: Incident type
        if len(user_input) >= 2 and user_input[1] in INCIDENT_TYPES:
            data["incident_type"] = INCIDENT_TYPES[user_input[1]]["code"]
            data["incident_type_name"] = INCIDENT_TYPES[user_input[1]]["name"]

        # Level 3: Species (or "Other" marker)
        if len(user_input) >= 3:
            species_choice = user_input[2]
            if species_choice == "0":
                if len(user_input) >= 4:
                    data["species"] = user_input[3].title()
                    data["species_is_other"] = True
            elif species_choice in SPECIES:
                data["species"] = SPECIES[species_choice]
                data["species_is_other"] = False
            else:
                data["species"] = species_choice.title()
                data["species_is_other"] = True

        # Level 4/5: Count
        if len(user_input) > 2 and user_input[2] == "0":
            count_index = 4
        else:
            count_index = 3

        if len(user_input) > count_index:
            count_choice = user_input[count_index]
            if count_choice in COUNT_OPTIONS:
                data["animal_count"] = COUNT_OPTIONS[count_choice]

        # Level 5/6/7: Location
        location_index = count_index + 1
        if len(user_input) > location_index:
            location_input = user_input[location_index]

            if location_input == "0":
                if len(user_input) > location_index + 1:
                    data["location_name"] = user_input[location_index + 1].title()
                    data["location_is_other"] = True
            elif location_input in LOCATIONS:
                data["location_name"] = LOCATIONS[location_input]
                data["location_is_other"] = False
            else:
                data["location_name"] = location_input.title()
                data["location_is_other"] = True

        session["data"] = data
        return data

    rebuild_from_path()

    # Level 1: What happened?
    if len(user_input) == 1:
        response = "CON What happened?\n"
        response += "1. Crop Damage\n"
        response += "2. Livestock Attack\n"
        response += "3. Property Damage\n"
        response += "4. Human Injury/Threat\n"
        response += "5. Dangerous Animal"
        return response

    # Level 2: Which animal?
    if len(user_input) == 2:
        if user_input[1] not in INCIDENT_TYPES:
            return handle_invalid_input()

        response = "CON Which animal?\n"
        for key, value in SPECIES.items():
            response += f"{key}. {value}\n"
        response += "0. Other (type name)"
        return response

    # Level 3: Handle species selection
    if len(user_input) == 3:
        species_input = user_input[2]

        if species_input == "0":
            return "CON Enter animal name:\n(e.g., Wild Dog, Jackal)"
        elif species_input in SPECIES:
            session["data"]["species"] = SPECIES[species_input]
            session["data"]["species_is_other"] = False
        else:
            return handle_invalid_input()

        response = "CON How many?\n"
        response += "1. One\n"
        response += "2. 2-5\n"
        response += "3. 6-10\n"
        response += "4. More than 10"
        return response

    # Level 4: Handle free text species input
    if len(user_input) == 4 and user_input[2] == "0":
        species_input = user_input[3]
        is_valid, cleaned, error = validate_text_input(species_input, 'species')
        if not is_valid:
            return f"CON {error}\nTry again:"
        session["data"]["species"] = cleaned
        session["data"]["species_is_other"] = True

        response = "CON How many?\n"
        response += "1. One\n"
        response += "2. 2-5\n"
        response += "3. 6-10\n"
        response += "4. More than 10"
        return response

    # Level 4 or 5: Count selected
    count_level = 4 if user_input[2] != "0" else 5
    if len(user_input) == count_level:
        count_choice = user_input[-1]
        if count_choice not in COUNT_OPTIONS:
            return handle_invalid_input()

        session["data"]["animal_count"] = COUNT_OPTIONS[count_choice]

        response = "CON Where?\n"
        for key, value in LOCATIONS.items():
            response += f"{key}. {value}\n"
        response += "0. Other place"
        return response

    # Level 5 or 6: Location selection
    location_level = 5 if user_input[2] != "0" else 6

    if len(user_input) == location_level and user_input[-1] == "0":
        return "CON Enter location:\n(e.g., Near Sosian, Mutara Road)"

    if len(user_input) == location_level or (len(user_input) == location_level + 1 and user_input[-2] == "0"):
        if len(user_input) > location_level and user_input[-2] == "0":
            location_input = user_input[-1]
        else:
            location_input = user_input[-1]

        if location_input in LOCATIONS:
            session["data"]["location_name"] = LOCATIONS[location_input]
            session["data"]["location_is_other"] = False
        else:
            is_valid, cleaned, error = validate_text_input(location_input, 'location')
            if not is_valid:
                return f"CON {error}\nTry again:"
            session["data"]["location_name"] = cleaned
            session["data"]["location_is_other"] = True

        incident_type = session["data"].get("incident_type")

        if incident_type == "livestock_attack":
            response = "CON Livestock type?\n"
            response += "1. Cattle\n"
            response += "2. Goats\n"
            response += "3. Sheep\n"
            response += "4. Donkeys\n"
            response += "5. Chickens\n"
            response += "0. Other"
            return response
        elif incident_type == "property_damage":
            response = "CON What was damaged?\n"
            response += "1. Fence/Wall\n"
            response += "2. Building\n"
            response += "3. Water System\n"
            response += "4. Crops Storage\n"
            response += "0. Other"
            return response
        elif incident_type == "human_injury":
            response = "CON How many people?\n"
            response += "1. One person\n"
            response += "2. 2-3 people\n"
            response += "3. More than 3"
            return response
        elif incident_type == "dangerous_behavior":
            response = "CON People at risk now?\n"
            response += "1. Yes - immediate danger\n"
            response += "2. No - but concerning"
            return response
        else:  # crop_damage
            response = "CON How bad is the damage?\n"
            response += "1. Minor (small area)\n"
            response += "2. Moderate (significant)\n"
            response += "3. Severe (major loss)"
            return response

    # Calculate dynamic level based on "Other" usage
    incident_type = session["data"].get("incident_type")
    species_other_offset = 1 if user_input[2] == "0" else 0

    location_level = 5 if user_input[2] != "0" else 6
    location_other_offset = 0
    if len(user_input) > location_level and user_input[location_level - 1] == "0":
        location_other_offset = 1

    context_level = 6 + species_other_offset + location_other_offset

    # Handle "Other" for livestock/property
    if len(user_input) == context_level and user_input[-1] == "0":
        if incident_type == "livestock_attack":
            return "CON Enter livestock type:\n(e.g., Rabbits, Ducks)"
        elif incident_type == "property_damage":
            return "CON What was damaged:\n(e.g., Solar panel, Gate)"

    # Context-specific data
    if len(user_input) == context_level:
        choice = user_input[-1]

        if incident_type == "livestock_attack":
            if choice in LIVESTOCK_TYPES:
                session["data"]["details"] = {
                    "livestock_type": LIVESTOCK_TYPES[choice],
                    "livestock_is_other": False
                }
            else:
                is_valid, cleaned, error = validate_text_input(choice, 'livestock')
                if not is_valid:
                    return f"CON {error}\nTry again:"
                session["data"]["details"] = {
                    "livestock_type": cleaned,
                    "livestock_is_other": True
                }

            response = "CON How many affected?\n"
            response += "1. One\n"
            response += "2. 2-3\n"
            response += "3. 4-5\n"
            response += "4. More than 5"
            return response

        elif incident_type == "property_damage":
            if choice in PROPERTY_TYPES:
                session["data"]["details"] = {"property_type": PROPERTY_TYPES[choice]}
            else:
                is_valid, cleaned, error = validate_text_input(choice, 'property')
                if not is_valid:
                    return f"CON {error}\nTry again:"
                session["data"]["details"] = {"property_type": cleaned, "property_is_other": True}

            response = "CON How severe?\n"
            response += "1. Minor\n"
            response += "2. Moderate\n"
            response += "3. Severe"
            return response

        elif incident_type == "human_injury":
            people_map = {"1": "1", "2": "2-3", "3": "3+"}
            session["data"]["details"] = {"people_affected": people_map.get(choice, "1")}

            response = "CON Medical help needed?\n"
            response += "1. Yes - URGENT\n"
            response += "2. No"
            return response

        elif incident_type == "dangerous_behavior":
            session["data"]["details"] = {"people_at_risk": choice == "1"}
            session["data"]["severity"] = "severe" if choice == "1" else "moderate"
            return show_confirmation(session)

    # Additional data for livestock/human injury
    if len(user_input) == context_level + 1:
        choice = user_input[-1]

        if incident_type == "livestock_attack":
            count_map = {"1": "1", "2": "2-3", "3": "4-5", "4": "5+"}
            session["data"]["details"]["livestock_count"] = count_map.get(choice, "1")

            response = "CON How severe?\n"
            response += "1. Minor (injured)\n"
            response += "2. Moderate (some killed)\n"
            response += "3. Severe (many killed)"
            return response

        elif incident_type == "human_injury":
            session["data"]["details"]["medical_needed"] = (choice == "1")
            session["data"]["severity"] = "severe"
            return show_confirmation(session)

    # Severity level handling
    if incident_type == "crop_damage":
        severity_level = context_level
        if len(user_input) == severity_level:
            severity_input = user_input[-1]
            if severity_input not in SEVERITY_OPTIONS:
                return handle_invalid_input()
            session["data"]["severity"] = SEVERITY_OPTIONS[severity_input]
            return show_confirmation(session)

    elif incident_type in ["livestock_attack", "property_damage"]:
        severity_level = context_level + 2
        if len(user_input) == severity_level:
            severity_input = user_input[-1]
            if severity_input not in SEVERITY_OPTIONS:
                return handle_invalid_input()
            session["data"]["severity"] = SEVERITY_OPTIONS[severity_input]
            return show_confirmation(session)

    # Confirmation level
    if incident_type == "crop_damage":
        confirmation_level = context_level + 1
        if len(user_input) == confirmation_level:
            choice = user_input[-1]
            if choice == "1":
                return "SUBMIT_EMERGENCY"
            elif choice == "2":
                return "END Report cancelled."
            else:
                return handle_invalid_input()

    elif incident_type in ["livestock_attack", "property_damage"]:
        confirmation_level = context_level + 3
        if len(user_input) == confirmation_level:
            choice = user_input[-1]
            if choice == "1":
                return "SUBMIT_EMERGENCY"
            elif choice == "2":
                return "END Report cancelled."
            else:
                return handle_invalid_input()

    elif incident_type in ["human_injury", "dangerous_behavior"]:
        confirmation_level = context_level + 2
        if len(user_input) == confirmation_level:
            choice = user_input[-1]
            if choice == "1":
                return "SUBMIT_EMERGENCY"
            elif choice == "2":
                return "END Report cancelled."
            else:
                return handle_invalid_input()

    return handle_invalid_input()


def show_confirmation(session: Dict[str, Any]) -> str:
    """Show confirmation screen for emergency"""
    data = session["data"]

    response = "CON Confirm Report:\n\n"
    response += f"{data.get('incident_type_name')}\n"
    response += f"Animal: {data.get('species')}"

    count_str = data.get('animal_count', '?')
    if data.get('species_is_other'):
        response += f" * ({count_str})\n"
    else:
        response += f" ({count_str})\n"

    response += f"Location: {data.get('location_name')}"
    if data.get('location_is_other'):
        response += " *\n"
    else:
        response += "\n"

    details = data.get('details', {})
    if 'livestock_type' in details:
        response += f"Livestock: {details['livestock_type']} ({details.get('livestock_count', '?')})\n"
    elif 'property_type' in details:
        response += f"Damaged: {details['property_type']}\n"
    elif 'people_affected' in details:
        response += f"People: {details['people_affected']}\n"

    if data.get('severity'):
        response += f"Severity: {data['severity'].title()}\n"

    response += "\n1. Submit Report\n"
    response += "2. Cancel"

    return response


def handle_wildlife_sighting(session: Dict[str, Any], user_input: list) -> str:
    """Handle wildlife sighting flow"""

    # Level 1: Which animal?
    if len(user_input) == 1:
        response = "CON Which animal?\n"
        for key, value in SPECIES.items():
            response += f"{key}. {value}\n"
        response += "0. Other"
        return response

    # Level 1b: Other animal
    if len(user_input) == 2 and user_input[1] == "0":
        return "CON Enter animal name:"

    # Level 2: Animal selected, ask count
    if len(user_input) == 2:
        if user_input[1] in SPECIES:
            session["data"]["species"] = SPECIES[user_input[1]]
            session["data"]["species_is_other"] = False
        else:
            is_valid, cleaned, error = validate_text_input(user_input[1], 'species')
            if not is_valid:
                return f"CON {error}\nTry again:"
            session["data"]["species"] = cleaned
            session["data"]["species_is_other"] = True

        response = "CON How many?\n"
        response += "1. One\n"
        response += "2. 2-5\n"
        response += "3. 6-10\n"
        response += "4. More than 10"
        return response

    # Level 3: Count selected, ask location
    if len(user_input) == 3:
        if user_input[2] not in COUNT_OPTIONS:
            return handle_invalid_input()

        session["data"]["animal_count"] = COUNT_OPTIONS[user_input[2]]

        response = "CON Where?\n"
        for key, value in LOCATIONS.items():
            response += f"{key}. {value}\n"
        response += "0. Other place"
        return response

    # Level 3b: Other location
    if len(user_input) == 4 and user_input[3] == "0":
        return "CON Enter location:"

    # Level 4: Location selected, ask behavior
    if len(user_input) == 4:
        if user_input[3] in LOCATIONS:
            session["data"]["location_name"] = LOCATIONS[user_input[3]]
            session["data"]["location_is_other"] = False
        else:
            is_valid, cleaned, error = validate_text_input(user_input[3], 'location')
            if not is_valid:
                return f"CON {error}\nTry again:"
            session["data"]["location_name"] = cleaned
            session["data"]["location_is_other"] = True

        response = "CON What doing?\n"
        response += "1. Grazing/Feeding\n"
        response += "2. Moving/Walking\n"
        response += "3. Resting\n"
        response += "4. Near water\n"
        response += "5. Unknown"
        return response

    # Level 5: Behavior selected, ask weather
    if len(user_input) == 5:
        if user_input[4] not in BEHAVIOR_OPTIONS:
            return handle_invalid_input()

        session["data"]["behavior"] = BEHAVIOR_OPTIONS[user_input[4]]

        response = "CON Weather now?\n"
        response += "1. Clear/Sunny\n"
        response += "2. Rainy\n"
        response += "3. Cloudy\n"
        response += "4. Skip"
        return response

    # Level 6: Weather selected, show confirmation
    if len(user_input) == 6:
        weather_choice = user_input[5]
        if weather_choice not in WEATHER_OPTIONS:
            return handle_invalid_input()

        weather = WEATHER_OPTIONS[weather_choice]
        session["data"]["weather"] = None if weather == "skip" else weather

        data = session["data"]
        response = "CON Confirm Sighting:\n\n"
        response += f"{data.get('species')} ({data.get('animal_count')})\n"
        response += f"Location: {data.get('location_name')}\n"
        response += f"Behavior: {data.get('behavior').title()}\n"
        if data.get('weather'):
            response += f"Weather: {data['weather'].title()}\n"

        response += "\n1. Submit\n"
        response += "2. Cancel"
        return response

    # Level 7: Confirmation
    if len(user_input) == 7:
        if user_input[6] == "1":
            return "SUBMIT_SIGHTING"
        else:
            return "END Sighting cancelled."

    return handle_invalid_input()


def handle_past_incident(session: Dict[str, Any], user_input: list) -> str:
    """Handle past incident reporting"""

    # Level 1: When did it happen?
    if len(user_input) == 1:
        response = "CON When did this happen?\n"
        response += "1. Yesterday\n"
        response += "2. 2-7 days ago\n"
        response += "3. Over a week ago"
        return response

    # Level 2: Time selected
    if len(user_input) == 2:
        when_choice = user_input[1]

        if when_choice not in ["1", "2", "3"]:
            return handle_invalid_input()

        when_map = {"1": "yesterday", "2": "2-7_days", "3": "over_week"}
        session["data"]["occurred_when"] = when_map[when_choice]
        session["data"]["report_type"] = "past_incident"

        response = "CON What happened?\n"
        response += "1. Crop Damage\n"
        response += "2. Livestock Attack\n"
        response += "3. Property Damage\n"
        response += "4. Human Injury/Threat\n"
        response += "5. Dangerous Animal"
        return response

    # Level 3+: Use emergency handler
    adjusted_input = ["1"] + user_input[2:]
    response = handle_emergency_incident(session, adjusted_input)

    if "Submit Report" in response or "END" in response:
        session["data"]["report_type"] = "past_incident"

    return response
