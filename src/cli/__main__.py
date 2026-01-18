#!/usr/bin/env python3
"""Terminal-based CLI for SlideWeaver."""

import sys
from pathlib import Path

from dotenv import load_dotenv

from core.agents import OrchestratorAgent, load_catalog
from core.config import CATALOG_PATH, DEFAULT_OUTPUT_DIR
from core.schemas import Tone


def print_header() -> None:
    """Print the CLI header."""
    print("\n" + "=" * 60)
    print("  🧵 SlideWeaver CLI")
    print("  Weave your ideas into presentations")
    print("=" * 60)


def print_help() -> None:
    """Print available commands."""
    print("""
Available Commands:
  create    - Create a new PowerPoint presentation
  plan      - Generate a slide plan only (no PPTX)
  catalog   - View available visualization artifacts
  help      - Show this help message
  exit      - Exit the application
  quit      - Exit the application
""")


def show_catalog() -> None:
    """Display the artifact catalog."""
    try:
        catalog = load_catalog()
        print(f"\nArtifact Catalog ({catalog.artifact_count} items)")
        print("-" * 50)

        for i, artifact in enumerate(catalog.artifacts, 1):
            print(f"\n{i}. {artifact.title}")
            print(f"   ID: {artifact.artifact_id}")
            print(f"   Type: {artifact.artifact_type}")
            print(f"   Description: {artifact.description[:80]}...")
            print(f"   Tags: {', '.join(artifact.tags)}")

    except FileNotFoundError:
        print(f"\nError: Catalog file not found at {CATALOG_PATH}")
    except Exception as e:
        print(f"\nError loading catalog: {e}")


def get_tone_choice() -> Tone:
    """Prompt user for tone selection."""
    print("\nSelect presentation tone:")
    print("  1. Executive (default)")
    print("  2. Technical")
    print("  3. Teaching")

    choice = input("\nEnter choice [1]: ").strip()

    if choice == "2":
        return Tone.TECHNICAL
    elif choice == "3":
        return Tone.TEACHING
    return Tone.EXECUTIVE


def create_presentation(plan_only: bool = False) -> None:
    """Create a new presentation interactively."""
    print("\n" + "-" * 40)
    print("Create New Presentation" if not plan_only else "Generate Slide Plan")
    print("-" * 40)

    # Get user request
    print("\nDescribe your presentation (what topic, what data to show):")
    user_request = input("> ").strip()

    if not user_request:
        print("Error: Please provide a description of your presentation.")
        return

    # Get audience
    print("\nTarget audience (press Enter for 'General business audience'):")
    audience = input("> ").strip()
    if not audience:
        audience = "General business audience"

    # Get tone
    tone = get_tone_choice()

    # Initialize orchestrator
    orchestrator = OrchestratorAgent(
        output_base_dir=DEFAULT_OUTPUT_DIR,
        catalog_path=CATALOG_PATH,
    )

    if plan_only:
        # Generate plan only
        print("\nGenerating slide plan...")
        try:
            plan = orchestrator.plan_only(user_request, audience, tone)

            print("\n" + "=" * 50)
            print("SLIDE PLAN GENERATED")
            print("=" * 50)
            print(f"\nTitle: {plan.title}")
            print(f"Subtitle: {plan.subtitle}")
            print(f"Audience: {plan.audience}")
            print(f"Tone: {plan.tone.value}")
            print(f"Slides: {len(plan.slides)}")

            print("\nSlide Overview:")
            for slide in plan.slides:
                print(
                    f"  {slide.slide_index}. [{slide.slide_type.value}] {slide.title}"
                )

            # Option to save
            save = input("\nSave plan to JSON file? [y/N]: ").strip().lower()
            if save == "y":
                output_path = Path("output") / "slide_plan.json"
                output_path.parent.mkdir(exist_ok=True)
                output_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
                print(f"Plan saved to: {output_path}")

        except Exception as e:
            print(f"\nError generating plan: {e}")

    else:
        # Full presentation generation
        print("\nGenerating presentation...")
        print("This may take a few minutes.\n")

        try:
            result = orchestrator.generate_presentation(
                user_request=user_request,
                audience=audience,
                tone=tone,
            )

            print("\n" + "=" * 50)
            if result.success:
                print("PRESENTATION GENERATED SUCCESSFULLY")
            else:
                print("PRESENTATION GENERATION COMPLETED WITH ISSUES")
            print("=" * 50)

            print(f"\nTitle: {result.title}")
            print(f"Slides: {result.slide_count}")
            print(f"Output: {result.output_dir}")

            if result.pptx_path:
                print(f"PPTX: {result.pptx_path}")

            if result.assumptions:
                print("\nAssumptions made:")
                for assumption in result.assumptions:
                    print(f"  - {assumption}")

            if result.limitations:
                print("\nLimitations/Warnings:")
                for limitation in result.limitations:
                    print(f"  - {limitation}")

            if result.errors:
                print("\nErrors:")
                for error in result.errors:
                    print(f"  - {error}")

        except Exception as e:
            print(f"\nError generating presentation: {e}")


def main() -> None:
    """Main CLI loop."""
    # Load environment variables
    load_dotenv()

    print_header()
    print_help()

    while True:
        try:
            command = input("\n🧵 weave> ").strip().lower()

            if command in ("exit", "quit", "q"):
                print("\nGoodbye!")
                sys.exit(0)

            elif command in ("help", "h", "?"):
                print_help()

            elif command == "catalog":
                show_catalog()

            elif command == "create":
                create_presentation(plan_only=False)

            elif command == "plan":
                create_presentation(plan_only=True)

            elif command == "":
                continue

            else:
                print(f"Unknown command: {command}")
                print("Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit.")
        except EOFError:
            print("\nGoodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
