"""FastAPI application for PowerPoint Generator web interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from core.schemas import Tone
from backend.generation_service import generation_service
from backend.image_handler import ImageValidationError, image_handler
from backend.schemas import (
    GenerateRequest,
    ImageListItem,
    ImageUploadResponse,
    SessionResponse,
)
from backend.session_manager import Session, session_manager

app = FastAPI(
    title="PowerPoint Generator API",
    description="AI-powered PowerPoint generation with chat interface",
    version="1.0.0",
)

# Add CORS middleware for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Helper Functions
# ============================================================================


def get_session_or_404(session_id: str) -> Session:
    """Get session or raise 404."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ============================================================================
# Session Endpoints
# ============================================================================


@app.post("/sessions", response_model=SessionResponse)
async def create_session():
    """Create a new session."""
    session = session_manager.create_session()
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and cleanup files."""
    if session_manager.cleanup_session(session_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session info."""
    session = get_session_or_404(session_id)
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "uploaded_images": len(session.uploaded_images),
        "total_artifacts": session.catalog.artifact_count,
    }


# ============================================================================
# Image Endpoints
# ============================================================================


@app.post("/sessions/{session_id}/images", response_model=ImageUploadResponse)
async def upload_image(
    session_id: str,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    description: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",  # Comma-separated tags
):
    """Upload an image to the session."""
    session = get_session_or_404(session_id)

    try:
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        artifact = await image_handler.process_upload(
            session=session,
            file=file,
            title=title,
            description=description,
            tags=tag_list,
        )

        # Save updated catalog
        session_manager.update_catalog(session)

        return ImageUploadResponse(
            artifact_id=artifact.artifact_id,
            title=artifact.title,
            save_path=artifact.save_path,
        )

    except ImageValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions/{session_id}/images", response_model=list[ImageListItem])
async def list_images(session_id: str):
    """List all uploaded images in the session."""
    session = get_session_or_404(session_id)

    images = []
    for artifact in session.catalog.artifacts:
        if artifact.artifact_id in session.uploaded_images:
            images.append(
                ImageListItem(
                    artifact_id=artifact.artifact_id,
                    title=artifact.title,
                    description=artifact.description,
                    save_path=artifact.save_path,
                )
            )

    return images


@app.delete("/sessions/{session_id}/images/{artifact_id}")
async def delete_image(session_id: str, artifact_id: str):
    """Remove an uploaded image."""
    session = get_session_or_404(session_id)

    if image_handler.remove_artifact(session, artifact_id):
        session_manager.update_catalog(session)
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Image not found or not user-uploaded")


@app.get("/sessions/{session_id}/images/{artifact_id}/file")
async def get_image_file(session_id: str, artifact_id: str):
    """Get the actual image file."""
    session = get_session_or_404(session_id)

    for artifact in session.catalog.artifacts:
        if artifact.artifact_id == artifact_id:
            path = Path(artifact.save_path)
            if path.exists():
                return FileResponse(path)
            raise HTTPException(status_code=404, detail="Image file not found")

    raise HTTPException(status_code=404, detail="Artifact not found")


# ============================================================================
# Catalog Endpoints
# ============================================================================


@app.get("/sessions/{session_id}/catalog")
async def get_catalog(session_id: str):
    """Get the session's artifact catalog."""
    session = get_session_or_404(session_id)
    return session.catalog.model_dump()


# ============================================================================
# Generation Endpoints
# ============================================================================


@app.post("/sessions/{session_id}/generate_stream")
async def generate_presentation_stream(
    session_id: str,
    request: GenerateRequest,
):
    """Generate a presentation with streaming progress updates."""
    session = get_session_or_404(session_id)

    # Parse tone
    try:
        tone = Tone(request.tone)
    except ValueError:
        tone = Tone.EXECUTIVE

    async def event_generator():
        async for event in generation_service.generate_presentation_stream(
            session=session,
            user_request=request.user_request,
            audience=request.audience,
            tone=tone,
            api_key=request.api_key,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Download Endpoints
# ============================================================================


@app.get("/sessions/{session_id}/download/{path:path}")
async def download_file(session_id: str, path: str):
    """Download a generated file from the session."""
    session = get_session_or_404(session_id)

    # Construct full path and validate it's within session directory
    file_path = session.session_dir / path
    file_path = file_path.resolve()

    # Security check: ensure path is within session directory
    if not str(file_path).startswith(str(session.session_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        filename=file_path.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PowerPoint Generator API",
        "docs": "/docs",
    }
