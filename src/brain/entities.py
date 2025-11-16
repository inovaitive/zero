"""
Entity Extraction for ZERO Assistant.

This module extracts structured entities from user input:
- Locations (cities, countries)
- Dates and times
- Durations (for timers)
- App names
- Numbers and quantities
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Try to import dependencies
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    logger.warning("dateparser not available - using basic date parsing")


@dataclass
class Entity:
    """Represents an extracted entity."""

    entity_type: str  # 'location', 'time', 'duration', 'app_name', etc.
    value: Any  # The extracted value
    text: str  # Original text
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityExtractionResult:
    """Result of entity extraction."""

    entities: List[Entity]
    raw_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_entity(self, entity_type: str) -> Optional[Entity]:
        """Get the first entity of a specific type."""
        for entity in self.entities:
            if entity.entity_type == entity_type:
                return entity
        return None

    def get_entities(self, entity_type: str) -> List[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self.entities if e.entity_type == entity_type]

    def has_entity(self, entity_type: str) -> bool:
        """Check if an entity type exists."""
        return any(e.entity_type == entity_type for e in self.entities)


class EntityExtractor:
    """
    Extracts entities from user input using multiple methods:
    1. spaCy Named Entity Recognition
    2. Custom regex patterns
    3. Context-aware extraction
    """

    def __init__(
        self,
        use_spacy: bool = True,
        spacy_model: str = "en_core_web_sm",
    ):
        """
        Initialize entity extractor.

        Args:
            use_spacy: Whether to use spaCy for NER
            spacy_model: spaCy model name
        """
        self.nlp = None
        if use_spacy and SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load(spacy_model)
                logger.info(f"Loaded spaCy model for entity extraction: {spacy_model}")
            except Exception as e:
                logger.warning(f"spaCy model '{spacy_model}' could not be loaded ({e}) - using custom extractors only")

        # Common app name mappings
        self.app_aliases = {
            'chrome': 'Google Chrome',
            'browser': 'Google Chrome',
            'safari': 'Safari',
            'firefox': 'Firefox',
            'code': 'Visual Studio Code',
            'vscode': 'Visual Studio Code',
            'editor': 'Visual Studio Code',
            'music': 'Spotify',
            'spotify': 'Spotify',
            'mail': 'Mail',
            'email': 'Mail',
            'notes': 'Notes',
            'terminal': 'Terminal',
            'slack': 'Slack',
            'discord': 'Discord',
            'zoom': 'Zoom',
        }

        logger.info("Entity extractor initialized")

    def extract(self, text: str, intent_type: str = None) -> EntityExtractionResult:
        """
        Extract entities from text.

        Args:
            text: User input text
            intent_type: Optional intent type to guide extraction

        Returns:
            EntityExtractionResult with extracted entities
        """
        entities = []

        # Extract using different methods
        entities.extend(self._extract_with_spacy(text))
        entities.extend(self._extract_locations(text))
        entities.extend(self._extract_dates_times(text))
        entities.extend(self._extract_durations(text))
        entities.extend(self._extract_app_names(text))
        entities.extend(self._extract_numbers(text))
        entities.extend(self._extract_weather_specific(text))

        # Remove duplicates (keep highest confidence)
        entities = self._deduplicate_entities(entities)

        return EntityExtractionResult(
            entities=entities,
            raw_text=text,
            metadata={'intent_type': intent_type}
        )

    def _extract_with_spacy(self, text: str) -> List[Entity]:
        """Extract entities using spaCy NER."""
        if not self.nlp:
            return []

        entities = []
        doc = self.nlp(text)

        for ent in doc.ents:
            entity_type = self._map_spacy_label(ent.label_)
            if entity_type:
                entities.append(Entity(
                    entity_type=entity_type,
                    value=ent.text,
                    text=ent.text,
                    confidence=0.85,
                    metadata={'spacy_label': ent.label_}
                ))

        return entities

    def _map_spacy_label(self, label: str) -> Optional[str]:
        """Map spaCy NER labels to our entity types."""
        mapping = {
            'GPE': 'location',  # Geopolitical entity
            'LOC': 'location',  # Location
            'DATE': 'date',
            'TIME': 'time',
            'CARDINAL': 'number',
            'QUANTITY': 'number',
            'PERSON': 'person',
            'ORG': 'organization',
        }
        return mapping.get(label)

    def _extract_locations(self, text: str) -> List[Entity]:
        """Extract location entities (cities, countries)."""
        entities = []

        # Common location patterns
        patterns = [
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "in New York"
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "at London"
            r'\bfor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "for Paris"
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                location = match.group(1)
                entities.append(Entity(
                    entity_type='location',
                    value=location,
                    text=location,
                    confidence=0.7,
                    metadata={'method': 'regex'}
                ))

        return entities

    def _extract_dates_times(self, text: str) -> List[Entity]:
        """Extract date and time entities."""
        entities = []

        # Use dateparser if available
        if DATEPARSER_AVAILABLE:
            # Common time expressions
            time_expressions = [
                'tomorrow', 'today', 'tonight', 'yesterday',
                'next week', 'next month', 'this week', 'this weekend',
                'in the morning', 'in the afternoon', 'in the evening',
            ]

            text_lower = text.lower()
            for expr in time_expressions:
                if expr in text_lower:
                    parsed = dateparser.parse(expr)
                    if parsed:
                        entities.append(Entity(
                            entity_type='time',
                            value=parsed,
                            text=expr,
                            confidence=0.9,
                            metadata={'expression': expr}
                        ))

        # Pattern-based time extraction
        time_patterns = {
            r'\btomorrow\b': timedelta(days=1),
            r'\btoday\b': timedelta(days=0),
            r'\bthis\s+week\b': timedelta(days=7),
            r'\bnext\s+week\b': timedelta(weeks=1),
        }

        for pattern, delta in time_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                future_time = datetime.now() + delta
                entities.append(Entity(
                    entity_type='date',
                    value=future_time,
                    text=re.search(pattern, text, re.IGNORECASE).group(0),
                    confidence=0.8,
                    metadata={'delta': str(delta)}
                ))

        return entities

    def _extract_durations(self, text: str) -> List[Entity]:
        """Extract duration entities (for timers)."""
        entities = []

        # Duration patterns: "5 minutes", "1 hour 30 minutes", "90 seconds"
        patterns = [
            # Hours and minutes
            r'(\d+)\s*(?:hour|hr)s?\s*(?:and\s*)?(\d+)?\s*(?:minute|min)s?',
            # Just hours
            r'(\d+)\s*(?:hour|hr)s?',
            # Just minutes
            r'(\d+)\s*(?:minute|min)s?',
            # Just seconds
            r'(\d+)\s*(?:second|sec)s?',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                duration_seconds = self._parse_duration(match.group(0))
                if duration_seconds:
                    entities.append(Entity(
                        entity_type='duration',
                        value=duration_seconds,
                        text=match.group(0),
                        confidence=0.95,
                        metadata={'seconds': duration_seconds}
                    ))

        return entities

    def _parse_duration(self, duration_text: str) -> Optional[int]:
        """Parse duration text into seconds."""
        total_seconds = 0

        # Hours
        hour_match = re.search(r'(\d+)\s*(?:hour|hr)s?', duration_text, re.IGNORECASE)
        if hour_match:
            total_seconds += int(hour_match.group(1)) * 3600

        # Minutes
        min_match = re.search(r'(\d+)\s*(?:minute|min)s?', duration_text, re.IGNORECASE)
        if min_match:
            total_seconds += int(min_match.group(1)) * 60

        # Seconds
        sec_match = re.search(r'(\d+)\s*(?:second|sec)s?', duration_text, re.IGNORECASE)
        if sec_match:
            total_seconds += int(sec_match.group(1))

        return total_seconds if total_seconds > 0 else None

    def _extract_app_names(self, text: str) -> List[Entity]:
        """Extract application names."""
        entities = []

        # Check for known app aliases
        text_lower = text.lower()
        for alias, app_name in self.app_aliases.items():
            # Word boundary pattern
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, text_lower):
                entities.append(Entity(
                    entity_type='app_name',
                    value=app_name,
                    text=alias,
                    confidence=0.9,
                    metadata={'alias': alias, 'canonical_name': app_name}
                ))

        # Extract capitalized words after action verbs (likely app names)
        action_verbs = ['open', 'launch', 'start', 'run', 'close', 'quit', 'exit', 'kill', 'switch to']
        for verb in action_verbs:
            pattern = rf'\b{verb}\s+([A-Z][a-zA-Z0-9\s]*?)(?:\s|$)'
            matches = re.finditer(pattern, text)
            for match in matches:
                app_name = match.group(1).strip()
                if app_name and len(app_name) > 1:
                    entities.append(Entity(
                        entity_type='app_name',
                        value=app_name,
                        text=app_name,
                        confidence=0.7,
                        metadata={'method': 'pattern'}
                    ))

        return entities

    def _extract_numbers(self, text: str) -> List[Entity]:
        """Extract numeric entities."""
        entities = []

        # Find all numbers
        pattern = r'\b(\d+(?:\.\d+)?)\b'
        matches = re.finditer(pattern, text)

        for match in matches:
            number_text = match.group(1)
            number_value = float(number_text) if '.' in number_text else int(number_text)

            entities.append(Entity(
                entity_type='number',
                value=number_value,
                text=number_text,
                confidence=0.95,
                metadata={'is_float': '.' in number_text}
            ))

        return entities

    def _extract_weather_specific(self, text: str) -> List[Entity]:
        """Extract weather-specific entities (units, conditions, etc.)."""
        entities = []

        # Temperature units
        if re.search(r'\b(celsius|fahrenheit|°c|°f)\b', text, re.IGNORECASE):
            unit_match = re.search(r'\b(celsius|fahrenheit|°c|°f)\b', text, re.IGNORECASE)
            if unit_match:
                unit_text = unit_match.group(1).lower()
                if 'c' in unit_text or 'celsius' in unit_text:
                    entities.append(Entity(
                        entity_type='temperature_unit',
                        value='metric',
                        text=unit_text,
                        confidence=0.95,
                        metadata={'unit': 'celsius'}
                    ))
                elif 'f' in unit_text or 'fahrenheit' in unit_text:
                    entities.append(Entity(
                        entity_type='temperature_unit',
                        value='imperial',
                        text=unit_text,
                        confidence=0.95,
                        metadata={'unit': 'fahrenheit'}
                    ))

        # Weather conditions
        weather_conditions = ['rain', 'snow', 'sunny', 'cloudy', 'storm', 'fog', 'wind']
        for condition in weather_conditions:
            if re.search(rf'\b{condition}(y|ing)?\b', text, re.IGNORECASE):
                entities.append(Entity(
                    entity_type='weather_condition',
                    value=condition,
                    text=condition,
                    confidence=0.85,
                    metadata={'condition_type': condition}
                ))

        return entities

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities, keeping the one with highest confidence."""
        if not entities:
            return []

        # Group by entity type and text
        grouped = {}
        for entity in entities:
            key = (entity.entity_type, entity.text.lower())
            if key not in grouped or entity.confidence > grouped[key].confidence:
                grouped[key] = entity

        return list(grouped.values())

    def add_app_alias(self, alias: str, app_name: str):
        """Add a custom app alias."""
        self.app_aliases[alias.lower()] = app_name
        logger.info(f"Added app alias: {alias} -> {app_name}")

    def get_app_aliases(self) -> Dict[str, str]:
        """Get all app aliases."""
        return self.app_aliases.copy()


# Convenience function
def create_entity_extractor(config: Dict[str, Any] = None) -> EntityExtractor:
    """
    Create an entity extractor with configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured EntityExtractor instance
    """
    if config is None:
        config = {}

    nlu_config = config.get('nlu', {})
    local_config = nlu_config.get('local', {})

    # Get custom app aliases from config
    app_control_config = config.get('skills', {}).get('app_control', {})
    custom_aliases = app_control_config.get('aliases', {})

    extractor = EntityExtractor(
        use_spacy=local_config.get('enabled', True),
        spacy_model=local_config.get('spacy_model', 'en_core_web_sm'),
    )

    # Add custom aliases
    for alias, app_name in custom_aliases.items():
        extractor.add_app_alias(alias, app_name)

    return extractor
