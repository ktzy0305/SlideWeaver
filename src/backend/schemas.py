"""Pydantic schemas for the web API."""

from __future__ import annotations

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """Response for session creation."""

    session_id: str
    created_at: str


class ImageUploadResponse(BaseModel):
    """Response for image upload."""

    artifact_id: str
    title: str
    save_path: str


class ImageListItem(BaseModel):
    """Item in image list response."""

    artifact_id: str
    title: str
    description: str
    save_path: str


class GenerateRequest(BaseModel):
    """Request for presentation generation."""

    user_request: str
    audience: str = "General business audience"
    tone: str = "executive"
    api_key: str | None = None
