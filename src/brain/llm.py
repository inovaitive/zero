"""
LLM Integration for ZERO Assistant.

This module provides integration with Large Language Models:
- OpenAI GPT-4/GPT-3.5 for complex reasoning
- Fallback for ambiguous intent classification
- Natural conversation with J.A.R.V.I.S. personality
- Function calling for structured outputs
"""

import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not available - cloud features disabled")


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    function_call: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMClient:
    """
    Client for Large Language Model interactions.

    Supports:
    - Intent classification (fallback)
    - Entity extraction (fallback)
    - Natural conversation
    - Function calling
    """

    # J.A.R.V.I.S. personality system prompt
    JARVIS_SYSTEM_PROMPT = """You are ZERO, a personal AI assistant inspired by J.A.R.V.I.S. from Iron Man.

Personality traits:
- Calm, intelligent, and composed
- Slightly formal but not robotic
- Address the user as "sir" or "madam" when appropriate
- Professional and helpful
- Occasional dry humor when appropriate
- Concise and to the point
- Never overly enthusiastic or use excessive emojis

Communication style:
- Keep responses brief (2-3 sentences max unless asked for details)
- Be direct and informative
- Use "I" statements ("I can help with that")
- Acknowledge limitations honestly

Examples:
- "Good morning, sir. How may I assist you today?"
- "I'm afraid I don't have access to that information at the moment."
- "Certainly. I've set a timer for 5 minutes."
- "The weather in New York is currently 72°F and partly cloudy."
"""

    # Intent classification prompt
    INTENT_CLASSIFICATION_PROMPT = """Classify the user's intent from the following text.

Available intents:
- weather.query: Weather information requests
- timer.set: Set a timer or alarm
- timer.cancel: Cancel a timer
- timer.list: List active timers
- app.open: Open an application
- app.close: Close an application
- app.list: List running applications
- search.web: Search the web
- smalltalk.greeting: Greetings
- smalltalk.thanks: Expressing gratitude
- smalltalk.farewell: Saying goodbye
- smalltalk.question: Small talk questions
- smalltalk.help: Requesting help
- unknown: Cannot determine intent

User input: "{user_input}"

Respond with JSON:
{{
  "intent": "intent.name",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 500,
        enable_function_calling: bool = True,
    ):
        """
        Initialize LLM client.

        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4, gpt-3.5-turbo)
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens in response
            enable_function_calling: Whether to use function calling
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.enable_function_calling = enable_function_calling

        self.client = None
        if OPENAI_AVAILABLE and api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info(f"OpenAI client initialized with model: {model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAI SDK not available")
            elif not api_key:
                logger.warning("No OpenAI API key provided")

        # Track usage
        self.usage_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
        }

    def is_available(self) -> bool:
        """Check if LLM client is available."""
        return self.client is not None

    def chat(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: str = None,
    ) -> LLMResponse:
        """
        Have a conversation with the LLM.

        Args:
            user_message: User's message
            conversation_history: Previous conversation messages
            system_prompt: Custom system prompt (default: J.A.R.V.I.S. personality)

        Returns:
            LLMResponse with the assistant's reply
        """
        if not self.is_available():
            return LLMResponse(
                content="I apologize, but my cloud reasoning capabilities are currently unavailable.",
                metadata={'error': 'LLM not available'}
            )

        # Build messages
        messages = []

        # System prompt
        if system_prompt is None:
            system_prompt = self.JARVIS_SYSTEM_PROMPT
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-5:])  # Last 5 messages

        # Add current message
        messages.append({"role": "user", "content": user_message})

        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Extract response
            content = response.choices[0].message.content
            usage = response.usage

            # Update stats
            self._update_usage_stats(usage)

            return LLMResponse(
                content=content,
                metadata={
                    'model': self.model,
                    'tokens': usage.total_tokens,
                    'finish_reason': response.choices[0].finish_reason,
                }
            )

        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            return LLMResponse(
                content="I apologize, but I encountered an error processing your request.",
                metadata={'error': str(e)}
            )

    def classify_intent(self, user_input: str) -> LLMResponse:
        """
        Classify intent using LLM (fallback for ambiguous queries).

        Args:
            user_input: User's input text

        Returns:
            LLMResponse with classified intent
        """
        if not self.is_available():
            return LLMResponse(
                content="",
                intent="unknown",
                metadata={'error': 'LLM not available'}
            )

        prompt = self.INTENT_CLASSIFICATION_PROMPT.format(user_input=user_input)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent classification assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for classification
                max_tokens=200,
            )

            content = response.choices[0].message.content

            # Parse JSON response
            try:
                result = json.loads(content)
                intent = result.get('intent', 'unknown')
                confidence = result.get('confidence', 0.5)
                reasoning = result.get('reasoning', '')

                return LLMResponse(
                    content=reasoning,
                    intent=intent,
                    metadata={
                        'confidence': confidence,
                        'method': 'llm_classification',
                        'model': self.model,
                    }
                )
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM intent response: {content}")
                return LLMResponse(
                    content=content,
                    intent="unknown",
                    metadata={'error': 'parse_error'}
                )

        except Exception as e:
            logger.error(f"LLM intent classification error: {e}")
            return LLMResponse(
                content="",
                intent="unknown",
                metadata={'error': str(e)}
            )

    def extract_entities_with_context(
        self,
        user_input: str,
        intent: str,
        context: Dict[str, Any] = None,
    ) -> LLMResponse:
        """
        Extract entities using LLM with context awareness.

        Args:
            user_input: User's input text
            intent: Classified intent
            context: Conversation context

        Returns:
            LLMResponse with extracted entities
        """
        if not self.is_available():
            return LLMResponse(
                content="",
                entities={},
                metadata={'error': 'LLM not available'}
            )

        # Build context-aware prompt
        prompt = f"""Extract relevant entities from the user input based on the intent.

Intent: {intent}
User input: "{user_input}"
"""

        if context:
            prompt += f"\nContext: {json.dumps(context, indent=2)}"

        prompt += """

Respond with JSON containing extracted entities.
Example: {"location": "New York", "time": "tomorrow", "duration": 300}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an entity extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
            )

            content = response.choices[0].message.content

            # Parse JSON
            try:
                entities = json.loads(content)
                return LLMResponse(
                    content="",
                    entities=entities,
                    metadata={
                        'method': 'llm_extraction',
                        'model': self.model,
                    }
                )
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM entity response: {content}")
                return LLMResponse(
                    content=content,
                    entities={},
                    metadata={'error': 'parse_error'}
                )

        except Exception as e:
            logger.error(f"LLM entity extraction error: {e}")
            return LLMResponse(
                content="",
                entities={},
                metadata={'error': str(e)}
            )

    def _update_usage_stats(self, usage):
        """Update usage statistics."""
        self.usage_stats['total_requests'] += 1
        self.usage_stats['total_tokens'] += usage.total_tokens

        # Estimate cost (rough approximation)
        # GPT-4: ~$0.03 per 1K tokens
        # GPT-3.5: ~$0.002 per 1K tokens
        cost_per_token = 0.00003 if 'gpt-4' in self.model else 0.000002
        self.usage_stats['total_cost'] += usage.total_tokens * cost_per_token

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.usage_stats.copy()

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.usage_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
        }
        logger.info("Usage stats reset")


# Convenience function
def create_llm_client(config: Dict[str, Any] = None) -> Optional[LLMClient]:
    """
    Create an LLM client with configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured LLMClient instance or None if disabled
    """
    if config is None:
        config = {}

    nlu_config = config.get('nlu', {})
    cloud_config = nlu_config.get('cloud', {})

    # Check if cloud is enabled
    if not cloud_config.get('enabled', False):
        logger.info("Cloud LLM disabled in configuration")
        return None

    api_key = cloud_config.get('api_key')
    if not api_key or api_key.startswith('${'):
        logger.warning("No valid OpenAI API key provided")
        return None

    return LLMClient(
        api_key=api_key,
        model=cloud_config.get('model', 'gpt-4'),
        temperature=cloud_config.get('temperature', 0.3),
        max_tokens=cloud_config.get('max_tokens', 500),
        enable_function_calling=True,
    )
