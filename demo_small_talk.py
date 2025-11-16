#!/usr/bin/env python3
"""
Interactive Demo for ZERO Small Talk Skill.
Chat with ZERO and test the J.A.R.V.I.S. personality!
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from skills.small_talk_skill import SmallTalkSkill


def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 70)
    print("  ███████╗███████╗██████╗  ██████╗     ")
    print("  ╚══███╔╝██╔════╝██╔══██╗██╔═══██╗    ")
    print("    ███╔╝ █████╗  ██████╔╝██║   ██║    ")
    print("   ███╔╝  ██╔══╝  ██╔══██╗██║   ██║    ")
    print("  ███████╗███████╗██║  ██║╚██████╔╝    ")
    print("  ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝     ")
    print()
    print("  J.A.R.V.I.S.-Inspired Personal Assistant - Small Talk Demo")
    print("=" * 70)
    print()


def print_help():
    """Print available commands."""
    print("\n📋 Try these example queries:")
    print("  • Hello / Hi / Good morning")
    print("  • How are you?")
    print("  • Who are you? / What's your name?")
    print("  • What can you do? / Help")
    print("  • Tell me a joke")
    print("  • Tell me a fact")
    print("  • Give me a quote")
    print("  • Thank you")
    print("  • Goodbye")
    print()
    print("💡 Special commands:")
    print("  • 'help' - Show this help")
    print("  • 'history' - Show conversation history")
    print("  • 'clear' - Clear conversation history")
    print("  • 'quit' or 'exit' - Exit demo")
    print()


def classify_intent(user_input: str) -> str:
    """Simple intent classification for demo."""
    user_lower = user_input.lower()

    # Greetings
    if any(word in user_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
        return "smalltalk.greeting"

    # Gratitude
    if any(word in user_lower for word in ['thank', 'thanks', 'appreciate']):
        return "smalltalk.thanks"

    # Farewell
    if any(word in user_lower for word in ['goodbye', 'bye', 'see you', 'farewell']):
        return "smalltalk.farewell"

    # Status
    if any(phrase in user_lower for phrase in ['how are you', 'how\'re you', 'doing well', 'are you okay']):
        return "smalltalk.status"

    # Identity
    if any(phrase in user_lower for phrase in ['who are you', 'what are you', 'your name', 'who\'s this']):
        return "smalltalk.identity"

    # Help
    if any(phrase in user_lower for phrase in ['what can you', 'help me', 'can you help', 'capabilities', 'what do you do']):
        return "smalltalk.help"

    # Joke
    if any(word in user_lower for word in ['joke', 'funny', 'make me laugh']):
        return "smalltalk.joke"

    # Fact
    if any(word in user_lower for word in ['fact', 'tell me something', 'interesting']):
        return "smalltalk.fact"

    # Quote
    if any(word in user_lower for word in ['quote', 'inspire', 'motivate', 'wisdom']):
        return "smalltalk.quote"

    # Default to general conversation
    return "smalltalk.general"


def main():
    """Run interactive demo."""
    print_banner()

    # Initialize Small Talk Skill
    print("🔧 Initializing ZERO Small Talk Skill...")
    config = {
        'skills': {
            'small_talk': {
                'enable_llm': False,  # Disable LLM for demo (no API key needed)
                'enable_jokes': True,
            }
        }
    }

    try:
        skill = SmallTalkSkill(config=config)
        print("✅ ZERO is ready!\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return 1

    print_help()

    # Interactive loop
    print("💬 Start chatting with ZERO (type 'quit' to exit):\n")
    print("-" * 70)

    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                response = skill.execute(
                    intent="smalltalk.farewell",
                    entities={"user_input": "goodbye"},
                    context={}
                )
                print(f"🤖 ZERO: {response.message}")
                print("\n" + "=" * 70)
                print("Session ended. Thank you for using ZERO!")
                print("=" * 70)
                break

            elif user_input.lower() == 'help':
                print_help()
                continue

            elif user_input.lower() == 'history':
                history = skill.get_conversation_history()
                if not history:
                    print("\n📝 No conversation history yet.")
                else:
                    print("\n📝 Conversation History:")
                    print("-" * 70)
                    for i, entry in enumerate(history, 1):
                        role = "You" if entry["role"] == "user" else "ZERO"
                        print(f"{i}. {role}: {entry['content']}")
                    print("-" * 70)
                continue

            elif user_input.lower() == 'clear':
                skill.clear_conversation_history()
                print("\n✅ Conversation history cleared.")
                continue

            # Classify intent
            intent = classify_intent(user_input)

            # Execute skill
            response = skill.execute(
                intent=intent,
                entities={"user_input": user_input},
                context={}
            )

            # Display response
            if response.success:
                print(f"\n🤖 ZERO: {response.message}")
            else:
                print(f"\n❌ Error: {response.message}")

            print("-" * 70)

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())
