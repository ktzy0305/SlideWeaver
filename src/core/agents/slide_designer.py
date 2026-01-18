"""Slide Designer agent using Strands SDK."""

import json
import re
from pathlib import Path
from typing import Any

from strands import Agent

from core.config import PROMPTS_DIR
from core.model_provider import get_model
from core.prompts.prompt_templates import (
    SLIDE_DESIGNER_REQUEST,
    SLIDE_DESIGNER_RETRY_MESSAGE,
)
from core.schemas import (
    ArtifactCatalog,
    GlobalRules,
    SlideDesignRequest,
    SlideDesignResult,
    SlideSpec,
    Theme,
)


def load_prompt(prompt_name: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = PROMPTS_DIR / "markdown" / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8")
    # Skip YAML frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    return content


class SlideDesignerAgent:
    """Agent that designs individual slides as HTML."""

    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        model_id: str | None = None,
        max_retries: int | None = None,
        api_key: str | None = None,
    ):
        """Initialize the Slide Designer agent.

        Args:
            model_id: Model ID to use (defaults to gpt-5-mini via OpenAI)
            max_retries: Maximum retries for validation failures (default: 3)
            api_key: OpenAI API key for LLM calls
        """
        self.system_prompt = load_prompt("slide_designer")
        self.model_id = model_id
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.api_key = api_key
        self._agent: Agent | None = None

    def _get_agent(self) -> Agent:
        """Get or create the Strands agent."""
        if self._agent is None:
            self._agent = Agent(
                system_prompt=self.system_prompt,
                model=get_model(self.model_id, api_key=self.api_key),
            )

        return self._agent

    def design_slide(
        self,
        slide: SlideSpec,
        theme: Theme,
        global_rules: GlobalRules,
        catalog: ArtifactCatalog | None = None,
    ) -> SlideDesignResult:
        """Design a single slide as HTML with retry logic.

        Args:
            slide: The slide specification
            theme: Theme configuration
            global_rules: Global rules for the presentation
            catalog: Artifact catalog for resolving artifact references

        Returns:
            SlideDesignResult with HTML content and validation status
        """
        # Resolve artifacts referenced in the slide
        resolved_artifacts = self._resolve_artifacts(slide, catalog)

        # Create the design request
        request = SlideDesignRequest(
            slide=slide,
            theme=theme,
            global_rules=global_rules,
            resolved_artifacts=resolved_artifacts,
        )

        # Format the prompt
        user_message = self._format_design_request(request)

        # Run the agent with retry logic
        agent = self._get_agent()
        validation_errors: list[str] = []

        for attempt in range(1, self.max_retries + 1):
            if attempt == 1:
                result = agent(user_message)
            else:
                # On retry, ask the agent to fix the validation errors
                errors_str = "\n".join(f"- {e}" for e in validation_errors)
                retry_message = SLIDE_DESIGNER_RETRY_MESSAGE.format(
                    errors=errors_str,
                    slide_id=slide.slide_id,
                )
                result = agent(retry_message)

            # Extract HTML from response
            html_content = self._extract_html(str(result))

            # Validate the HTML
            validation_errors = self._validate_html(html_content, slide)

            if len(validation_errors) == 0:
                if attempt > 1:
                    print(f"    HTML validated on attempt {attempt}")
                return SlideDesignResult(
                    slide_id=slide.slide_id,
                    html_content=html_content,
                    validation_passed=True,
                    validation_errors=[],
                )

            print(
                f"    Attempt {attempt}/{self.max_retries} validation errors: {validation_errors}"
            )

        # Return with errors after all retries exhausted
        return SlideDesignResult(
            slide_id=slide.slide_id,
            html_content=html_content,
            validation_passed=False,
            validation_errors=validation_errors,
        )

    def _resolve_artifacts(
        self, slide: SlideSpec, catalog: ArtifactCatalog | None
    ) -> dict[str, dict[str, str]]:
        """Resolve artifact references to actual paths and content."""
        resolved: dict[str, dict[str, str]] = {}

        if catalog is None:
            return resolved

        # Build a lookup map
        artifact_map = {a.artifact_id: a for a in catalog.artifacts}

        for block in slide.content_blocks:
            if block.artifact_id and block.artifact_id in artifact_map:
                artifact = artifact_map[block.artifact_id]
                resolved[block.artifact_id] = {
                    "save_path": str(Path(artifact.save_path).resolve()),
                    "html_table": artifact.html_table,
                    "title": artifact.title,
                    "description": artifact.description,
                }

        return resolved

    def _format_design_request(self, request: SlideDesignRequest) -> str:
        """Format the design request as a prompt."""
        slide = request.slide
        theme = request.theme

        # Format content blocks
        blocks_info = []
        for i, block in enumerate(slide.content_blocks):
            block_dict: dict[str, Any] = {
                "index": i + 1,
                "type": block.block_type.value,
                "width_percent": block.width_percent,
            }

            if block.content:
                block_dict["content"] = block.content

            if block.artifact_id:
                block_dict["artifact_id"] = block.artifact_id
                block_dict["render_mode"] = (
                    block.artifact_render_mode.value
                    if block.artifact_render_mode
                    else "image"
                )

                # Add resolved artifact data
                if block.artifact_id in request.resolved_artifacts:
                    artifact_data = request.resolved_artifacts[block.artifact_id]
                    if (
                        block.artifact_render_mode
                        and block.artifact_render_mode.value == "image"
                    ):
                        block_dict["image_path"] = artifact_data["save_path"]
                    elif (
                        block.artifact_render_mode
                        and block.artifact_render_mode.value == "html_table"
                    ):
                        block_dict["html_table"] = artifact_data["html_table"]

            blocks_info.append(block_dict)

        # Format key points
        key_points_str = (
            "\n".join(f"- {p}" for p in slide.key_points)
            if slide.key_points
            else "None"
        )

        prompt = SLIDE_DESIGNER_REQUEST.format(
            slide_id=slide.slide_id,
            slide_type=slide.slide_type.value,
            title=slide.title,
            layout_hint=slide.layout_hint.value,
            objective=slide.objective,
            key_points=key_points_str,
            content_blocks=json.dumps(blocks_info, indent=2),
            font_heading=theme.fonts.heading,
            font_body=theme.fonts.body,
            color_primary=theme.color_palette.primary,
            color_secondary=theme.color_palette.secondary,
            color_accent=theme.color_palette.accent,
            color_background=theme.color_palette.background,
            color_text=theme.color_palette.text,
            max_words_per_slide=request.global_rules.max_words_per_slide,
            asset_policy=request.global_rules.asset_policy,
        )

        return prompt

    def _extract_html(self, response: str) -> str:
        """Extract HTML content from the agent response."""
        response = response.strip()

        # Handle markdown code blocks
        if "```html" in response:
            start = response.find("```html") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # Look for DOCTYPE
        doctype_match = re.search(r"<!DOCTYPE\s+html.*?>", response, re.IGNORECASE)
        if doctype_match:
            start = doctype_match.start()
            # Find the closing </html> tag
            end_match = re.search(r"</html>", response[start:], re.IGNORECASE)
            if end_match:
                return response[start : start + end_match.end()].strip()

        # If all else fails, return the response as-is
        return response

    def _validate_html(self, html: str, slide: SlideSpec) -> list[str]:
        """Validate the generated HTML."""
        errors = []

        # Check for slide-root
        if 'id="slide-root"' not in html:
            errors.append("Missing #slide-root container")

        # Check for data-slide-id
        if f'data-slide-id="{slide.slide_id}"' not in html:
            errors.append(
                f"Missing or incorrect data-slide-id (expected {slide.slide_id})"
            )

        # Check for external URLs
        if re.search(r'(src|href)=["\']https?://', html):
            errors.append("Contains external URLs (http/https)")

        # Check for DOCTYPE
        if "<!DOCTYPE" not in html.upper():
            errors.append("Missing DOCTYPE declaration")

        # Check for basic structure
        if "<html" not in html.lower():
            errors.append("Missing <html> tag")
        if "<head" not in html.lower():
            errors.append("Missing <head> tag")
        if "<body" not in html.lower():
            errors.append("Missing <body> tag")

        # Check for unwrapped text in divs (PPTX converter requirement)
        # Look for patterns like: >text< where text is not inside p, h1-h6, li, td, th
        unwrapped_pattern = r"<div[^>]*>\s*([A-Za-z][^<]{10,})"
        unwrapped_matches = re.findall(unwrapped_pattern, html)
        if unwrapped_matches:
            errors.append(
                f"DIV contains unwrapped text (wrap in <p> tags): '{unwrapped_matches[0][:50]}...'"
            )

        return errors


def design_slides_batch(
    slides: list[SlideSpec],
    theme: Theme,
    global_rules: GlobalRules,
    catalog: ArtifactCatalog | None = None,
    model_id: str | None = None,
) -> list[SlideDesignResult]:
    """Design multiple slides.

    Args:
        slides: List of slide specifications
        theme: Theme configuration
        global_rules: Global rules
        catalog: Artifact catalog
        model_id: Optional model ID

    Returns:
        List of design results
    """
    designer = SlideDesignerAgent(model_id=model_id)
    results = []

    for slide in slides:
        result = designer.design_slide(slide, theme, global_rules, catalog)
        results.append(result)

    return results
