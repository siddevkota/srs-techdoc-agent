from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class UserRole(BaseModel):
    """User role definition."""
    name: str = Field(description="Role name (e.g., Admin, Web User)")
    description: str = Field(description="Role description and responsibilities")
    permissions: List[str] = Field(default_factory=list, description="Key permissions")


class FunctionalRequirement(BaseModel):
    """Functional requirement or user story."""
    id: str = Field(description="Requirement identifier")
    title: str = Field(description="Requirement title")
    description: str = Field(description="Detailed description")
    user_story: Optional[str] = Field(None, description="User story format")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    priority: Optional[str] = Field(None, description="Priority level (High/Medium/Low)")
    module: Optional[str] = Field(None, description="Module or feature area")


class NonFunctionalRequirement(BaseModel):
    """Non-functional requirement."""
    category: str = Field(description="NFR category (Performance, Security, etc.)")
    requirement: str = Field(description="Requirement description")
    measurement: Optional[str] = Field(None, description="How to measure/verify")


class TechnologyStackItem(BaseModel):
    """Technology stack component."""
    component: str = Field(description="Component name (Frontend, Backend, Database, etc.)")
    technology: str = Field(description="Technology/framework name")
    version: Optional[str] = Field(None, description="Version if specified")
    justification: Optional[str] = Field(None, description="Why this technology")


class EnvironmentConfig(BaseModel):
    """Environment configuration details."""
    name: str = Field(description="Environment name (Dev, Stage, UAT, Prod)")
    purpose: str = Field(description="Purpose of this environment")
    infrastructure: Optional[str] = Field(None, description="Infrastructure details")
    database_tier: Optional[str] = Field(None, description="Database tier/config")


class UseCase(BaseModel):
    """Detailed use case."""
    title: str = Field(description="Use case title")
    actor: str = Field(description="Primary actor")
    preconditions: List[str] = Field(default_factory=list)
    main_flow: List[str] = Field(default_factory=list)
    postconditions: List[str] = Field(default_factory=list)
    alternate_flows: List[str] = Field(default_factory=list)


class ParsedSRS(BaseModel):
    """Complete parsed SRS structure."""
    
    # Project metadata
    project_name: str = Field(description="Project name")
    purpose: str = Field(description="Project purpose and goals")
    scope: str = Field(description="Project scope")
    intended_audience: List[str] = Field(default_factory=list, description="Target audience")
    
    # Requirements
    functional_requirements: List[FunctionalRequirement] = Field(
        default_factory=list,
        description="All functional requirements and user stories"
    )
    non_functional_requirements: List[NonFunctionalRequirement] = Field(
        default_factory=list,
        description="All non-functional requirements"
    )
    
    # User roles and features
    user_roles: List[UserRole] = Field(default_factory=list)
    product_features: List[str] = Field(default_factory=list, description="High-level features")
    
    # Use cases
    use_cases: List[UseCase] = Field(default_factory=list)
    
    # Technical considerations
    technology_preferences: List[str] = Field(
        default_factory=list,
        description="Any mentioned technology preferences"
    )
    integration_requirements: List[str] = Field(
        default_factory=list,
        description="Third-party integrations needed"
    )
    
    # Additional context
    operating_platforms: List[str] = Field(
        default_factory=list,
        description="Target platforms/browsers"
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Project constraints"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Project assumptions"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Example Platform",
                "purpose": "Educational platform for teachers",
                "scope": "Web application with resource management",
                "functional_requirements": [
                    {
                        "id": "FR-001",
                        "title": "User Login",
                        "description": "Users can log in with email/password",
                        "acceptance_criteria": ["Valid credentials allow access"]
                    }
                ],
                "non_functional_requirements": [
                    {
                        "category": "Performance",
                        "requirement": "Page load time under 3 seconds"
                    }
                ]
            }
        }


class TechDocArtifact(BaseModel):
    """Generated technical documentation artifact."""
    project_name: str
    generated_at: datetime = Field(default_factory=datetime.now)
    markdown_content: str = Field(description="Full technical documentation in Markdown")
    parsed_srs: ParsedSRS = Field(description="Source parsed SRS")
    
    def get_word_count(self) -> int:
        """Get approximate word count of generated documentation."""
        return len(self.markdown_content.split())
    
    def get_section_count(self) -> int:
        """Get number of main sections (h1 and h2 headers)."""
        lines = self.markdown_content.split('\n')
        return sum(1 for line in lines if line.startswith('#'))


class ProjectMetadata(BaseModel):
    """Project metadata for tracking in UI."""
    id: str = Field(description="Unique project identifier")
    name: str = Field(description="Project name")
    uploaded_at: datetime = Field(default_factory=datetime.now)
    file_name: str = Field(description="Original uploaded filename")
    file_size: int = Field(description="File size in bytes")
    status: str = Field(default="uploaded", description="Processing status")
    parsed_srs: Optional[ParsedSRS] = None
    tech_doc: Optional[str] = None
    progress_message: Optional[str] = None
    current_chunk: Optional[int] = None
    total_chunks: Optional[int] = None
    
    def get_status_emoji(self) -> str:
        """Get emoji for current status."""
        status_map = {
            "uploaded": "📄",
            "parsing": "🔄",
            "parsed": "✅",
            "generating": "⚙️",
            "completed": "✨",
            "error": "❌",
        }
        return status_map.get(self.status, "❓")
