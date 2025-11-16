"""
Intent Classification for ZERO Assistant.

This module classifies user commands into actionable intents using:
1. Local pattern matching (regex + keyword detection)
2. Cloud-based classification (OpenAI GPT) for ambiguous queries
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Try to import spaCy, but don't fail if not available
try:
    import spacy
    from spacy.matcher import Matcher
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available - using pattern matching only")


class IntentType(Enum):
    """Supported intent types."""

    # Weather intents
    WEATHER_QUERY = "weather.query"

    # Timer intents
    TIMER_SET = "timer.set"
    TIMER_CANCEL = "timer.cancel"
    TIMER_LIST = "timer.list"
    TIMER_STATUS = "timer.status"

    # App control intents
    APP_OPEN = "app.open"
    APP_CLOSE = "app.close"
    APP_LIST = "app.list"
    APP_SWITCH = "app.switch"

    # Search intents
    SEARCH_WEB = "search.web"

    # Small talk intents
    SMALLTALK_GREETING = "smalltalk.greeting"
    SMALLTALK_THANKS = "smalltalk.thanks"
    SMALLTALK_FAREWELL = "smalltalk.farewell"
    SMALLTALK_QUESTION = "smalltalk.question"
    SMALLTALK_HELP = "smalltalk.help"

    # System intents
    SYSTEM_STATUS = "system.status"
    SYSTEM_SETTINGS = "system.settings"

    # Unknown/fallback
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent classification."""

    intent: IntentType
    confidence: float  # 0.0 to 1.0
    method: str  # 'pattern', 'spacy', 'cloud'
    raw_text: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IntentClassifier:
    """
    Classifies user input into intents using local patterns and optional cloud AI.

    Uses a hybrid approach:
    1. First tries local pattern matching (fast, offline)
    2. Falls back to cloud AI if confidence is low
    """

    def __init__(
        self,
        use_spacy: bool = True,
        spacy_model: str = "en_core_web_sm",
        confidence_threshold: float = 0.8,
        use_cloud_fallback: bool = False,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize intent classifier.

        Args:
            use_spacy: Whether to use spaCy for pattern matching
            spacy_model: spaCy model name
            confidence_threshold: Minimum confidence for local classification
            use_cloud_fallback: Whether to use cloud AI for low-confidence results
            llm_client: Optional LLM client for cloud fallback
        """
        self.confidence_threshold = confidence_threshold
        self.use_cloud_fallback = use_cloud_fallback
        self.llm_client = llm_client

        # Initialize spaCy if available and requested
        self.nlp = None
        self.matcher = None
        if use_spacy and SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load(spacy_model)
                self.matcher = Matcher(self.nlp.vocab)
                self._setup_spacy_patterns()
                logger.info(f"Loaded spaCy model: {spacy_model}")
            except Exception as e:
                logger.warning(f"spaCy model '{spacy_model}' could not be loaded ({e}) - using pattern matching only")

        # Initialize intent patterns
        self._setup_patterns()

        logger.info("Intent classifier initialized")

    def _setup_patterns(self):
        """Set up regex patterns for intent matching."""
        self.patterns = {
            # Weather patterns
            IntentType.WEATHER_QUERY: [
                r'\b(what|how)\'?s?\s+the\s+weather\b',
                r'\bweather\s+(in|at|for)\b',
                r'\b(will|is)\s+it\s+(going\s+to\s+)?(rain|snow|sunny|cloudy)\b',
                r'\bis\s+it\s+going\s+to\s+(rain|snow|sunny|cloudy)\b',
                r'\bforecast\b',
                r'\btemperature\b.*\b(in|at|for)\b',
                r'\bhow\s+(hot|cold|warm)\b',
            ],

            # Timer patterns
            IntentType.TIMER_SET: [
                r'\bset\s+(a\s+)?timer\b',
                r'\btimer\s+for\b',
                r'\bremind\s+me\s+in\b',
                r'\balarm\s+(for|in)\b',
            ],
            IntentType.TIMER_CANCEL: [
                r'\bcancel\s+(the\s+)?(all\s+)?timer(s)?\b',
                r'\bstop\s+(the\s+)?(all\s+)?timer(s)?\b',
                r'\bdelete\s+(the\s+)?(all\s+)?timer(s)?\b',
                r'\bturn\s+off\s+(the\s+)?(all\s+)?timer(s)?\b',
            ],
            IntentType.TIMER_LIST: [
                r'\blist\s+timers\b',
                r'\bshow\s+(me\s+)?(my\s+)?timers\b',
                r'\bwhat\s+timers\b',
                r'\bactive\s+timers\b',
            ],
            IntentType.TIMER_STATUS: [
                r'\bhow\s+(much|long)\s+.*\s+(left|remaining)\b',
                r'\btime\s+(left|remaining)\b',
                r'\btimer\s+status\b',
            ],

            # App control patterns
            IntentType.APP_OPEN: [
                r'\bopen\s+\w+',
                r'\blaunch\s+\w+',
                r'\bstart\s+\w+',
                r'\brun\s+\w+',
            ],
            IntentType.APP_CLOSE: [
                r'\bclose\s+\w+',
                r'\bquit\s+\w+',
                r'\bexit\s+\w+',
                r'\bkill\s+\w+',
                r'\bstop\s+\w+',
            ],
            IntentType.APP_LIST: [
                r'\blist\s+(running\s+)?app(lication)?s\b',
                r'\bwhat\s+apps?\s+(are\s+)?(running|open)\b',
                r'\bshow\s+(me\s+)?(running\s+)?app(lication)?s\b',
            ],
            IntentType.APP_SWITCH: [
                r'\bswitch\s+to\s+\w+',
                r'\bfocus\s+(on\s+)?\w+',
                r'\bgo\s+to\s+\w+',
            ],

            # Search patterns
            IntentType.SEARCH_WEB: [
                r'\bsearch\s+(for\s+)?\w+',
                r'\bgoogle\s+\w+',
                r'\blook\s+up\s+\w+',
                r'\bfind\s+(me\s+)?(information\s+)?(about\s+)?\w+',
            ],

            # Small talk patterns
            IntentType.SMALLTALK_GREETING: [
                r'\b(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b',
                r'\bwhat\'?s\s+up\b',
                r'\bhowdy\b',
            ],
            IntentType.SMALLTALK_THANKS: [
                r'\b(thank|thanks|thx|ty)\b',
                r'\bappreciate\s+it\b',
                r'\byou\'?re\s+(the\s+)?best\b',
            ],
            IntentType.SMALLTALK_FAREWELL: [
                r'\b(bye|goodbye|see\s+you|farewell)\b',
                r'\bgood\s+night\b',
                r'\btalk\s+to\s+you\s+later\b',
            ],
            IntentType.SMALLTALK_QUESTION: [
                r'\bhow\s+are\s+you\b',
                r'\bhow\'?s\s+it\s+going\b',
                r'\bwhat\s+do\s+you\s+think\b',
                r'\bwho\s+are\s+you\b',
                r'\bwhat\'?s\s+your\s+name\b',
            ],
            IntentType.SMALLTALK_HELP: [
                r'\bhelp\b',
                r'\bwhat\s+can\s+you\s+do\b',
                r'\bshow\s+me\s+(your\s+)?capabilities\b',
                r'\bwhat\s+(are\s+)?your\s+commands\b',
            ],

            # System patterns
            IntentType.SYSTEM_STATUS: [
                r'\bstatus\b',
                r'\bhow\s+(are\s+)?things\b',
                r'\b(system\s+)?info(rmation)?\b',
            ],
        }

    def _setup_spacy_patterns(self):
        """Set up spaCy Matcher patterns."""
        if not self.matcher:
            return

        # Weather patterns
        self.matcher.add("WEATHER_QUERY", [
            [{"LOWER": {"IN": ["weather", "forecast", "temperature"]}}],
            [{"LOWER": "how"}, {"LOWER": {"IN": ["hot", "cold", "warm"]}}],
        ])

        # Timer patterns
        self.matcher.add("TIMER_SET", [
            [{"LOWER": "set"}, {"LOWER": {"IN": ["timer", "alarm"]}}],
            [{"LOWER": "timer"}, {"LOWER": "for"}],
        ])

        # App control patterns
        self.matcher.add("APP_OPEN", [
            [{"LOWER": {"IN": ["open", "launch", "start", "run"]}}],
        ])

        # Small talk patterns
        self.matcher.add("GREETING", [
            [{"LOWER": {"IN": ["hi", "hello", "hey", "greetings"]}}],
        ])

    def classify(self, text: str) -> IntentResult:
        """
        Classify user input into an intent.

        Args:
            text: User input text

        Returns:
            IntentResult with classified intent and confidence
        """
        text = text.strip().lower()

        if not text:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=1.0,
                method='empty',
                raw_text=text
            )

        # Try local pattern matching first
        result = self._classify_with_patterns(text)

        # If confidence is high enough, return it
        if result.confidence >= self.confidence_threshold:
            logger.debug(f"Intent classified with patterns: {result.intent.value} ({result.confidence:.2f})")
            return result

        # Try spaCy if available
        if self.nlp and self.matcher:
            spacy_result = self._classify_with_spacy(text)
            if spacy_result.confidence > result.confidence:
                result = spacy_result

        # If still low confidence and cloud fallback enabled, use cloud
        if result.confidence < self.confidence_threshold and self.use_cloud_fallback:
            logger.debug(f"Low confidence ({result.confidence:.2f}), using cloud fallback")
            cloud_result = self._classify_with_cloud(text)
            if cloud_result and cloud_result.confidence > result.confidence:
                logger.info(f"Cloud classification improved confidence: {result.confidence:.2f} -> {cloud_result.confidence:.2f}")
                return cloud_result
            elif cloud_result:
                logger.debug(f"Cloud classification confidence ({cloud_result.confidence:.2f}) not better than local, using local result")

        logger.debug(f"Final intent: {result.intent.value} ({result.confidence:.2f})")
        return result

    def _classify_with_patterns(self, text: str) -> IntentResult:
        """Classify using regex patterns."""
        best_match = None
        best_confidence = 0.0

        for intent_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Calculate confidence based on match quality
                    match_length = len(match.group(0))
                    text_length = len(text)
                    confidence = min(0.95, (match_length / text_length) * 1.2)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = intent_type
                        break

        if best_match:
            return IntentResult(
                intent=best_match,
                confidence=best_confidence,
                method='pattern',
                raw_text=text,
                metadata={'pattern_matched': True}
            )

        # No match found
        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            method='pattern',
            raw_text=text
        )

    def _classify_with_spacy(self, text: str) -> IntentResult:
        """Classify using spaCy matcher."""
        if not self.nlp or not self.matcher:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                method='spacy',
                raw_text=text
            )

        doc = self.nlp(text)
        matches = self.matcher(doc)

        if matches:
            # Get the first match (could be improved to rank matches)
            match_id, start, end = matches[0]
            match_label = self.nlp.vocab.strings[match_id]

            # Map spaCy label to IntentType
            intent_map = {
                "WEATHER_QUERY": IntentType.WEATHER_QUERY,
                "TIMER_SET": IntentType.TIMER_SET,
                "APP_OPEN": IntentType.APP_OPEN,
                "GREETING": IntentType.SMALLTALK_GREETING,
            }

            intent = intent_map.get(match_label, IntentType.UNKNOWN)
            confidence = 0.85  # spaCy matches get 0.85 confidence

            return IntentResult(
                intent=intent,
                confidence=confidence,
                method='spacy',
                raw_text=text,
                metadata={'spacy_label': match_label}
            )

        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            method='spacy',
            raw_text=text
        )

    def _classify_with_cloud(self, text: str) -> Optional[IntentResult]:
        """
        Classify intent using cloud LLM (OpenAI).

        Args:
            text: User input text

        Returns:
            IntentResult from cloud classification, or None if unavailable
        """
        if not self.llm_client or not self.llm_client.is_available():
            logger.debug("LLM client not available for cloud classification")
            return None

        try:
            # Use LLM client to classify intent
            llm_response = self.llm_client.classify_intent(text)
            
            if llm_response.intent and llm_response.metadata.get('error') is None:
                # Map string intent to IntentType enum
                intent_str = llm_response.intent
                confidence = llm_response.metadata.get('confidence', 0.7)
                
                # Try to find matching IntentType
                intent_type = None
                for intent_enum in IntentType:
                    if intent_enum.value == intent_str:
                        intent_type = intent_enum
                        break
                
                # If no exact match, try to infer from the string
                if intent_type is None:
                    # Handle common variations
                    if 'weather' in intent_str.lower():
                        intent_type = IntentType.WEATHER_QUERY
                    elif 'timer' in intent_str.lower() and 'set' in intent_str.lower():
                        intent_type = IntentType.TIMER_SET
                    elif 'timer' in intent_str.lower() and 'cancel' in intent_str.lower():
                        intent_type = IntentType.TIMER_CANCEL
                    elif 'app' in intent_str.lower() and 'open' in intent_str.lower():
                        intent_type = IntentType.APP_OPEN
                    elif 'greeting' in intent_str.lower() or 'hello' in intent_str.lower():
                        intent_type = IntentType.SMALLTALK_GREETING
                    elif 'thanks' in intent_str.lower() or 'thank' in intent_str.lower():
                        intent_type = IntentType.SMALLTALK_THANKS
                    else:
                        intent_type = IntentType.UNKNOWN
                
                return IntentResult(
                    intent=intent_type,
                    confidence=float(confidence),
                    method='cloud_llm',
                    raw_text=text,
                    metadata={
                        'llm_model': llm_response.metadata.get('model', 'unknown'),
                        'llm_reasoning': llm_response.content,
                    }
                )
            else:
                logger.warning(f"Cloud classification failed: {llm_response.metadata.get('error', 'unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error in cloud classification: {e}", exc_info=True)
            return None

    def get_intent_info(self, intent: IntentType) -> Dict[str, Any]:
        """
        Get information about an intent type.

        Args:
            intent: The intent type

        Returns:
            Dictionary with intent information
        """
        descriptions = {
            IntentType.WEATHER_QUERY: "Get weather information",
            IntentType.TIMER_SET: "Set a timer or alarm",
            IntentType.TIMER_CANCEL: "Cancel a timer",
            IntentType.TIMER_LIST: "List active timers",
            IntentType.TIMER_STATUS: "Check timer status",
            IntentType.APP_OPEN: "Open an application",
            IntentType.APP_CLOSE: "Close an application",
            IntentType.APP_LIST: "List running applications",
            IntentType.APP_SWITCH: "Switch to an application",
            IntentType.SEARCH_WEB: "Search the web",
            IntentType.SMALLTALK_GREETING: "Greeting",
            IntentType.SMALLTALK_THANKS: "Express gratitude",
            IntentType.SMALLTALK_FAREWELL: "Say goodbye",
            IntentType.SMALLTALK_QUESTION: "Small talk question",
            IntentType.SMALLTALK_HELP: "Request help",
            IntentType.SYSTEM_STATUS: "Check system status",
            IntentType.SYSTEM_SETTINGS: "Manage settings",
            IntentType.UNKNOWN: "Unknown intent",
        }

        return {
            "name": intent.value,
            "description": descriptions.get(intent, "No description"),
            "category": intent.value.split('.')[0] if '.' in intent.value else "unknown"
        }

    def list_intents(self) -> List[Dict[str, Any]]:
        """List all available intents."""
        return [self.get_intent_info(intent) for intent in IntentType]


# Convenience function
def create_intent_classifier(config: Dict[str, Any] = None) -> IntentClassifier:
    """
    Create an intent classifier with configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured IntentClassifier instance
    """
    if config is None:
        config = {}

    # Extract NLU config
    nlu_config = config.get('nlu', {})
    local_config = nlu_config.get('local', {})
    cloud_config = nlu_config.get('cloud', {})

    # Create LLM client if cloud fallback is enabled
    llm_client = None
    use_cloud_fallback = cloud_config.get('enabled', False)
    if use_cloud_fallback:
        from src.brain.llm import create_llm_client
        llm_client = create_llm_client(config)
        if llm_client and llm_client.is_available():
            logger.info("LLM client initialized for cloud fallback")
        else:
            logger.warning("Cloud fallback enabled but LLM client not available - falling back to local only")
            use_cloud_fallback = False

    return IntentClassifier(
        use_spacy=local_config.get('enabled', True),
        spacy_model=local_config.get('spacy_model', 'en_core_web_sm'),
        confidence_threshold=local_config.get('confidence_threshold', 0.8),
        use_cloud_fallback=use_cloud_fallback,
        llm_client=llm_client,
    )
