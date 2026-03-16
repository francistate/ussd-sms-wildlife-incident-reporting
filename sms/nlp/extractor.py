"""
NLP Extractor for SMS messages
Extracts structured incident data from free-form text
"""
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from rapidfuzz import fuzz, process
import logging

from nlp.keywords import get_keyword_data, KeywordData

logger = logging.getLogger(__name__)


@dataclass
class FieldExtraction:
    """Result of extracting a single field"""
    value: Optional[str] = None
    confidence: float = 0.0
    method: str = "none"  # exact, fuzzy, pattern


@dataclass
class ExtractionResult:
    """Complete extraction result from SMS"""
    species: FieldExtraction = field(default_factory=FieldExtraction)
    incident_type: FieldExtraction = field(default_factory=FieldExtraction)
    location: FieldExtraction = field(default_factory=FieldExtraction)
    animal_count: FieldExtraction = field(default_factory=FieldExtraction)
    severity: FieldExtraction = field(default_factory=FieldExtraction)

    overall_confidence: float = 0.0
    extraction_method: str = "rule_based"
    needs_clarification: bool = False
    clarification_field: Optional[str] = None
    raw_text: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return {
            "species": {"value": self.species.value, "confidence": self.species.confidence},
            "incident_type": {"value": self.incident_type.value, "confidence": self.incident_type.confidence},
            "location": {"value": self.location.value, "confidence": self.location.confidence},
            "animal_count": {"value": self.animal_count.value, "confidence": self.animal_count.confidence},
            "severity": {"value": self.severity.value, "confidence": self.severity.confidence},
            "overall_confidence": self.overall_confidence,
            "extraction_method": self.extraction_method,
            "needs_clarification": self.needs_clarification,
            "clarification_field": self.clarification_field
        }


class SMSExtractor:
    """Extract structured incident data from free-form SMS text"""

    # Minimum fuzzy match score to consider a match
    FUZZY_THRESHOLD = 70

    def __init__(self):
        self.keywords = get_keyword_data()

    def extract(self, sms_text: str) -> ExtractionResult:
        """
        Main extraction method

        Args:
            sms_text: Raw SMS text

        Returns:
            ExtractionResult with extracted fields and confidence scores
        """
        text_lower = sms_text.lower().strip()
        text_normalized = self._normalize_text(text_lower)

        result = ExtractionResult(raw_text=sms_text)

        # Extract each field
        result.species = self._extract_species(text_normalized)
        result.incident_type = self._extract_incident_type(text_normalized)
        result.location = self._extract_location(text_normalized, sms_text)
        result.animal_count = self._extract_count(text_normalized)
        result.severity = self._extract_severity(text_normalized, result)

        # Calculate overall confidence
        result.overall_confidence = self._calculate_overall_confidence(result)

        # Determine if clarification needed
        result.needs_clarification, result.clarification_field = self._needs_clarification(result)

        logger.info(f"Extraction complete. Confidence: {result.overall_confidence:.2f}")
        return result

    def _normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove punctuation except apostrophes
        text = re.sub(r"[^\w\s']", " ", text)
        return text

    def _extract_species(self, text: str) -> FieldExtraction:
        """Extract animal species from text"""
        # First try exact matches
        all_keywords = self.keywords.get_all_species_keywords()

        # Sort by length (longer matches first) to catch "wild dog" before "dog"
        for keyword in sorted(all_keywords, key=len, reverse=True):
            if keyword in text:
                species = self.keywords.species_from_keyword(keyword)
                return FieldExtraction(
                    value=species,
                    confidence=1.0,
                    method="exact"
                )

        # Try fuzzy matching
        words = text.split()
        # Also try bigrams for multi-word species like "wild dog"
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        candidates = words + bigrams

        best_match = None
        best_score = 0

        for candidate in candidates:
            match = process.extractOne(
                candidate,
                all_keywords,
                scorer=fuzz.ratio,
                score_cutoff=self.FUZZY_THRESHOLD
            )
            if match and match[1] > best_score:
                best_score = match[1]
                best_match = match[0]

        if best_match:
            species = self.keywords.species_from_keyword(best_match)
            return FieldExtraction(
                value=species,
                confidence=best_score / 100,
                method="fuzzy"
            )

        return FieldExtraction()

    def _extract_incident_type(self, text: str) -> FieldExtraction:
        """Extract incident type from text"""
        incident_scores = {}

        # Check each incident type's keywords
        for incident_type, data in self.keywords.incidents.items():
            score = 0
            matches = 0

            all_keywords = data.get("keywords", []) + data.get("sw", [])

            for keyword in all_keywords:
                if keyword.lower() in text:
                    # Weight longer keyword matches higher
                    weight = len(keyword.split())
                    score += weight
                    matches += 1

            if matches > 0:
                # Normalize score
                normalized = min(1.0, score / 3)  # Cap at 3 keyword matches
                incident_scores[incident_type] = normalized

        if incident_scores:
            best_type = max(incident_scores, key=incident_scores.get)
            return FieldExtraction(
                value=best_type,
                confidence=incident_scores[best_type],
                method="exact"
            )

        return FieldExtraction()

    def _extract_location(self, text_lower: str, original_text: str) -> FieldExtraction:
        """Extract location from text"""
        known_locations = self.keywords.get_known_locations()
        indicators = self.keywords.get_location_indicators()

        # Try exact match with known locations
        for location in known_locations:
            if location.lower() in text_lower:
                return FieldExtraction(
                    value=location.title(),
                    confidence=1.0,
                    method="exact"
                )

        # Try fuzzy matching with known locations
        words = text_lower.split()
        for word in words:
            if len(word) >= 4:  # Skip short words
                match = process.extractOne(
                    word,
                    known_locations,
                    scorer=fuzz.ratio,
                    score_cutoff=80  # Higher threshold for locations
                )
                if match:
                    return FieldExtraction(
                        value=match[0].title(),
                        confidence=match[1] / 100,
                        method="fuzzy"
                    )

        # Try to find location after indicators
        for indicator in indicators:
            pattern = rf"{indicator}\s+([a-zA-Z\s]+?)(?:\s|$|,|\.)"
            match = re.search(pattern, text_lower)
            if match:
                location_text = match.group(1).strip()
                # Clean up and validate
                if len(location_text) >= 3 and len(location_text) <= 50:
                    return FieldExtraction(
                        value=location_text.title(),
                        confidence=0.6,
                        method="pattern"
                    )

        return FieldExtraction()

    def _extract_count(self, text: str) -> FieldExtraction:
        """Extract animal count from text"""
        count_mapping = self.keywords.get_count_mapping()

        # Try numeric patterns first
        number_match = re.search(r'\b(\d+)\b', text)
        if number_match:
            num = int(number_match.group(1))
            if num == 1:
                count_range = "1"
            elif num <= 5:
                count_range = "2-5"
            elif num <= 10:
                count_range = "6-10"
            else:
                count_range = "10+"
            return FieldExtraction(value=count_range, confidence=0.95, method="pattern")

        # Try word matches
        for word, count_range in count_mapping.items():
            if word in text:
                return FieldExtraction(
                    value=count_range,
                    confidence=0.8,
                    method="exact"
                )

        # Default to unknown
        return FieldExtraction(value="1", confidence=0.3, method="default")

    def _extract_severity(self, text: str, result: ExtractionResult) -> FieldExtraction:
        """Extract severity based on text and other extracted data"""
        severity_data = self.keywords.severity

        # Check for severe indicators
        for keyword in severity_data.get("severe", {}).get("keywords", []):
            if keyword in text:
                return FieldExtraction(value="severe", confidence=0.9, method="exact")

        for keyword in severity_data.get("severe", {}).get("sw", []):
            if keyword in text:
                return FieldExtraction(value="severe", confidence=0.9, method="exact")

        # Human injury is always severe
        if result.incident_type.value == "human_injury":
            return FieldExtraction(value="severe", confidence=1.0, method="inferred")

        # Check for moderate indicators
        for keyword in severity_data.get("moderate", {}).get("keywords", []):
            if keyword in text:
                return FieldExtraction(value="moderate", confidence=0.7, method="exact")

        # Check count for severity inference
        if result.animal_count.value in ["6-10", "10+"]:
            return FieldExtraction(value="moderate", confidence=0.6, method="inferred")

        # Default based on incident type
        if result.incident_type.value in ["livestock_attack", "dangerous_animal"]:
            return FieldExtraction(value="moderate", confidence=0.5, method="default")

        return FieldExtraction(value="minor", confidence=0.4, method="default")

    def _calculate_overall_confidence(self, result: ExtractionResult) -> float:
        """Calculate overall extraction confidence"""
        # Weight different fields
        weights = {
            "species": 0.25,
            "incident_type": 0.35,
            "location": 0.25,
            "severity": 0.10,
            "animal_count": 0.05
        }

        total = 0
        total += result.species.confidence * weights["species"]
        total += result.incident_type.confidence * weights["incident_type"]
        total += result.location.confidence * weights["location"]
        total += result.severity.confidence * weights["severity"]
        total += result.animal_count.confidence * weights["animal_count"]

        # Bonus for having all critical fields
        if all([
            result.species.value,
            result.incident_type.value,
            result.location.value
        ]):
            total = min(1.0, total + 0.1)

        return round(total, 3)

    def _needs_clarification(self, result: ExtractionResult) -> Tuple[bool, Optional[str]]:
        """Determine if clarification is needed and which field"""
        # If overall confidence is too low
        if result.overall_confidence < 0.3:
            # Find the most problematic field
            if not result.incident_type.value or result.incident_type.confidence < 0.3:
                return True, "incident_type"
            if not result.species.value or result.species.confidence < 0.3:
                return True, "species"
            if not result.location.value or result.location.confidence < 0.3:
                return True, "location"

        # Missing critical field with low confidence
        if not result.species.value and result.incident_type.value != "sighting":
            return True, "species"

        return False, None


# Global extractor instance
_extractor = None


def get_extractor() -> SMSExtractor:
    """Get cached extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = SMSExtractor()
    return _extractor


def extract_from_sms(sms_text: str) -> ExtractionResult:
    """Convenience function to extract from SMS text"""
    return get_extractor().extract(sms_text)
