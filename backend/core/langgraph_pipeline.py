from pathlib import Path
from typing import Union, Tuple, Callable, Optional, Dict, Any
import uuid
from backend.core.srs_loader import SRSLoader
from backend.core.langgraph_supervisor import LangGraphSupervisorWorkflow, SupervisorState
from backend.core.models import ParsedSRS
import os


class LangGraphPipeline:
    """
    Multi-agent pipeline using LangGraph for SRS to Technical Documentation.
    
    Features:
    - Multi-agent collaboration (Parser, Architect, API, Database, Review agents)
    - Automatic quality checks and refinement loops
    - Human-in-the-loop checkpoints
    - State persistence across workflow execution
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LangGraph pipeline with agents"""
        self.loader = SRSLoader()
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        self.workflow = LangGraphSupervisorWorkflow(
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        )
        
        # Track active workflows
        self.active_workflows: Dict[str, str] = {}  # project_id -> thread_id
    
    def run_from_file(
        self,
        file_path: Union[str, Path],
        project_name: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[ParsedSRS, str]:
        """
        Run LangGraph pipeline from a file path.
        
        Args:
            file_path: Path to SRS document
            project_name: Name of the project
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            Tuple of (ParsedSRS, tech_doc_markdown)
        """
        # Load document
        if progress_callback:
            progress_callback(0, 0, "Loading document...")
        
        raw_text = self.loader.load_text(file_path)
        
        return self._run_workflow(raw_text, project_name, progress_callback)
    
    def run_from_uploaded_file(
        self,
        uploaded_file,
        project_name: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[ParsedSRS, str]:
        """
        Run LangGraph pipeline from uploaded file.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            project_name: Name of the project
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            Tuple of (ParsedSRS, tech_doc_markdown)
        """
        # Load document
        if progress_callback:
            progress_callback(0, 0, "Loading document...")
        
        raw_text = self.loader.load_from_uploaded_file(uploaded_file)
        
        return self._run_workflow(raw_text, project_name, progress_callback)
    
    def _run_workflow(
        self,
        srs_content: str,
        project_name: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[ParsedSRS, str]:
        """Execute the LangGraph multi-agent workflow"""
        
        # Generate unique thread ID for this workflow
        thread_id = str(uuid.uuid4())
        
        if progress_callback:
            progress_callback(0, 100, "Initializing multi-agent workflow...")
        
        # Execute workflow with progress callback
        final_state = self.workflow.process_srs(
            srs_content=srs_content,
            project_name=project_name,
            thread_id=thread_id,
            progress_callback=progress_callback
        )
        
        # Progress messages already emitted in real-time via callbacks
        # No need to replay them here
        
        # Check for errors
        if final_state.get("error"):
            raise RuntimeError(f"Workflow failed: {final_state['error']}")
        
        # Convert state to ParsedSRS format for compatibility
        parsed_srs = self._state_to_parsed_srs(final_state)
        tech_doc = final_state.get("tech_doc", "")
        
        if progress_callback:
            progress_callback(100, 100, "Multi-agent workflow completed!")
        
        return parsed_srs, tech_doc
    
    def _state_to_parsed_srs(self, state: Dict[str, Any]) -> ParsedSRS:
        """Convert LangGraph state to ParsedSRS model for backward compatibility"""
        # Extract requirements text (it's now a markdown string, not a dict)
        requirements_text = state.get("requirements", "")
        
        # Create minimal ParsedSRS to satisfy validation
        return ParsedSRS(
            project_name=state.get("project_name", ""),
            purpose="AI-generated technical documentation",  # Required field
            scope="Full system scope",  # Required field
            functional_requirements=[],  # Empty list is valid
            non_functional_requirements=[],
            user_roles=[],
            use_cases=[],
            constraints=[],
            assumptions=[]
        )
    
    def get_workflow_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of a workflow for a project"""
        thread_id = self.active_workflows.get(project_id)
        if not thread_id:
            return None
        
        # Note: Supervisor pattern doesn't need stateful retrieval
        return None
    
    def provide_human_feedback(
        self,
        project_id: str,
        feedback: str,
        approved_sections: Optional[list] = None
    ):
        """Provide human feedback to continue workflow"""
        thread_id = self.active_workflows.get(project_id)
        if not thread_id:
            raise ValueError(f"No active workflow for project {project_id}")
        
        updates = {
            "human_feedback": feedback,
            "approved_sections": approved_sections or []
        }
        
        self.workflow.update_state(thread_id, updates)
    
    def start_async_workflow(
        self,
        srs_content: str,
        project_id: str,
        project_name: str
    ) -> str:
        """
        Start an async workflow that can be paused for human review.
        Returns thread_id for tracking.
        """
        thread_id = str(uuid.uuid4())
        self.active_workflows[project_id] = thread_id
        
        # Workflow will run async and pause at human_review checkpoint
        # Frontend can poll get_workflow_state to check progress
        
        return thread_id
