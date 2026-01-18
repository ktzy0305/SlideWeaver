"""Session management for multi-user support."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from core.config import CATALOG_PATH, SESSIONS_DIR

if TYPE_CHECKING:
    from core.schemas import ArtifactCatalog


@dataclass
class Session:
    """Represents a user session with isolated workspace."""

    session_id: str
    created_at: datetime
    session_dir: Path
    catalog: ArtifactCatalog
    uploaded_images: list[str] = field(default_factory=list)

    @property
    def uploads_dir(self) -> Path:
        """Directory for uploaded images."""
        return self.session_dir / "uploads"

    @property
    def output_dir(self) -> Path:
        """Directory for generated output."""
        return self.session_dir / "output"

    @property
    def catalog_path(self) -> Path:
        """Path to session-specific catalog."""
        return self.session_dir / "catalog.json"


class SessionManager:
    """Manages user sessions with isolated workspaces."""

    def __init__(
        self,
        base_dir: Path = SESSIONS_DIR,
        base_catalog_path: Path = CATALOG_PATH,
    ):
        self.base_dir = base_dir
        self.base_catalog_path = base_catalog_path
        self._sessions: dict[str, Session] = {}
        self._base_catalog: ArtifactCatalog | None = None

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _load_base_catalog(self) -> ArtifactCatalog:
        """Load and cache the base catalog."""
        if self._base_catalog is None:
            from core.schemas import ArtifactCatalog

            if self.base_catalog_path.exists():
                with open(self.base_catalog_path) as f:
                    data = json.load(f)
                self._base_catalog = ArtifactCatalog(**data)
            else:
                # Empty catalog if base doesn't exist
                self._base_catalog = ArtifactCatalog(artifact_count=0, artifacts=[])
        return self._base_catalog

    def _create_session_catalog(self) -> ArtifactCatalog:
        """Create a session-specific catalog starting with base artifacts."""
        from core.schemas import ArtifactCatalog

        base = self._load_base_catalog()
        # Deep copy base catalog
        return ArtifactCatalog(
            artifact_count=base.artifact_count,
            artifacts=[a.model_copy() for a in base.artifacts],
        )

    def create_session(self) -> Session:
        """Create a new session with isolated directories."""
        session_id = str(uuid.uuid4())
        session_dir = self.base_dir / session_id

        # Create session directories
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "uploads").mkdir(exist_ok=True)
        (session_dir / "output").mkdir(exist_ok=True)

        # Initialize session catalog
        catalog = self._create_session_catalog()

        session = Session(
            session_id=session_id,
            created_at=datetime.now(),
            session_dir=session_dir,
            catalog=catalog,
        )

        # Save initial catalog to session directory
        self._save_session_catalog(session)

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get an existing session by ID."""
        return self._sessions.get(session_id)

    def _save_session_catalog(self, session: Session) -> None:
        """Save the session catalog to disk."""
        session.catalog_path.write_text(
            session.catalog.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def update_catalog(self, session: Session) -> None:
        """Update the session catalog on disk."""
        self._save_session_catalog(session)

    def cleanup_session(self, session_id: str) -> bool:
        """Remove session and all associated files."""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            try:
                shutil.rmtree(session.session_dir, ignore_errors=True)
                return True
            except Exception:
                return False
        return False

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Remove sessions older than max_age_hours."""
        cleaned = 0
        cutoff = datetime.now()
        to_remove = []

        for session_id, session in self._sessions.items():
            age = (cutoff - session.created_at).total_seconds() / 3600
            if age > max_age_hours:
                to_remove.append(session_id)

        for session_id in to_remove:
            if self.cleanup_session(session_id):
                cleaned += 1

        return cleaned


# Global session manager instance
session_manager = SessionManager()
