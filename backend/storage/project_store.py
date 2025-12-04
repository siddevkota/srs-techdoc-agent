from typing import Dict, Optional, List
from pathlib import Path
import json
import pickle
from datetime import datetime
import sys

from backend.core.models import ProjectMetadata
import backend.core
import backend.core.models


class ProjectStore:
    """
    Simple in-memory storage for projects with file persistence.
    Can be replaced with database in production.
    """
    
    def __init__(self, storage_dir: str = "backend/storage/data"):
        """Initialize project store."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.projects: Dict[str, ProjectMetadata] = {}
        self.files: Dict[str, bytes] = {}
        
        # Load existing projects
        self._load_projects()
    
    def save_project(self, project: ProjectMetadata) -> None:
        """Save project metadata."""
        self.projects[project.id] = project
        self._persist_project(project)
    
    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """Get project by ID."""
        return self.projects.get(project_id)
    
    def list_projects(self) -> List[ProjectMetadata]:
        """Get all projects sorted by upload date."""
        return sorted(
            self.projects.values(),
            key=lambda p: p.uploaded_at,
            reverse=True
        )
    
    def delete_project(self, project_id: str) -> bool:
        """Delete project and associated files."""
        if project_id not in self.projects:
            return False
        
        # Remove from memory
        del self.projects[project_id]
        if project_id in self.files:
            del self.files[project_id]
        
        # Remove from disk
        project_file = self.storage_dir / f"{project_id}.pkl"
        file_path = self.storage_dir / f"{project_id}_file.bin"
        
        if project_file.exists():
            project_file.unlink()
        if file_path.exists():
            file_path.unlink()
        
        return True
    
    def save_file(self, project_id: str, content: bytes, filename: str) -> None:
        """Save uploaded file content."""
        self.files[project_id] = content
        
        # Persist to disk
        file_path = self.storage_dir / f"{project_id}_file.bin"
        with open(file_path, 'wb') as f:
            f.write(content)
    
    def get_file(self, project_id: str) -> Optional[bytes]:
        """Get uploaded file content."""
        # Try memory first
        if project_id in self.files:
            return self.files[project_id]
        
        # Load from disk
        file_path = self.storage_dir / f"{project_id}_file.bin"
        if file_path.exists():
            with open(file_path, 'rb') as f:
                content = f.read()
                self.files[project_id] = content
                return content
        
        return None
    
    def _persist_project(self, project: ProjectMetadata) -> None:
        """Persist project to disk."""
        project_file = self.storage_dir / f"{project.id}.pkl"
        with open(project_file, 'wb') as f:
            pickle.dump(project, f)
    
    def _load_projects(self) -> None:
        """Load all projects from disk."""
        if not self.storage_dir.exists():
            return
        
        # Map old 'app' module to new 'backend.core' for backward compatibility
        sys.modules['app'] = backend.core
        sys.modules['app.models'] = backend.core.models
        
        for project_file in self.storage_dir.glob("*.pkl"):
            try:
                with open(project_file, 'rb') as f:
                    project = pickle.load(f)
                    self.projects[project.id] = project
            except Exception as e:
                print(f"Failed to load project {project_file}: {e}")
                # Delete corrupted project file
                try:
                    project_file.unlink()
                    print(f"Deleted corrupted project file: {project_file}")
                except:
                    pass
    
    def clear_all(self) -> None:
        """Clear all projects (for testing)."""
        self.projects.clear()
        self.files.clear()
        
        # Clear disk storage
        for file in self.storage_dir.glob("*"):
            if file.is_file():
                file.unlink()
