import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.llm.agents.presentation_planner import PresentationPlanner
from src.pptx.render.node_render import render_html_to_pptx


def main():
    """Main entry point for PowerPoint generation."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate PowerPoint presentations from visualization data using AI agents"
    )
    parser.add_argument(
        "prompt",
        type=str,
        help="Description of the presentation you want to create",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output/presentation.pptx",
        help="Output path for the generated PowerPoint file (default: output/presentation.pptx)",
    )

    args = parser.parse_args()

    print(f"Generating presentation: {args.prompt}")
    print()

    # Initialize the presentation planner agent
    planner = PresentationPlanner(api_key=os.getenv("OPENAI_API_KEY"))

    # Generate HTML slides in output directory for inspection
    slides_dir = Path("output/slides")
    slides_dir.mkdir(parents=True, exist_ok=True)

    print("Planning presentation and generating slides...")
    html_files = planner.generate_presentation(args.prompt, slides_dir)

    if not html_files:
        print("Error: No slides were generated", file=sys.stderr)
        sys.exit(1)

    print(f"Generated {len(html_files)} slides")
    print(f"HTML slides saved to: {slides_dir.resolve()}")
    print()

    # Convert HTML slides to PowerPoint
    print("Converting HTML to PowerPoint...")
    output_path = Path(args.output)
    js_workspace = Path("src/pptx/render/js")
    html2pptx_js = js_workspace / "html2pptx" / "html2pptx.cjs"

    returncode, stdout, stderr = render_html_to_pptx(
        html_files=html_files,
        output_pptx=output_path,
        js_workspace=js_workspace,
        html2pptx_js=html2pptx_js,
        layout="LAYOUT_16x9",
    )

    if returncode != 0:
        print("Error converting to PowerPoint:", file=sys.stderr)
        print(stderr, file=sys.stderr)
        print(f"\nHTML slides are available at: {slides_dir.resolve()}")
        print("You can inspect them to debug the issue.")
        sys.exit(1)

    if stdout:
        print(stdout)

    print()
    print(f"Success! Presentation saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
