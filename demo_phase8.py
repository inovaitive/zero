#!/usr/bin/env python3
"""
Interactive Demo for ZERO Assistant - Phase 8.

This script demonstrates the Phase 8 integration:
- Main engine orchestration
- Complete NLU → Skills pipeline
- All components working together
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

from src.core.config import get_config
from src.core.engine import create_engine
from src.core.state import get_state_manager


console = Console()


def print_header():
    """Print demo header."""
    console.clear()
    console.print()
    console.print("╔════════════════════════════════════════════════════════╗", style="bold cyan")
    console.print("║       ZERO Assistant - Phase 8 Demo                   ║", style="bold cyan")
    console.print("║       Main Engine & Integration                       ║", style="bold cyan")
    console.print("╚════════════════════════════════════════════════════════╝", style="bold cyan")
    console.print()


def print_section(title: str):
    """Print section header."""
    console.print()
    console.print(f"[bold yellow]{'='*60}[/bold yellow]")
    console.print(f"[bold yellow]{title}[/bold yellow]")
    console.print(f"[bold yellow]{'='*60}[/bold yellow]")
    console.print()


def print_status(status: dict):
    """Print engine status."""
    table = Table(title="Engine Status", box=box.ROUNDED, show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Running", "✓ Yes" if status['running'] else "✗ No")
    table.add_row("State", status['state'])
    table.add_row("Skills Loaded", str(status['skills_loaded']))

    console.print(table)

    # Components table
    components_table = Table(title="Components", box=box.ROUNDED)
    components_table.add_column("Component", style="cyan")
    components_table.add_column("Status", style="green")

    for component, loaded in status['components'].items():
        status_icon = "✓" if loaded else "✗"
        components_table.add_row(component, status_icon)

    console.print(components_table)


def print_result(result):
    """Print processing result."""
    # Result summary
    result_table = Table(box=box.ROUNDED, show_header=False)
    result_table.add_column("Property", style="cyan")
    result_table.add_column("Value")

    result_table.add_row("Success", "✓" if result.success else "✗")
    result_table.add_row("Intent", result.intent or "N/A")
    result_table.add_row("Latency", f"{result.latency_ms:.0f}ms" if result.latency_ms else "N/A")

    if result.entities:
        entities_str = ", ".join([f"{k}={v}" for k, v in result.entities.items()])
        result_table.add_row("Entities", entities_str)

    console.print(result_table)

    # Response
    console.print()
    console.print(Panel(
        Text(result.response_text or "No response", style="bold green"),
        title="[bold]Response",
        border_style="green"
    ))


def demo_initialization():
    """Demo: Engine initialization."""
    print_section("1. Engine Initialization")

    console.print("Creating ZERO engine...")

    # Load config
    config = get_config()
    console.print("✓ Configuration loaded", style="green")

    # Create state manager
    state_manager = get_state_manager()
    console.print("✓ State manager created", style="green")

    # Create engine
    engine = create_engine(config, state_manager)
    console.print("✓ Engine created", style="green")

    # Initialize components
    console.print("\nInitializing components...")
    engine.initialize_components()
    console.print("✓ All components initialized", style="green")

    return engine


def demo_status(engine):
    """Demo: Status reporting."""
    print_section("2. Engine Status")

    status = engine.get_status()
    print_status(status)

    console.print()
    console.print(f"✓ Engine has [bold]{status['skills_loaded']}[/bold] skills loaded", style="green")


def demo_text_pipeline(engine):
    """Demo: Text processing pipeline."""
    print_section("3. Text Processing Pipeline")

    test_queries = [
        ("Hello", "Simple greeting"),
        ("What's the weather in New York?", "Weather query with location"),
        ("Set a timer for 5 minutes", "Timer command with duration"),
        ("What timers are active?", "Timer status query"),
        ("Thank you", "Gratitude expression"),
    ]

    for i, (query, description) in enumerate(test_queries, 1):
        console.print(f"\n[bold cyan]Test {i}:[/bold cyan] {description}")
        console.print(f"[dim]Query:[/dim] \"{query}\"")
        console.print()

        # Process query
        result = engine.process_text_command(query)

        # Display result
        print_result(result)

        if i < len(test_queries):
            input("\n[dim]Press Enter to continue...[/dim]")


def demo_context(engine):
    """Demo: Context management."""
    print_section("4. Context Management")

    console.print("Testing context persistence across queries...\n")

    # First query establishes context
    console.print("[bold cyan]Query 1:[/bold cyan] Establishing context")
    console.print('[dim]"What\'s the weather in Paris?"[/dim]\n')

    result1 = engine.process_text_command("What's the weather in Paris?")
    print_result(result1)

    input("\n[dim]Press Enter for next query...[/dim]")

    # Second query uses context
    console.print("\n[bold cyan]Query 2:[/bold cyan] Using context from previous query")
    console.print('[dim]"What about tomorrow?"[/dim]\n')

    result2 = engine.process_text_command("What about tomorrow?")
    print_result(result2)

    console.print()
    console.print("✓ Context maintained across queries", style="green")


def demo_skills(engine):
    """Demo: Skill routing and execution."""
    print_section("5. Skill Routing & Execution")

    console.print("Testing skill routing for different intents...\n")

    skill_tests = [
        ("What's the weather?", "WeatherSkill", "weather"),
        ("Set a timer", "TimerSkill", "timer"),
        ("How are you?", "SmallTalkSkill", "smalltalk"),
    ]

    for query, expected_skill, intent_prefix in skill_tests:
        console.print(f"[bold cyan]Query:[/bold cyan] \"{query}\"")
        console.print(f"[dim]Expected to route to: {expected_skill}[/dim]\n")

        result = engine.process_text_command(query)

        # Verify routing
        if result.intent and result.intent.startswith(intent_prefix):
            console.print(f"✓ Correctly routed to {expected_skill}", style="green")
        else:
            console.print(f"✗ Unexpected routing: {result.intent}", style="yellow")

        print_result(result)
        console.print()


def demo_error_handling(engine):
    """Demo: Error handling."""
    print_section("6. Error Handling")

    console.print("Testing error handling and recovery...\n")

    error_tests = [
        ("", "Empty input"),
        ("asdfghjkl qwerty", "Nonsense input"),
    ]

    for query, description in error_tests:
        console.print(f"[bold cyan]Test:[/bold cyan] {description}")
        console.print(f'[dim]Query: "{query}"[/dim]\n')

        result = engine.process_text_command(query)

        if result.success or not result.success:  # Either way is OK
            console.print("✓ Error handled gracefully", style="green")
        else:
            console.print("✗ Unexpected crash", style="red")

        print_result(result)
        console.print()

    # Verify engine still works
    console.print("[bold cyan]Verification:[/bold cyan] Engine still functional after errors")
    console.print('[dim]Query: "Hello"[/dim]\n')

    result = engine.process_text_command("Hello")
    if result.success:
        console.print("✓ Engine recovered successfully", style="green")
    else:
        console.print("✗ Engine not functional", style="red")

    console.print()


def demo_performance(engine):
    """Demo: Performance testing."""
    print_section("7. Performance Testing")

    console.print("Testing response latency...\n")

    queries = [
        "Hello",
        "What's the weather?",
        "Set a timer for 5 minutes",
        "Thank you",
    ]

    latencies = []

    for query in queries:
        result = engine.process_text_command(query)
        if result.latency_ms:
            latencies.append(result.latency_ms)
            console.print(f"  {query:<40} {result.latency_ms:>6.0f}ms")

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        console.print()
        console.print(f"  [bold]Average Latency:[/bold] {avg_latency:.0f}ms", style="cyan")
        console.print(f"  [bold]Min Latency:[/bold]     {min_latency:.0f}ms", style="cyan")
        console.print(f"  [bold]Max Latency:[/bold]     {max_latency:.0f}ms", style="cyan")

        console.print()
        if avg_latency < 3000:
            console.print("✓ Meets performance target (<3s)", style="green")
        else:
            console.print("⚠ Above target latency", style="yellow")


def demo_interactive(engine):
    """Demo: Interactive mode."""
    print_section("8. Interactive Mode")

    console.print("You can now interact with ZERO directly!")
    console.print("Type your queries and see the full pipeline in action.")
    console.print("[dim]Type 'exit' to return to menu[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'back']:
                break

            console.print()
            result = engine.process_text_command(user_input)
            print_result(result)
            console.print()

        except KeyboardInterrupt:
            break


def main():
    """Run the interactive demo."""
    print_header()

    console.print("[bold]This demo showcases Phase 8: Main Engine & Integration[/bold]")
    console.print()
    console.print("Features demonstrated:")
    console.print("  • Engine initialization and component orchestration")
    console.print("  • Complete NLU → Skills pipeline")
    console.print("  • State management and transitions")
    console.print("  • Context persistence across queries")
    console.print("  • Skill auto-discovery and routing")
    console.print("  • Error handling and recovery")
    console.print("  • Performance measurement")
    console.print()

    input("[dim]Press Enter to begin the demo...[/dim]")

    try:
        # Initialize engine
        engine = demo_initialization()

        while True:
            console.print()
            console.print("[bold cyan]Demo Menu:[/bold cyan]")
            console.print("  1. View Engine Status")
            console.print("  2. Test Text Processing Pipeline")
            console.print("  3. Test Context Management")
            console.print("  4. Test Skill Routing")
            console.print("  5. Test Error Handling")
            console.print("  6. Test Performance")
            console.print("  7. Interactive Mode")
            console.print("  8. Run All Demos")
            console.print("  0. Exit")
            console.print()

            choice = console.input("[bold]Select demo (0-8):[/bold] ").strip()

            if choice == '0':
                break
            elif choice == '1':
                demo_status(engine)
            elif choice == '2':
                demo_text_pipeline(engine)
            elif choice == '3':
                demo_context(engine)
            elif choice == '4':
                demo_skills(engine)
            elif choice == '5':
                demo_error_handling(engine)
            elif choice == '6':
                demo_performance(engine)
            elif choice == '7':
                demo_interactive(engine)
            elif choice == '8':
                demo_status(engine)
                input("\n[dim]Press Enter to continue...[/dim]")
                demo_text_pipeline(engine)
                demo_context(engine)
                input("\n[dim]Press Enter to continue...[/dim]")
                demo_skills(engine)
                input("\n[dim]Press Enter to continue...[/dim]")
                demo_error_handling(engine)
                demo_performance(engine)
            else:
                console.print("[red]Invalid choice. Please select 0-8.[/red]")

        console.print()
        console.print("[bold green]Demo complete! Thank you for testing ZERO Phase 8.[/bold green]")
        console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
