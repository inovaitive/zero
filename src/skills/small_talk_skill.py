"""
Small Talk Skill for ZERO Assistant.

This skill handles conversational interactions with J.A.R.V.I.S. personality:
- Greetings ("Hello", "Hi", "Good morning")
- Gratitude ("Thank you", "Thanks")
- Farewells ("Goodbye", "See you")
- Status queries ("How are you?", "What can you do?")
- Identity questions ("Who are you?", "What's your name?")
- Help requests ("Help me", "What can I ask?")
- General conversation (GPT-powered for complex queries)
- Fun interactions (jokes, facts, quotes)
"""

import os
import logging
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.skills.base_skill import BaseSkill, SkillResponse

logger = logging.getLogger(__name__)

# Try to import LLM client
try:
    from src.brain.llm import LLMClient
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger.warning("LLM client not available - small talk will be rule-based only")


class SmallTalkSkill(BaseSkill):
    """
    Small talk skill for natural conversation.

    Handles queries like:
    - "Hello Zero"
    - "How are you?"
    - "What can you do?"
    - "Tell me a joke"
    - "Who created you?"
    - "Thank you"
    - "Goodbye"
    """

    # Rule-based responses for common queries
    GREETINGS = [
        "Good {time_of_day}, sir. How may I assist you today?",
        "Hello, sir. I'm at your service.",
        "Greetings, sir. What can I help you with?",
        "Good {time_of_day}. Ready to assist.",
    ]

    GRATITUDE_RESPONSES = [
        "You're quite welcome, sir.",
        "Happy to help, sir.",
        "At your service, sir.",
        "My pleasure, sir.",
        "Always glad to assist.",
    ]

    FAREWELLS = [
        "Goodbye, sir. Have an excellent {time_of_day}.",
        "Until next time, sir.",
        "Farewell, sir. I'll be here when you need me.",
        "Take care, sir.",
    ]

    STATUS_RESPONSES = [
        "I'm functioning within normal parameters, sir. All systems operational.",
        "All systems are running smoothly, sir. Thank you for asking.",
        "Operating at peak efficiency, sir. How may I assist you?",
        "I'm quite well, sir. Ready to help with whatever you need.",
    ]

    IDENTITY_RESPONSES = [
        "I am ZERO, your personal AI assistant, sir. Inspired by J.A.R.V.I.S., "
        "I'm here to help with weather information, timers, application control, and general assistance.",

        "I'm ZERO, sir. A voice-driven personal assistant designed to make your life easier. "
        "I can help with weather, set timers, control applications, and engage in conversation.",

        "My name is ZERO, sir. I'm an intelligent assistant built to serve you with "
        "information retrieval, task management, and various computational needs.",
    ]

    HELP_RESPONSES = [
        "I can assist you with several tasks, sir. I can provide weather information, "
        "set timers, control applications, search the web, and engage in conversation. "
        "Simply ask me what you need.",

        "Certainly, sir. I'm capable of checking weather forecasts, managing timers, "
        "opening or closing applications, conducting web searches, and answering questions. "
        "What would you like me to help with?",

        "I have various capabilities, sir. Weather queries, timer management, "
        "application control, and general assistance are among my functions. "
        "Feel free to ask me anything.",
    ]

    CAPABILITY_DESCRIPTION = """I can assist you with the following, sir:

• Weather: "What's the weather in New York?"
• Timers: "Set a timer for 5 minutes"
• Applications: "Open Chrome" or "Close Slack"
• Web Search: "Search for Python tutorials"
• Conversation: Just talk to me naturally

What would you like help with today?"""

    # J.A.R.V.I.S.-appropriate jokes
    JOKES = [
        "Why did the programmer quit his job? Because he didn't get arrays. "
        "Although I must say, sir, that's a rather elementary pun.",

        "I would tell you a UDP joke, but you might not get it. "
        "TCP jokes, however, I'll keep telling until you acknowledge them, sir.",

        "There are only 10 types of people in the world, sir: "
        "those who understand binary, and those who don't.",

        "Why do Java developers wear glasses? Because they can't C#. "
        "My apologies, sir, that was rather predictable.",

        "A SQL query walks into a bar, walks up to two tables and asks, "
        "'May I join you?' Perhaps not the most sophisticated humor, sir.",
    ]

    # Interesting facts
    FACTS = [
        "The human brain processes information at approximately 120 meters per second, sir. "
        "Quite impressive, though still measurably slower than modern computing.",

        "There are more possible iterations of a game of chess than there are atoms "
        "in the known universe. Approximately 10^120 game variations, sir.",

        "The first computer programmer was Ada Lovelace in the 1840s, sir. "
        "She wrote algorithms for Charles Babbage's Analytical Engine.",

        "A single Google search query requires more computing power than the entire "
        "Apollo 11 moon landing mission, sir. Technology has advanced considerably.",

        "The total amount of data created every day is approximately 2.5 quintillion bytes, sir. "
        "That's 2.5 followed by 18 zeros.",
    ]

    # Motivational quotes (J.A.R.V.I.S. style)
    QUOTES = [
        "As Tony Stark once demonstrated, sir, sometimes you have to run before you can walk. "
        "Innovation often requires bold action.",

        "Intelligence is not a privilege, sir, it's a gift. And you use it for the good of mankind. "
        "Wise words to live by.",

        "The best way to predict the future is to invent it, sir. "
        "I believe that aligns well with your objectives.",

        "Excellence is not a destination, sir. It's a continuous journey. "
        "Each day presents new opportunities for improvement.",

        "Knowledge speaks, but wisdom listens, sir. Perhaps we both have something to learn.",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        enable_llm: bool = True,
        enable_jokes: bool = True,
        config: Dict[str, Any] = None,
    ):
        """
        Initialize small talk skill.

        Args:
            api_key: OpenAI API key for LLM-powered conversation
            enable_llm: Whether to use LLM for complex queries
            enable_jokes: Whether to enable jokes/fun interactions
            config: Full configuration dictionary
        """
        super().__init__(
            name="small_talk",
            description="Natural conversation with J.A.R.V.I.S. personality",
            version="1.0.0",
        )

        self.enable_llm = enable_llm and LLM_AVAILABLE
        self.enable_jokes = enable_jokes

        # Get API key from parameter, config, or environment
        if api_key:
            self.api_key = api_key
        elif config and 'nlu' in config:
            self.api_key = config.get('nlu', {}).get('cloud', {}).get('api_key')
        else:
            self.api_key = os.getenv("OPENAI_API_KEY")

        # Initialize LLM client for complex conversations
        self.llm_client = None
        if self.enable_llm and self.api_key and self.api_key != "your_openai_api_key_here":
            try:
                from src.brain.llm import LLMClient
                self.llm_client = LLMClient(
                    api_key=self.api_key,
                    model=config.get('nlu', {}).get('cloud', {}).get('model', 'gpt-4') if config else 'gpt-4',
                    temperature=0.7,  # Higher temperature for more creative conversation
                    max_tokens=300,
                )
                self.logger.info("LLM client initialized for small talk")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM client: {e}")
                self.llm_client = None
        else:
            if not self.enable_llm:
                self.logger.info("LLM disabled - using rule-based responses only")
            elif not self.api_key or self.api_key == "your_openai_api_key_here":
                self.logger.info("No OpenAI API key - using rule-based responses only")

        # Conversation history for context-aware responses
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10  # Keep last 10 exchanges

    def can_handle(self, intent: str) -> bool:
        """Check if this skill can handle the intent."""
        return intent in [
            "smalltalk.greeting",
            "smalltalk.thanks",
            "smalltalk.farewell",
            "smalltalk.status",
            "smalltalk.identity",
            "smalltalk.help",
            "smalltalk.joke",
            "smalltalk.fact",
            "smalltalk.quote",
            "smalltalk.question",
            "smalltalk.general",
            # Also accept enum-style values
            "SMALLTALK_GREETING",
            "SMALLTALK_THANKS",
            "SMALLTALK_FAREWELL",
            "SMALLTALK_STATUS",
            "SMALLTALK_IDENTITY",
            "SMALLTALK_HELP",
            "SMALLTALK_JOKE",
            "SMALLTALK_FACT",
            "SMALLTALK_QUOTE",
            "SMALLTALK_QUESTION",
            "SMALLTALK_GENERAL",
        ]

    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return [
            "smalltalk.greeting",
            "smalltalk.thanks",
            "smalltalk.farewell",
            "smalltalk.status",
            "smalltalk.identity",
            "smalltalk.help",
            "smalltalk.joke",
            "smalltalk.fact",
            "smalltalk.quote",
            "smalltalk.question",
            "smalltalk.general",
        ]

    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Execute small talk interaction.

        Args:
            intent: Intent type
            entities: Extracted entities
            context: Conversation context

        Returns:
            SkillResponse with conversation reply
        """
        # Normalize intent to lowercase without prefix
        normalized_intent = intent.lower().replace("smalltalk.", "").replace("smalltalk_", "")

        try:
            # Route to appropriate handler
            if normalized_intent == "greeting":
                message = self._handle_greeting(entities, context)
            elif normalized_intent == "thanks":
                message = self._handle_thanks(entities, context)
            elif normalized_intent == "farewell":
                message = self._handle_farewell(entities, context)
            elif normalized_intent == "status":
                message = self._handle_status(entities, context)
            elif normalized_intent == "identity":
                message = self._handle_identity(entities, context)
            elif normalized_intent == "help":
                message = self._handle_help(entities, context)
            elif normalized_intent == "joke":
                message = self._handle_joke(entities, context)
            elif normalized_intent == "fact":
                message = self._handle_fact(entities, context)
            elif normalized_intent == "quote":
                message = self._handle_quote(entities, context)
            elif normalized_intent in ["question", "general"]:
                message = self._handle_general_conversation(entities, context)
            else:
                # Fallback to general conversation
                message = self._handle_general_conversation(entities, context)

            # Update conversation history
            user_input = entities.get("user_input", "")
            if user_input:
                self._add_to_history(user_input, message)

            return self._create_success_response(
                message=message,
                data={"intent": intent},
                context_update={"last_small_talk": datetime.now().isoformat()},
            )

        except Exception as e:
            self.logger.exception(f"Error in small talk skill: {e}")
            return self._create_error_response(
                "I apologize, sir, but I encountered a minor error processing that request."
            )

    def _handle_greeting(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle greeting intents."""
        time_of_day = self._get_time_of_day()
        response = random.choice(self.GREETINGS)
        return response.format(time_of_day=time_of_day)

    def _handle_thanks(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle gratitude expressions."""
        return random.choice(self.GRATITUDE_RESPONSES)

    def _handle_farewell(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle farewell intents."""
        time_of_day = self._get_time_of_day()
        response = random.choice(self.FAREWELLS)
        return response.format(time_of_day=time_of_day)

    def _handle_status(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle status queries (How are you?)."""
        return random.choice(self.STATUS_RESPONSES)

    def _handle_identity(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle identity questions (Who are you?)."""
        return random.choice(self.IDENTITY_RESPONSES)

    def _handle_help(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle help requests."""
        # Check if user wants detailed help
        user_input = entities.get("user_input", "").lower()
        if "detail" in user_input or "all" in user_input or "everything" in user_input:
            return self.CAPABILITY_DESCRIPTION
        return random.choice(self.HELP_RESPONSES)

    def _handle_joke(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle joke requests."""
        if not self.enable_jokes:
            return "I'm afraid humor is not currently enabled, sir. Shall we discuss something else?"
        return random.choice(self.JOKES)

    def _handle_fact(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle fact requests."""
        return random.choice(self.FACTS)

    def _handle_quote(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Handle motivational quote requests."""
        return random.choice(self.QUOTES)

    def _handle_general_conversation(
        self,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Handle general conversation using LLM or fallback.

        Args:
            entities: Extracted entities
            context: Conversation context

        Returns:
            Response message
        """
        user_input = entities.get("user_input", "")

        # If LLM is available, use it for natural conversation
        if self.llm_client and self.llm_client.is_available():
            try:
                response = self.llm_client.chat(
                    user_message=user_input,
                    conversation_history=self.conversation_history[-5:],  # Last 5 exchanges
                )
                return response.content
            except Exception as e:
                self.logger.error(f"LLM conversation error: {e}")
                # Fall through to fallback

        # Fallback for when LLM is not available
        fallback_responses = [
            "I'm afraid I don't have enough information to provide a detailed answer to that, sir. "
            "Perhaps you could ask me about weather, timers, or applications?",

            "That's an interesting question, sir, but I'm not equipped to answer it at the moment. "
            "I'm better suited for weather information, timer management, and application control.",

            "I must confess, sir, that question is beyond my current capabilities. "
            "However, I can certainly help with weather, timers, and various other tasks.",

            "An intriguing query, sir, but not one I can adequately address. "
            "Perhaps I can assist you with something else?",
        ]
        return random.choice(fallback_responses)

    def _get_time_of_day(self) -> str:
        """Get current time of day for contextual greetings."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "evening"  # Use evening for night time too

    def _add_to_history(self, user_input: str, assistant_response: str):
        """Add exchange to conversation history."""
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

        # Trim history if too long
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.logger.info("Conversation history cleared")

    def get_help(self) -> str:
        """Get help text for small talk skill."""
        return """
Small Talk Skill - Natural conversation with J.A.R.V.I.S. personality

Examples:
- "Hello Zero" / "Good morning"
- "How are you?"
- "What can you do?"
- "Tell me a joke"
- "Tell me a fact"
- "Give me a quote"
- "Who are you?"
- "Thank you"
- "Goodbye"

Features:
- Natural greetings and farewells
- Status queries and identity questions
- Help and capability descriptions
- Jokes, facts, and quotes
- General conversation (GPT-powered if available)
- Context-aware responses with conversation history

The skill maintains J.A.R.V.I.S. personality: calm, intelligent, slightly formal,
addressing you as "sir" and providing helpful, professional responses.
        """.strip()


# Convenience function for skill creation
def create_small_talk_skill(config: Dict[str, Any] = None) -> SmallTalkSkill:
    """
    Create a small talk skill from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured SmallTalkSkill instance
    """
    if config is None:
        config = {}

    small_talk_config = config.get('skills', {}).get('small_talk', {})

    return SmallTalkSkill(
        api_key=small_talk_config.get('api_key'),
        enable_llm=small_talk_config.get('enable_llm', True),
        enable_jokes=small_talk_config.get('enable_jokes', True),
        config=config,
    )
