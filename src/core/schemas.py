"""Pydantic models for PowerPoint Generator agent communication."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class SlideType(str, Enum):
    """Supported slide types."""

    TITLE = "TITLE"
    AGENDA = "AGENDA"
    SECTION = "SECTION"
    CONTENT = "CONTENT"
    CHART = "CHART"
    TABLE = "TABLE"
    SUMMARY = "SUMMARY"
    QNA = "QNA"


class ContentBlockType(str, Enum):
    """Types of content blocks within a slide."""

    TEXT = "text"
    BULLETS = "bullets"
    IMAGE = "image"
    TABLE = "table"
    CHART = "chart"
    QUOTE = "quote"


class LayoutHint(str, Enum):
    """Layout hints for slide design."""

    HERO = "hero"
    SINGLE_COLUMN = "single-column"
    TWO_COLUMN = "two-column"
    TWO_COLUMN_WIDE_LEFT = "two-column-wide-left"
    TWO_COLUMN_WIDE_RIGHT = "two-column-wide-right"
    THREE_CARDS = "three-cards"
    IMAGE_LEFT_TEXT_RIGHT = "image-left-text-right"
    TEXT_LEFT_IMAGE_RIGHT = "text-left-image-right"


class ArtifactRenderMode(str, Enum):
    """How to render an artifact in a slide."""

    IMAGE = "image"
    HTML_TABLE = "html_table"


class Tone(str, Enum):
    """Presentation tone options."""

    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    TEACHING = "teaching"


# ============================================================================
# Theme and Configuration Models
# ============================================================================


class FontConfig(BaseModel):
    """Font configuration for the presentation."""

    heading: str = Field(default="Arial", description="Font for headings")
    body: str = Field(default="Arial", description="Font for body text")


class ColorPalette(BaseModel):
    """Color palette for the presentation."""

    primary: str = Field(
        default="#1a365d", description="Primary color (headers, accents)"
    )
    secondary: str = Field(default="#2d3748", description="Secondary color")
    accent: str = Field(default="#3182ce", description="Accent color for highlights")
    background: str = Field(default="#ffffff", description="Background color")
    text: str = Field(default="#1a202c", description="Main text color")


class Theme(BaseModel):
    """Complete theme configuration."""

    fonts: FontConfig = Field(default_factory=FontConfig)
    color_palette: ColorPalette = Field(default_factory=ColorPalette)
    spacing_scale: list[int] = Field(
        default=[4, 8, 12, 16, 24], description="Spacing scale in px"
    )
    layout_grid: str = Field(default="12-col", description="Layout grid system")


class GlobalRules(BaseModel):
    """Global rules for the presentation."""

    max_words_per_slide: int = Field(default=75, description="Maximum words per slide")
    asset_policy: str = Field(default="local_only", description="Asset loading policy")
    chart_policy: str = Field(
        default="image_preferred", description="Chart rendering policy"
    )


# ============================================================================
# Content Block Models
# ============================================================================


class ContentBlock(BaseModel):
    """A content block within a slide."""

    block_type: ContentBlockType = Field(description="Type of content block")
    content: str | list[str] | None = Field(
        default=None, description="Text content or bullet items"
    )
    artifact_id: str | None = Field(
        default=None, description="Reference to catalog artifact"
    )
    artifact_render_mode: ArtifactRenderMode | None = Field(
        default=None, description="How to render the artifact"
    )
    width_percent: int = Field(
        default=100, ge=10, le=100, description="Width as percentage"
    )


# ============================================================================
# Slide Models
# ============================================================================


class SlideSpec(BaseModel):
    """Specification for a single slide."""

    slide_id: str = Field(description="Unique slide identifier (e.g., 's01_title')")
    slide_index: int = Field(ge=1, description="1-based slide index")
    slide_type: SlideType = Field(description="Type of slide")
    title: str = Field(description="Slide title")
    objective: str = Field(default="", description="Why this slide exists")
    key_points: list[str] = Field(
        default_factory=list, description="Key points for this slide"
    )
    content_blocks: list[ContentBlock] = Field(
        default_factory=list, description="Content blocks"
    )
    layout_hint: LayoutHint = Field(
        default=LayoutHint.SINGLE_COLUMN, description="Layout suggestion"
    )
    speaker_notes: str = Field(default="", description="Speaker notes")
    acceptance_checks: list[str] = Field(
        default_factory=list, description="Validation checks for this slide"
    )


# ============================================================================
# Slide Plan Models
# ============================================================================


class SlidePlan(BaseModel):
    """Complete slide plan output from the Slide Planner agent."""

    title: str = Field(description="Presentation title")
    subtitle: str = Field(default="", description="Presentation subtitle")
    audience: str = Field(default="General", description="Target audience")
    tone: Tone = Field(default=Tone.EXECUTIVE, description="Presentation tone")
    aspect_ratio: str = Field(default="16:9", description="Slide aspect ratio")
    theme: Theme = Field(default_factory=Theme, description="Theme configuration")
    global_rules: GlobalRules = Field(
        default_factory=GlobalRules, description="Global rules"
    )
    slides: list[SlideSpec] = Field(
        default_factory=list, description="List of slide specifications"
    )


# ============================================================================
# Orchestrator Models
# ============================================================================


class OrchestratorBrief(BaseModel):
    """Brief created by the Orchestrator for delegation."""

    goal: str = Field(description="What the deck is for")
    target_audience: str = Field(description="Who will view the presentation")
    desired_tone: Tone = Field(
        default=Tone.EXECUTIVE, description="Desired presentation tone"
    )
    required_deliverables: list[str] = Field(
        default_factory=lambda: ["PPTX"], description="Required outputs"
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict, description="Any constraints"
    )
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made")
    risk_flags: list[str] = Field(
        default_factory=list, description="Potential risk areas"
    )


class SlideDesignRequest(BaseModel):
    """Request to the Slide Designer agent for a single slide."""

    slide: SlideSpec = Field(description="Slide specification")
    theme: Theme = Field(description="Theme to apply")
    global_rules: GlobalRules = Field(description="Global rules")
    resolved_artifacts: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Resolved artifact data: {artifact_id: {save_path, html_table}}",
    )


class SlideDesignResult(BaseModel):
    """Result from the Slide Designer agent."""

    slide_id: str = Field(description="Slide ID this result is for")
    html_content: str = Field(description="Generated HTML content")
    validation_passed: bool = Field(
        default=True, description="Whether validation passed"
    )
    validation_errors: list[str] = Field(
        default_factory=list, description="Any validation errors"
    )


# ============================================================================
# Artifact Models
# ============================================================================


class Artifact(BaseModel):
    """A visualization artifact from the catalog."""

    artifact_id: str = Field(description="Unique artifact identifier")
    artifact_type: str = Field(description="Type: 'plot' or 'table'")
    title: str = Field(description="Display title")
    description: str = Field(description="Description of what it shows")
    dataset: str = Field(default="", description="Source dataset")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    save_path: str = Field(default="", description="Path to image file")
    html_table: str = Field(default="", description="HTML table representation")
    markdown_table: str = Field(default="", description="Markdown table representation")


class ArtifactCatalog(BaseModel):
    """Catalog of available artifacts."""

    artifact_count: int = Field(description="Number of artifacts")
    artifacts: list[Artifact] = Field(
        default_factory=list, description="List of artifacts"
    )


# ============================================================================
# Build Result Models
# ============================================================================


class BuildResult(BaseModel):
    """Result from the PPTX build process."""

    success: bool = Field(description="Whether build succeeded")
    pptx_path: str | None = Field(default=None, description="Path to generated PPTX")
    slide_count: int = Field(default=0, description="Number of slides built")
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered"
    )
    warnings: list[str] = Field(default_factory=list, description="Any warnings")


class PresentationResult(BaseModel):
    """Final result from the orchestration process."""

    success: bool = Field(description="Overall success status")
    title: str = Field(description="Presentation title")
    slide_count: int = Field(description="Number of slides")
    pptx_path: str | None = Field(default=None, description="Path to PPTX file")
    output_dir: str = Field(description="Output directory path")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made")
    limitations: list[str] = Field(
        default_factory=list, description="Known limitations"
    )
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
