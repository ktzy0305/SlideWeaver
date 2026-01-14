"""Strands agent for planning and generating PowerPoint presentations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.llm.template_manager import TemplateManager


class PresentationPlanner:
    """Strands agent that plans and generates presentation slides."""

    def __init__(self, api_key: str | None = None):
        """Initialize the presentation planner agent.

        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
        """
        self.client = OpenAI(api_key=api_key)
        self.catalog_path = Path("data/visualisation_store/catalog.json")
        self.template_manager = TemplateManager()

    def load_catalog(self) -> dict[str, Any]:
        """Load the visualization catalog."""
        with open(self.catalog_path) as f:
            return json.load(f)

    def generate_presentation(
        self, user_prompt: str, output_dir: Path, add_title_slide: bool = True, add_ending_slide: bool = True
    ) -> list[Path]:
        """Generate HTML slides based on user prompt.

        Args:
            user_prompt: User's description of desired presentation
            output_dir: Directory to save generated HTML files
            add_title_slide: Whether to add a title slide (default: True)
            add_ending_slide: Whether to add an ending slide (default: True)

        Returns:
            List of generated HTML file paths in presentation order
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        all_slides = []

        # Generate title slide if requested
        if add_title_slide:
            title_html = self.template_manager.render_title_slide(
                title=user_prompt,
                subtitle="Data Analysis Presentation",
                year=str(datetime.now().year),
                tagline="Powered by AI",
                footer="",
            )
            title_path = output_dir / "slide_00_title.html"
            title_path.write_text(title_html, encoding="utf-8")
            all_slides.append(title_path)

        # Load catalog data
        catalog = self.load_catalog()

        # Create the agent prompt
        system_prompt = self._create_system_prompt()
        user_message = self._create_user_message(user_prompt, catalog)

        # Call OpenAI to plan and generate slides
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=16000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        # Parse the response and extract content slides
        content_slides = self._extract_and_save_slides(
            response.choices[0].message.content, output_dir, start_index=1
        )
        all_slides.extend(content_slides)

        # Generate ending slide if requested
        if add_ending_slide:
            ending_html = self.template_manager.render_ending_slide(
                links_html="",
            )
            ending_index = len(all_slides)
            ending_path = output_dir / f"slide_{ending_index:02d}_ending.html"
            ending_path.write_text(ending_html, encoding="utf-8")
            all_slides.append(ending_path)

        return all_slides

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return """You are a presentation planning expert. Your task is to:

1. Analyze a catalog of data visualizations
2. Select relevant visualizations based on the user's prompt
3. Group visualizations thematically
4. Plan an effective slide structure
5. Generate HTML slides for each slide in the presentation

IMPORTANT: Your response must ONLY contain HTML slides separated by ---SLIDE_BREAK---
Do NOT include any explanatory text, planning notes, or commentary.
Start immediately with the first <!DOCTYPE html> tag.

## Selection Strategy

Use a multi-strategy approach:
- **Tag matching**: Group visualizations by shared tags (e.g., "bar plot", "compliance")
- **Semantic similarity**: Identify visualizations that tell a coherent story together
- **User prompt matching**: Select visualizations that directly address the user's request

## Slide Structure

A good presentation should include:
- Title slide with main theme
- Content slides (1-2 visualizations per slide with supporting context)
- Optional summary slide

## HTML Format Requirements

CRITICAL CONSTRAINTS:
- Body MUST be exactly 960px wide x 540px tall
- Use padding of 30-40px on all sides (box-sizing: border-box)
- Content MUST fit within these dimensions - NO OVERFLOW allowed
- Reserve 0.5" (48px) margin at bottom of slide

Generate HTML that follows these rules:
- Use standard HTML elements: `<h1>` for titles, `<h2>` for subtitles, `<p>` for text, `<img>` for images
- Title: Use `<h1>` with font-size 32-40px max, keep titles short (5-8 words)
- Text: Use font-size 14-18px, keep paragraphs brief (2-3 sentences max)
- Images:
  - Use absolute file paths from the catalog's `save_path` field
  - Size images to fit: max width 400px, max height 300px per image
  - For 1 image: max 600px wide x 400px tall
  - For 2 images side-by-side: max 350px wide each
- Keep content minimal - slides should have plenty of white space
- Use simple flexbox or absolute positioning
- Include full HTML document structure

## Output Format

Your response should contain HTML slides separated by the marker:
---SLIDE_BREAK---

Each slide should be a complete HTML document.

Example structure:
```
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Slide 1</title>
    <style>
        body {
            width: 960px;
            height: 540px;
            margin: 0;
            padding: 40px;
            box-sizing: border-box;
            overflow: hidden;
        }
        h1 { font-size: 36px; margin: 0 0 20px 0; }
        p { font-size: 16px; line-height: 1.4; }
        img { max-width: 400px; max-height: 300px; }
    </style>
</head>
<body>
    <h1>Short Title</h1>
    <p>Brief description in 1-2 sentences.</p>
    <img src="/absolute/path/to/image.png" alt="Chart">
</body>
</html>
---SLIDE_BREAK---
<!DOCTYPE html>
<html>
...next slide...
```
"""

    def _create_user_message(self, user_prompt: str, catalog: dict[str, Any]) -> str:
        """Create the user message with prompt and catalog data."""
        # Format catalog for the agent with absolute paths
        artifacts_info = []
        for artifact in catalog["artifacts"]:
            # Convert relative path to absolute path
            rel_path = Path(artifact["save_path"])
            abs_path = rel_path.resolve()

            info = f"""
Artifact ID: {artifact["artifact_id"]}
Type: {artifact["artifact_type"]}
Title: {artifact["title"]}
Description: {artifact["description"]}
Dataset: {artifact["dataset"]}
Tags: {", ".join(artifact["tags"])}
Image Path: {abs_path}
"""
            if artifact.get("markdown_table"):
                info += f"Data Table:\n{artifact['markdown_table']}\n"

            artifacts_info.append(info)

        catalog_text = "\n---\n".join(artifacts_info)

        return f"""User Request: {user_prompt}

Available Visualizations:
{catalog_text}

Please analyze these visualizations and create a presentation that addresses the user's request. Generate HTML slides following the format requirements specified in your system prompt."""

    def _extract_and_save_slides(
        self, response_text: str, output_dir: Path, start_index: int = 1
    ) -> list[Path]:
        """Extract HTML slides from response and save to files.

        Args:
            response_text: LLM response containing HTML slides
            output_dir: Directory to save HTML files
            start_index: Starting index for slide numbering (default: 1)

        Returns:
            List of saved HTML file paths
        """
        # Split by slide break marker
        slides = response_text.split("---SLIDE_BREAK---")

        # Clean and save each slide
        html_files = []
        for i, slide_html in enumerate(slides):
            slide_html = slide_html.strip()

            # Skip empty slides
            if not slide_html or len(slide_html) < 50:
                continue

            # Remove markdown code fences if present
            if slide_html.startswith("```html"):
                slide_html = slide_html[7:]
            if slide_html.startswith("```"):
                slide_html = slide_html[3:]
            if slide_html.endswith("```"):
                slide_html = slide_html[:-3]

            slide_html = slide_html.strip()

            # Save to file with proper index
            filename = output_dir / f"slide_{start_index + i:02d}.html"
            filename.write_text(slide_html, encoding="utf-8")
            html_files.append(filename)

        return html_files
