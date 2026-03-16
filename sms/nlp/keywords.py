"""
Keyword data loader for NLP extraction
"""
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Base path for keyword files
KEYWORDS_DIR = Path(__file__).parent.parent / "data" / "keywords"


def load_json(filename: str) -> Dict[str, Any]:
    """Load JSON file from keywords directory"""
    filepath = KEYWORDS_DIR / filename
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Keyword file not found: {filepath}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return {}


class KeywordData:
    """Container for all keyword data"""

    def __init__(self):
        self.species = load_json("species.json")
        self.incidents = load_json("incidents.json")
        self.locations = load_json("locations.json")
        self.severity = load_json("severity.json")

        # Build flat keyword lists for quick lookup
        self._species_flat = self._flatten_species()
        self._incident_flat = self._flatten_incidents()

    def _flatten_species(self) -> Dict[str, str]:
        """Create flat mapping: keyword -> species_name"""
        flat = {}
        for species_name, languages in self.species.items():
            for lang, keywords in languages.items():
                for keyword in keywords:
                    flat[keyword.lower()] = species_name
        return flat

    def _flatten_incidents(self) -> Dict[str, str]:
        """Create flat mapping: keyword -> incident_type"""
        flat = {}
        for incident_type, data in self.incidents.items():
            for keyword in data.get("keywords", []):
                flat[keyword.lower()] = incident_type
            for keyword in data.get("sw", []):
                flat[keyword.lower()] = incident_type
        return flat

    def get_all_species_keywords(self) -> List[str]:
        """Get all species keywords for fuzzy matching"""
        return list(self._species_flat.keys())

    def get_all_incident_keywords(self) -> List[str]:
        """Get all incident keywords"""
        return list(self._incident_flat.keys())

    def get_known_locations(self) -> List[str]:
        """Get known location names"""
        return self.locations.get("known_locations", [])

    def get_location_indicators(self) -> List[str]:
        """Get location indicator words"""
        indicators = self.locations.get("location_indicators", [])
        indicators.extend(self.locations.get("swahili_indicators", []))
        return indicators

    def species_from_keyword(self, keyword: str) -> str:
        """Get species name from keyword"""
        return self._species_flat.get(keyword.lower())

    def incident_from_keyword(self, keyword: str) -> str:
        """Get incident type from keyword"""
        return self._incident_flat.get(keyword.lower())

    def get_incident_priority_boost(self, incident_type: str) -> float:
        """Get priority boost for incident type"""
        return self.incidents.get(incident_type, {}).get("priority_boost", 0)

    def get_severity_score(self, severity: str) -> float:
        """Get severity score"""
        return self.severity.get(severity, {}).get("score", 0.5)

    def get_count_mapping(self) -> Dict[str, str]:
        """Get count word to range mapping"""
        return self.severity.get("count_patterns", {})


# Global instance
_keyword_data = None


def get_keyword_data() -> KeywordData:
    """Get cached keyword data instance"""
    global _keyword_data
    if _keyword_data is None:
        _keyword_data = KeywordData()
    return _keyword_data
