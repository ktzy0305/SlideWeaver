"""Prompt templates for LLM agents.

These templates use {placeholder} syntax for string formatting.
"""

# =============================================================================
# Slide Planner Templates
# =============================================================================

SLIDE_PLANNER_USER_MESSAGE = """\
## Orchestrator Brief

**Goal**: {goal}
**Target Audience**: {target_audience}
**Desired Tone**: {desired_tone}
**Required Deliverables**: {deliverables}

### Constraints
{constraints}

### Assumptions
{assumptions}

## Available Artifacts

{catalog_summary}

Please create a complete Slide Plan in JSON format following the schema in your instructions.\
"""

SLIDE_PLANNER_RETRY_MESSAGE = """\
The previous response had a validation error:
{error}

Please fix the issue and output a valid JSON Slide Plan. Output ONLY the JSON, no explanations.\
"""

# =============================================================================
# Slide Designer Templates
# =============================================================================

SLIDE_DESIGNER_REQUEST = """\
## Slide Specification

**Slide ID**: {slide_id}
**Slide Type**: {slide_type}
**Title**: {title}
**Layout Hint**: {layout_hint}
**Objective**: {objective}

### Key Points
{key_points}

### Content Blocks
```json
{content_blocks}
```

## Theme Configuration

**Fonts**:
- Heading: {font_heading}
- Body: {font_body}

**Colors**:
- Primary: {color_primary}
- Secondary: {color_secondary}
- Accent: {color_accent}
- Background: {color_background}
- Text: {color_text}

## Global Rules

- Max words per slide: {max_words_per_slide}
- Asset policy: {asset_policy}

Generate the HTML for this slide following your instructions.\
"""

SLIDE_DESIGNER_RETRY_MESSAGE = """\
The previous HTML had validation errors:
{errors}

Please fix these issues and output valid HTML. Remember:
- Include id="slide-root" with data-slide-id="{slide_id}"
- No external URLs (http/https)
- Include <!DOCTYPE html>, <html>, <head>, and <body> tags

Output ONLY the HTML, no explanations.\
"""

# =============================================================================
# Catalog Formatting
# =============================================================================

ARTIFACT_SUMMARY_TEMPLATE = """\
### {title}
- **ID**: `{artifact_id}`
- **Type**: {artifact_type}
- **Description**: {description}
- **Tags**: {tags}
- **Path**: `{path}`
"""
