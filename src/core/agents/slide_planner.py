"""Slide Planner agent using Strands SDK."""

import json
from pathlib import Path

from strands import Agent, tool

from core.config import CATALOG_PATH, PROMPTS_DIR
from core.model_provider import get_model
from core.schemas import (
    ArtifactCatalog,
    OrchestratorBrief,
    SlidePlan,
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


def load_catalog(catalog_path: str | Path | None = None) -> ArtifactCatalog:
    """Load the artifact catalog."""
    if catalog_path is None:
        catalog_path = CATALOG_PATH
    else:
        catalog_path = Path(catalog_path)

    with open(catalog_path) as f:
        data = json.load(f)

    return ArtifactCatalog(**data)


@tool
def get_artifact_catalog() -> str:
    """
    Retrieve the visualization artifact catalog containing available plots and tables.

    Returns a JSON string with all available artifacts including their IDs, titles,
    descriptions, tags, and file paths.
    """
    catalog = load_catalog()

    # Format for LLM consumption
    artifacts_info = []
    for artifact in catalog.artifacts:
        info = {
            "artifact_id": artifact.artifact_id,
            "type": artifact.artifact_type,
            "title": artifact.title,
            "description": artifact.description,
            "tags": artifact.tags,
            "save_path": str(Path(artifact.save_path).resolve()),
        }
        artifacts_info.append(info)

    return json.dumps(artifacts_info, indent=2)


class SlidePlannerAgent:
    """Agent that plans presentation slides based on an orchestrator brief."""

    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        model_id: str | None = None,
        max_retries: int | None = None,
        api_key: str | None = None,
    ):
        """Initialize the Slide Planner agent.

        Args:
            model_id: Model ID to use (defaults to gpt-5-mini via OpenAI)
            max_retries: Maximum retries for validation failures (default: 3)
            api_key: OpenAI API key for LLM calls
        """
        self.system_prompt = load_prompt("slide_planner")
        self.model_id = model_id
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.api_key = api_key
        self._agent: Agent | None = None

    def _get_agent(self) -> Agent:
        """Get or create the Strands agent."""
        if self._agent is None:
            self._agent = Agent(
                system_prompt=self.system_prompt,
                tools=[get_artifact_catalog],
                model=get_model(self.model_id, api_key=self.api_key),
            )

        return self._agent

    def plan(
        self, brief: OrchestratorBrief, catalog: ArtifactCatalog | None = None
    ) -> SlidePlan:
        """Generate a slide plan from an orchestrator brief.

        Args:
            brief: The orchestrator brief with presentation requirements
            catalog: Optional pre-loaded catalog (will load if not provided)

        Returns:
            A validated SlidePlan object
        """
        if catalog is None:
            catalog = load_catalog()

        # Format the catalog for the prompt
        catalog_summary = self._format_catalog_for_prompt(catalog)

        # Create the user message
        user_message = f"""## Orchestrator Brief

**Goal**: {brief.goal}
**Target Audience**: {brief.target_audience}
**Desired Tone**: {brief.desired_tone.value}
**Required Deliverables**: {", ".join(brief.required_deliverables)}

### Constraints
{json.dumps(brief.constraints, indent=2) if brief.constraints else "None specified"}

### Assumptions
{chr(10).join(f"- {a}" for a in brief.assumptions) if brief.assumptions else "None"}

## Available Artifacts

{catalog_summary}

Please create a complete Slide Plan in JSON format following the schema in your instructions."""

        # Run the agent with retry logic
        agent = self._get_agent()
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt == 1:
                    result = agent(user_message)
                else:
                    # On retry, ask the agent to fix the error
                    retry_message = f"""The previous response had a validation error:
{last_error}

Please fix the issue and output a valid JSON Slide Plan. Output ONLY the JSON, no explanations."""
                    result = agent(retry_message)

                # Extract and parse the JSON response
                response_text = str(result)
                slide_plan = self._parse_slide_plan(response_text)

                if attempt > 1:
                    print(f"  Slide plan validated on attempt {attempt}")

                return slide_plan

            except Exception as e:
                last_error = e
                print(f"  Attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries:
                    raise ValueError(
                        f"Failed to generate valid slide plan after {self.max_retries} attempts. "
                        f"Last error: {last_error}"
                    ) from e

        # This should never be reached, but satisfies type checker
        raise ValueError("Unexpected error in plan generation")

    def _format_catalog_for_prompt(self, catalog: ArtifactCatalog) -> str:
        """Format the catalog for inclusion in the prompt."""
        lines = []
        for artifact in catalog.artifacts:
            abs_path = Path(artifact.save_path).resolve()
            lines.append(f"""### {artifact.title}
- **ID**: `{artifact.artifact_id}`
- **Type**: {artifact.artifact_type}
- **Description**: {artifact.description}
- **Tags**: {", ".join(artifact.tags)}
- **Path**: `{abs_path}`
""")
        return "\n".join(lines)

    def _parse_slide_plan(self, response: str) -> SlidePlan:
        """Parse the slide plan JSON from the agent response."""
        # Try to extract JSON from the response
        response = response.strip()

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        # Find JSON object boundaries
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1

        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON object found in response")

        json_str = response[start_idx:end_idx]

        try:
            data = json.loads(json_str)
            return SlidePlan(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to validate slide plan: {e}") from e
