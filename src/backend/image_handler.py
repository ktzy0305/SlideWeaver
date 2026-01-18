"""Image upload handling and validation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import UploadFile

from core.config import get_allowed_image_extensions, get_max_image_size_mb
from core.schemas import Artifact

if TYPE_CHECKING:
    from backend.session_manager import Session

# Allowed image types
ALLOWED_EXTENSIONS = get_allowed_image_extensions()
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/svg+xml",
    "image/webp",
}
MAX_FILE_SIZE = get_max_image_size_mb() * 1024 * 1024


class ImageValidationError(Exception):
    """Raised when image validation fails."""

    pass


class ImageHandler:
    """Handles image upload, validation, and catalog integration."""

    def validate_file(self, file: UploadFile, content: bytes) -> None:
        """Validate uploaded file.

        Args:
            file: The uploaded file
            content: File content bytes

        Raises:
            ImageValidationError: If validation fails
        """
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise ImageValidationError(
                f"File size {len(content)} exceeds maximum {MAX_FILE_SIZE} bytes"
            )

        # Check extension
        if file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ImageValidationError(
                    f"File extension '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"
                )

        # Check MIME type
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            raise ImageValidationError(
                f"MIME type '{file.content_type}' not allowed. Allowed: {ALLOWED_MIME_TYPES}"
            )

    async def process_upload(
        self,
        session: Session,
        file: UploadFile,
        title: str | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ) -> Artifact:
        """Process uploaded image and add to session catalog.

        Args:
            session: The user session
            file: Uploaded file
            title: Display title for the image
            description: Description of what the image shows
            tags: Tags for categorization

        Returns:
            The created Artifact
        """
        # Read file content
        content = await file.read()

        # Validate
        self.validate_file(file, content)

        # Generate artifact ID
        artifact_id = f"user_upload_{uuid.uuid4().hex[:8]}"

        # Determine extension
        ext = ".png"  # Default
        if file.filename:
            ext = Path(file.filename).suffix.lower()

        # Save file
        save_path = session.uploads_dir / f"{artifact_id}{ext}"
        save_path.write_bytes(content)

        # Use filename as title if not provided
        if not title:
            title = Path(file.filename).stem if file.filename else artifact_id

        # Create artifact entry
        artifact = Artifact(
            artifact_id=artifact_id,
            artifact_type="plot",  # Treat as plot for image display
            title=title,
            description=description,
            tags=(tags or []) + ["user_upload"],
            save_path=str(save_path.resolve()),
            html_table="",
            markdown_table="",
        )

        # Add to session catalog
        session.catalog.artifacts.append(artifact)
        session.catalog.artifact_count += 1
        session.uploaded_images.append(artifact_id)

        return artifact

    def remove_artifact(self, session: Session, artifact_id: str) -> bool:
        """Remove an uploaded artifact from the session.

        Args:
            session: The user session
            artifact_id: ID of artifact to remove

        Returns:
            True if removed, False if not found
        """
        # Only allow removing user uploads
        if artifact_id not in session.uploaded_images:
            return False

        # Find and remove from catalog
        for i, artifact in enumerate(session.catalog.artifacts):
            if artifact.artifact_id == artifact_id:
                # Delete the file
                path = Path(artifact.save_path)
                if path.exists():
                    path.unlink()

                # Remove from catalog
                session.catalog.artifacts.pop(i)
                session.catalog.artifact_count -= 1
                session.uploaded_images.remove(artifact_id)
                return True

        return False


# Global image handler instance
image_handler = ImageHandler()
