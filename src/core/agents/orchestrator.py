"""Orchestrator agent that coordinates the presentation generation pipeline."""

import subprocess
from datetime import datetime
from pathlib import Path

from core.agents.slide_designer import SlideDesignerAgent
from core.agents.slide_planner import SlidePlannerAgent, load_catalog
from core.config import JS_CONVERTER_SCRIPT, get_converter_timeout, get_default_audience
from core.schemas import (
    BuildResult,
    OrchestratorBrief,
    PresentationResult,
    SlidePlan,
    Tone,
)


class OrchestratorAgent:
    """Orchestrates the full presentation generation pipeline."""

    def __init__(
        self,
        output_base_dir: str | Path = "output",
        model_id: str | None = None,
        catalog_path: str | Path | None = None,
        api_key: str | None = None,
    ):
        """Initialize the Orchestrator agent.

        Args:
            output_base_dir: Base directory for outputs
            model_id: Model ID for sub-agents
            catalog_path: Path to artifact catalog
            api_key: OpenAI API key for LLM calls
        """
        self.output_base_dir = Path(output_base_dir)
        self.model_id = model_id
        self.catalog_path = catalog_path
        self.api_key = api_key

        # Sub-agents
        self._planner: SlidePlannerAgent | None = None
        self._designer: SlideDesignerAgent | None = None

    @property
    def planner(self) -> SlidePlannerAgent:
        """Get or create the slide planner agent."""
        if self._planner is None:
            self._planner = SlidePlannerAgent(
                model_id=self.model_id, api_key=self.api_key
            )
        return self._planner

    @property
    def designer(self) -> SlideDesignerAgent:
        """Get or create the slide designer agent."""
        if self._designer is None:
            self._designer = SlideDesignerAgent(
                model_id=self.model_id, api_key=self.api_key
            )
        return self._designer

    def create_brief(
        self,
        user_request: str,
        audience: str = get_default_audience(),
        tone: Tone = Tone.EXECUTIVE,
    ) -> OrchestratorBrief:
        """Create an orchestrator brief from a user request.

        Args:
            user_request: The user's description of what they want
            audience: Target audience
            tone: Desired tone

        Returns:
            OrchestratorBrief object
        """
        # Make reasonable defaults and assumptions
        assumptions = [
            "16:9 aspect ratio for modern displays",
            "Professional color scheme with blue primary",
            "Arial font family for broad compatibility",
            "Local assets only (no external URLs)",
            "Maximum 75 words per slide for readability",
        ]

        return OrchestratorBrief(
            goal=user_request,
            target_audience=audience,
            desired_tone=tone,
            required_deliverables=["PPTX"],
            constraints={
                "aspect_ratio": "16:9",
                "asset_policy": "local_only",
            },
            assumptions=assumptions,
            risk_flags=[],
        )

    def generate_presentation(
        self,
        user_request: str,
        audience: str = get_default_audience(),
        tone: Tone = Tone.EXECUTIVE,
        output_name: str | None = None,
    ) -> PresentationResult:
        """Generate a complete presentation from a user request.

        Args:
            user_request: What the user wants
            audience: Target audience
            tone: Desired tone
            output_name: Optional name for the output folder

        Returns:
            PresentationResult with status and file paths
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Step 1: Create the orchestrator brief
        print("Creating orchestrator brief...")
        brief = self.create_brief(user_request, audience, tone)

        # Step 2: Set up output directory
        if output_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"presentation_{timestamp}"

        output_dir = self.output_base_dir / output_name
        slides_dir = output_dir / "slides"
        build_dir = output_dir / "build"

        output_dir.mkdir(parents=True, exist_ok=True)
        slides_dir.mkdir(exist_ok=True)
        build_dir.mkdir(exist_ok=True)

        # Step 3: Load catalog
        print("Loading artifact catalog...")
        try:
            catalog = load_catalog(self.catalog_path)
        except Exception as e:
            errors.append(f"Failed to load catalog: {e}")
            return PresentationResult(
                success=False,
                title="",
                slide_count=0,
                output_dir=str(output_dir),
                errors=errors,
            )

        # Step 4: Generate slide plan
        print("Generating slide plan...")
        try:
            slide_plan = self.planner.plan(brief, catalog)
            print(f"  Generated plan with {len(slide_plan.slides)} slides")
        except Exception as e:
            errors.append(f"Slide planning failed: {e}")
            return PresentationResult(
                success=False,
                title="",
                slide_count=0,
                output_dir=str(output_dir),
                errors=errors,
            )

        # Save the slide plan
        plan_path = output_dir / "deck.json"
        plan_path.write_text(slide_plan.model_dump_json(indent=2), encoding="utf-8")

        # Step 5: Design each slide
        print("Designing slides...")
        html_files: list[Path] = []

        for slide in slide_plan.slides:
            print(f"  Designing slide {slide.slide_index}: {slide.title}")
            try:
                result = self.designer.design_slide(
                    slide=slide,
                    theme=slide_plan.theme,
                    global_rules=slide_plan.global_rules,
                    catalog=catalog,
                )

                if not result.validation_passed:
                    for err in result.validation_errors:
                        warnings.append(f"Slide {slide.slide_id}: {err}")

                # Save the HTML
                filename = f"{slide.slide_index:02d}_{slide.slide_id}.html"
                html_path = slides_dir / filename
                html_path.write_text(result.html_content, encoding="utf-8")
                html_files.append(html_path)

            except Exception as e:
                errors.append(f"Failed to design slide {slide.slide_id}: {e}")

        if not html_files:
            errors.append("No slides were successfully designed")
            return PresentationResult(
                success=False,
                title=slide_plan.title,
                slide_count=0,
                output_dir=str(output_dir),
                errors=errors,
            )

        # Step 6: Build PPTX
        print("Building PPTX...")
        build_result = self._build_pptx(slides_dir, build_dir, slide_plan.title)

        if build_result.errors:
            errors.extend(build_result.errors)

        return PresentationResult(
            success=build_result.success and len(errors) == 0,
            title=slide_plan.title,
            slide_count=len(html_files),
            pptx_path=build_result.pptx_path,
            output_dir=str(output_dir),
            assumptions=brief.assumptions,
            limitations=warnings,
            errors=errors,
        )

    def _build_pptx(self, slides_dir: Path, build_dir: Path, title: str) -> BuildResult:
        """Build the PPTX file from HTML slides.

        Args:
            slides_dir: Directory containing HTML slides
            build_dir: Directory for build outputs
            title: Presentation title (used for filename)

        Returns:
            BuildResult with success status and paths
        """
        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        safe_title = safe_title[:50]  # Limit length
        output_filename = f"{safe_title}.pptx"
        output_path = build_dir / output_filename

        # Find the converter script
        if not JS_CONVERTER_SCRIPT.exists():
            return BuildResult(
                success=False,
                errors=[f"Converter script not found: {JS_CONVERTER_SCRIPT}"],
            )

        # Run the converter
        try:
            cmd = [
                "node",
                str(JS_CONVERTER_SCRIPT),
                "--input",
                str(slides_dir),
                "--output",
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=get_converter_timeout(),
            )

            if result.returncode != 0:
                return BuildResult(
                    success=False,
                    errors=[f"Converter failed: {result.stderr}"],
                )

            if not output_path.exists():
                return BuildResult(
                    success=False,
                    errors=["Converter completed but PPTX file was not created"],
                )

            # Count slides in the output
            html_files = list(slides_dir.glob("*.html"))

            return BuildResult(
                success=True,
                pptx_path=str(output_path),
                slide_count=len(html_files),
            )

        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                errors=[f"Converter timed out after {get_converter_timeout()} seconds"],
            )
        except Exception as e:
            return BuildResult(
                success=False,
                errors=[f"Build failed: {e}"],
            )

    def plan_only(
        self,
        user_request: str,
        audience: str = get_default_audience(),
        tone: Tone = Tone.EXECUTIVE,
    ) -> SlidePlan:
        """Generate only the slide plan without building.

        Useful for previewing or debugging the planning stage.

        Args:
            user_request: What the user wants
            audience: Target audience
            tone: Desired tone

        Returns:
            SlidePlan object
        """
        brief = self.create_brief(user_request, audience, tone)
        catalog = load_catalog(self.catalog_path)
        return self.planner.plan(brief, catalog)
