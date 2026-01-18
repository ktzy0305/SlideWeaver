"""Generation service that wraps OrchestratorAgent for streaming progress updates."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

from core.agents import OrchestratorAgent
from core.schemas import Tone

if TYPE_CHECKING:
    from backend.session_manager import Session


class GenerationService:
    """Wraps OrchestratorAgent for async web execution with progress streaming."""

    async def generate_presentation_stream(
        self,
        session: Session,
        user_request: str,
        audience: str = "General business audience",
        tone: Tone = Tone.EXECUTIVE,
        api_key: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate presentation with streaming progress updates.

        Yields SSE-formatted events for progress updates.

        Args:
            session: The user session
            user_request: What the user wants
            audience: Target audience
            tone: Desired tone
            api_key: OpenAI API key for generation

        Yields:
            SSE-formatted strings with progress events
        """

        def make_event(event_type: str, **data) -> str:
            """Create SSE-formatted event."""
            payload = {"event": event_type, **data}
            return f"data: {json.dumps(payload)}\n\n"

        try:
            # Create orchestrator with session-specific output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"presentation_{timestamp}"
            output_dir = session.output_dir / output_name
            slides_dir = output_dir / "slides"
            build_dir = output_dir / "build"

            output_dir.mkdir(parents=True, exist_ok=True)
            slides_dir.mkdir(exist_ok=True)
            build_dir.mkdir(exist_ok=True)

            orchestrator = OrchestratorAgent(
                output_base_dir=session.output_dir,
                catalog_path=None,  # We'll pass catalog directly
                api_key=api_key,
            )

            # Step 1: Create brief
            yield make_event("brief_created", status="Creating orchestrator brief...")
            brief = orchestrator.create_brief(user_request, audience, tone)
            await asyncio.sleep(0.01)  # Allow event to be sent

            # Step 2: Load/use session catalog
            yield make_event(
                "catalog_loaded", artifact_count=session.catalog.artifact_count
            )
            catalog = session.catalog
            await asyncio.sleep(0.01)

            # Step 3: Generate slide plan
            yield make_event("planning_started", status="Planning slides...")

            # Run planning in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            slide_plan = await loop.run_in_executor(
                None,
                lambda: orchestrator.planner.plan(brief, catalog),
            )

            yield make_event(
                "planning_complete",
                slide_count=len(slide_plan.slides),
                title=slide_plan.title,
            )
            await asyncio.sleep(0.01)

            # Save the slide plan
            plan_path = output_dir / "deck.json"
            plan_path.write_text(slide_plan.model_dump_json(indent=2), encoding="utf-8")

            # Step 4: Design each slide
            html_files: list[Path] = []
            errors: list[str] = []
            warnings: list[str] = []

            for slide in slide_plan.slides:
                yield make_event(
                    "slide_designing",
                    index=slide.slide_index,
                    total=len(slide_plan.slides),
                    title=slide.title,
                )

                try:
                    # Design slide in thread pool
                    result = await loop.run_in_executor(
                        None,
                        lambda s=slide: orchestrator.designer.design_slide(
                            slide=s,
                            theme=slide_plan.theme,
                            global_rules=slide_plan.global_rules,
                            catalog=catalog,
                        ),
                    )

                    if not result.validation_passed:
                        for err in result.validation_errors:
                            warnings.append(f"Slide {slide.slide_id}: {err}")

                    # Save the HTML
                    filename = f"{slide.slide_index:02d}_{slide.slide_id}.html"
                    html_path = slides_dir / filename
                    html_path.write_text(result.html_content, encoding="utf-8")
                    html_files.append(html_path)

                    yield make_event(
                        "slide_complete",
                        index=slide.slide_index,
                        slide_id=slide.slide_id,
                    )

                except Exception as e:
                    error_msg = f"Failed to design slide {slide.slide_id}: {e}"
                    errors.append(error_msg)
                    yield make_event(
                        "slide_error",
                        index=slide.slide_index,
                        error=error_msg,
                    )

                await asyncio.sleep(0.01)

            if not html_files:
                yield make_event(
                    "generation_error",
                    error="No slides were successfully designed",
                )
                yield "data: [DONE]\n\n"
                return

            # Step 5: Build PPTX
            yield make_event("build_started", status="Building PowerPoint file...")

            build_result = await loop.run_in_executor(
                None,
                lambda: orchestrator._build_pptx(
                    slides_dir, build_dir, slide_plan.title
                ),
            )

            if build_result.errors:
                errors.extend(build_result.errors)

            if build_result.success and build_result.pptx_path:
                # Create download URL relative to session
                pptx_path = Path(build_result.pptx_path)
                relative_path = pptx_path.relative_to(session.session_dir)

                yield make_event(
                    "generation_complete",
                    success=True,
                    title=slide_plan.title,
                    slide_count=len(html_files),
                    download_path=str(relative_path),
                    pptx_filename=pptx_path.name,
                    warnings=warnings,
                )
            else:
                yield make_event(
                    "generation_error",
                    error=errors[0] if errors else "Build failed",
                    errors=errors,
                )

        except Exception as e:
            yield make_event(
                "generation_error",
                error=str(e),
            )

        yield "data: [DONE]\n\n"


# Global generation service instance
generation_service = GenerationService()
