"""
LLM Service for fallback extraction
Uses Hugging Face models when rule-based extraction fails
Options: Local model or Hugging Face Inference API
"""
import json
import logging
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMExtractionResult:
    """Result from LLM extraction"""
    species: Optional[str] = None
    incident_type: Optional[str] = None
    location: Optional[str] = None
    animal_count: Optional[str] = None
    severity: Optional[str] = None
    confidence: int = 0
    success: bool = False
    error: Optional[str] = None


# Valid values for validation
VALID_SPECIES = [
    "elephant", "lion", "leopard", "buffalo", "hyena", "hippo",
    "crocodile", "snake", "wild_dog", "cheetah", "rhino", "baboon",
    "monkey", "warthog", "jackal", "zebra", "giraffe"
]

VALID_INCIDENTS = [
    "crop_damage", "livestock_attack", "property_damage",
    "human_injury", "dangerous_animal", "sighting"
]

VALID_SEVERITY = ["minor", "moderate", "severe"]
VALID_COUNTS = ["1", "2-5", "6-10", "10+"]


# Prompt for text generation models
EXTRACTION_PROMPT = """Extract wildlife incident info from this SMS and return JSON only.

SMS: "{message}"

Return JSON with: species, incident_type, location, animal_count, severity, confidence (0-100)
Valid species: elephant, lion, leopard, buffalo, hyena, hippo, crocodile, snake, wild_dog
Valid incident_type: crop_damage, livestock_attack, property_damage, human_injury, dangerous_animal, sighting
Valid severity: minor, moderate, severe
Use null if unknown.

JSON:"""


class HuggingFaceExtractor:
    """
    Hugging Face-based extractor using Inference API or local model
    """

    def __init__(self):
        self.api_token = getattr(settings, 'hf_api_token', None)
        self.model_id = getattr(settings, 'hf_model_id', 'google/flan-t5-small')
        self._pipeline = None

    def _get_pipeline(self):
        """Lazy load the local pipeline"""
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline(
                    "text2text-generation",
                    model=self.model_id,
                    max_length=200
                )
                logger.info(f"Loaded local model: {self.model_id}")
            except Exception as e:
                logger.error(f"Failed to load local model: {e}")
                raise
        return self._pipeline

    async def extract_with_api(self, message: str) -> LLMExtractionResult:
        """
        Use Hugging Face Inference API for extraction

        Requires HF_API_TOKEN environment variable
        """
        if not self.api_token:
            return LLMExtractionResult(
                success=False,
                error="HF_API_TOKEN not configured"
            )

        try:
            import httpx

            # Use a small, fast model
            api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"

            prompt = EXTRACTION_PROMPT.format(message=message)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json={"inputs": prompt, "parameters": {"max_length": 200}},
                    timeout=30.0
                )

                if response.status_code != 200:
                    return LLMExtractionResult(
                        success=False,
                        error=f"API error: {response.status_code}"
                    )

                result = response.json()

                # Parse the generated text
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get("generated_text", "")
                    return self._parse_response(generated_text)

                return LLMExtractionResult(success=False, error="Empty response")

        except ImportError:
            return LLMExtractionResult(
                success=False,
                error="httpx not installed for API calls"
            )
        except Exception as e:
            logger.error(f"HF API extraction failed: {e}")
            return LLMExtractionResult(success=False, error=str(e))

    def extract_with_local(self, message: str) -> LLMExtractionResult:
        """
        Use local Hugging Face model for extraction

        Requires transformers and torch installed
        """
        try:
            pipe = self._get_pipeline()
            prompt = EXTRACTION_PROMPT.format(message=message)

            result = pipe(prompt)[0]["generated_text"]
            return self._parse_response(result)

        except ImportError as e:
            return LLMExtractionResult(
                success=False,
                error=f"transformers not installed: {e}"
            )
        except Exception as e:
            logger.error(f"Local model extraction failed: {e}")
            return LLMExtractionResult(success=False, error=str(e))

    def _parse_response(self, text: str) -> LLMExtractionResult:
        """Parse model response into structured data"""
        try:
            # Try to extract JSON from response
            # Handle various formats the model might return

            # Clean up the text
            text = text.strip()

            # Try direct JSON parse
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Try to find JSON in the text
                json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    # Try to parse key-value pairs
                    data = self._parse_key_value(text)

            # Validate and normalize
            return LLMExtractionResult(
                species=self._validate_species(data.get("species")),
                incident_type=self._validate_incident(data.get("incident_type")),
                location=data.get("location") if data.get("location") else None,
                animal_count=self._validate_count(data.get("animal_count")),
                severity=self._validate_severity(data.get("severity")),
                confidence=min(100, max(0, int(data.get("confidence", 50)))),
                success=True
            )

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response was: {text}")
            return LLMExtractionResult(success=False, error=f"Parse error: {e}")

    def _parse_key_value(self, text: str) -> Dict[str, Any]:
        """Parse key-value pairs from text when JSON fails"""
        data = {}
        patterns = [
            (r'species[:\s]+([a-z_]+)', 'species'),
            (r'incident[_\s]?type[:\s]+([a-z_]+)', 'incident_type'),
            (r'location[:\s]+([^,\n]+)', 'location'),
            (r'animal[_\s]?count[:\s]+([0-9\-\+]+)', 'animal_count'),
            (r'severity[:\s]+([a-z]+)', 'severity'),
            (r'confidence[:\s]+(\d+)', 'confidence'),
        ]

        text_lower = text.lower()
        for pattern, key in patterns:
            match = re.search(pattern, text_lower)
            if match:
                data[key] = match.group(1).strip()

        return data

    def _validate_species(self, value: Any) -> Optional[str]:
        """Validate species value"""
        if not value or value == "null":
            return None
        value = str(value).lower().strip()
        return value if value in VALID_SPECIES else None

    def _validate_incident(self, value: Any) -> Optional[str]:
        """Validate incident type"""
        if not value or value == "null":
            return None
        value = str(value).lower().strip().replace(" ", "_")
        return value if value in VALID_INCIDENTS else None

    def _validate_severity(self, value: Any) -> Optional[str]:
        """Validate severity"""
        if not value or value == "null":
            return None
        value = str(value).lower().strip()
        return value if value in VALID_SEVERITY else None

    def _validate_count(self, value: Any) -> Optional[str]:
        """Validate animal count"""
        if not value or value == "null":
            return None
        value = str(value).strip()
        return value if value in VALID_COUNTS else None


# Global extractor instance
_hf_extractor: Optional[HuggingFaceExtractor] = None


def get_hf_extractor() -> HuggingFaceExtractor:
    """Get HuggingFace extractor instance"""
    global _hf_extractor
    if _hf_extractor is None:
        _hf_extractor = HuggingFaceExtractor()
    return _hf_extractor


async def extract_with_llm(message: str, use_api: bool = True) -> LLMExtractionResult:
    """
    Extract using Hugging Face model

    Args:
        message: SMS text to extract from
        use_api: If True, use HF Inference API. If False, use local model.

    Returns:
        LLMExtractionResult with extracted data
    """
    extractor = get_hf_extractor()

    if use_api:
        return await extractor.extract_with_api(message)
    else:
        return extractor.extract_with_local(message)


def extract_with_llm_sync(message: str) -> LLMExtractionResult:
    """
    Synchronous extraction using local model only

    Args:
        message: SMS text to extract from

    Returns:
        LLMExtractionResult with extracted data
    """
    extractor = get_hf_extractor()
    return extractor.extract_with_local(message)


def merge_llm_result(
    rule_based_result: Dict[str, Any],
    llm_result: LLMExtractionResult
) -> Dict[str, Any]:
    """
    Merge LLM extraction results with rule-based results

    Prefer LLM results for fields where rule-based had low confidence

    Args:
        rule_based_result: Result from rule-based extraction
        llm_result: Result from LLM extraction

    Returns:
        Merged result dictionary
    """
    if not llm_result.success:
        return rule_based_result

    merged = rule_based_result.copy()

    # Fields to potentially update
    fields = ["species", "incident_type", "location", "animal_count", "severity"]

    for field in fields:
        rule_conf = rule_based_result.get(field, {}).get("confidence", 0)
        llm_value = getattr(llm_result, field)

        # Use LLM value if rule-based confidence is low and LLM has a value
        if llm_value and rule_conf < 0.5:
            merged[field] = {
                "value": llm_value,
                "confidence": llm_result.confidence / 100,
                "method": "llm"
            }

    # Update overall confidence
    if llm_result.confidence > merged.get("overall_confidence", 0) * 100:
        merged["overall_confidence"] = llm_result.confidence / 100

    merged["extraction_method"] = "hybrid"

    return merged
