import httpx
from typing import List, Dict, Any, Optional
from pathlib import Path
import time


class APIClient:
    """Client for SRS Agent FastAPI backend."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize API client."""
        self.base_url = base_url
        self.timeout = 300.0  # 5 minutes for processing
    
    def health_check(self) -> Dict[str, Any]:
        """Check if backend is healthy."""
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=5.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def upload_file(self, file_path: Path = None, file_bytes: bytes = None, filename: str = None) -> Dict[str, Any]:
        """
        Upload an SRS file to create a project.
        
        Args:
            file_path: Path to file (if uploading from disk)
            file_bytes: File bytes (if uploading from memory)
            filename: Filename to use
        
        Returns:
            Project metadata
        """
        try:
            if file_path:
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.name, f)}
                    response = httpx.post(
                        f"{self.base_url}/projects/upload",
                        files=files,
                        timeout=30.0
                    )
            elif file_bytes and filename:
                files = {'file': (filename, file_bytes)}
                response = httpx.post(
                    f"{self.base_url}/projects/upload",
                    files=files,
                    timeout=30.0
                )
            else:
                raise ValueError("Must provide either file_path or (file_bytes + filename)")
            
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise TimeoutError("Backend is busy processing. Try using progress stream instead.")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Get project failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Get project error: {str(e)}")
    
    def process_project(self, project_id: str) -> Dict[str, Any]:
        """
        Start processing a project (non-blocking).
        
        Args:
            project_id: Project ID
        
        Returns:
            Processing status
        """
        try:
            response = httpx.post(
                f"{self.base_url}/projects/{project_id}/process",
                timeout=5.0  # Quick response since it's just starting the background task
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            # If it times out, the processing likely started anyway
            return {"project_id": project_id, "status": "processing", "message": "Processing started"}
        except httpx.HTTPStatusError as e:
            raise Exception(f"Process failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Process error: {str(e)}")
    
    def get_project(self, project_id: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Get project details.
        
        Args:
            project_id: Project ID
            timeout: Request timeout in seconds
        
        Returns:
            Project metadata
        """
        try:
            response = httpx.get(
                f"{self.base_url}/projects/{project_id}",
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise Exception(f"Get project failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Get project error: {str(e)}")
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        Get list of all projects.
        
        Returns:
            List of project metadata
        """
        try:
            response = httpx.get(
                f"{self.base_url}/projects",
                timeout=10.0  # Reduced timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            # If timeout, return empty list instead of error
            return []
        except Exception as e:
            raise Exception(f"List projects error: {str(e)}")
    
    def get_requirements(self, project_id: str) -> Dict[str, Any]:
        """
        Get parsed requirements for a project.
        
        Args:
            project_id: Project ID
        
        Returns:
            Parsed SRS data
        """
        try:
            response = httpx.get(
                f"{self.base_url}/projects/{project_id}/requirements",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return None
            raise Exception(f"Get requirements failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Get requirements error: {str(e)}")
    
    def get_techdoc(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get generated technical documentation.
        
        Args:
            project_id: Project ID
        
        Returns:
            Technical documentation data
        """
        try:
            response = httpx.get(
                f"{self.base_url}/projects/{project_id}/techdoc",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return None
            raise Exception(f"Get tech doc failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Get tech doc error: {str(e)}")
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project ID
        
        Returns:
            True if successful
        """
        try:
            response = httpx.delete(
                f"{self.base_url}/projects/{project_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise Exception(f"Delete project failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Delete project error: {str(e)}")
    
    def generate_pdf(self, project_id: str) -> bytes:
        """
        Generate PDF for a project.
        
        Args:
            project_id: Project ID
        
        Returns:
            PDF bytes
        """
        try:
            # Use follow_redirects in case of any redirects
            response = httpx.post(
                f"{self.base_url}/projects/{project_id}/pdf",
                timeout=60.0,  # PDF generation can take time
                follow_redirects=True
            )
            response.raise_for_status()
            
            pdf_bytes = response.content
            
            # Validate PDF
            if not pdf_bytes or len(pdf_bytes) < 100:
                raise Exception(f"PDF too small or empty: {len(pdf_bytes)} bytes")
            
            if not pdf_bytes.startswith(b'%PDF'):
                # Show what we actually got
                preview = pdf_bytes[:50].decode('utf-8', errors='replace')
                raise Exception(f"Invalid PDF format. Received: {preview}")
            
            return pdf_bytes
            
        except httpx.HTTPStatusError as e:
            error_text = e.response.text if hasattr(e.response, 'text') else str(e)
            raise Exception(f"PDF generation failed: {error_text}")
        except Exception as e:
            raise Exception(f"PDF generation error: {str(e)}")
    
    def generate_pdf_from_content(self, content: str, filename: str = "document") -> bytes:
        """
        Generate PDF from markdown content.
        
        Args:
            content: Markdown content
            filename: Filename for the PDF
        
        Returns:
            PDF bytes
        """
        try:
            response = httpx.post(
                f"{self.base_url}/pdf/generate",
                json={"content": content, "filename": filename},
                timeout=60.0
            )
            response.raise_for_status()
            
            pdf_bytes = response.content
            
            if not pdf_bytes or len(pdf_bytes) < 100:
                raise Exception(f"PDF too small or empty: {len(pdf_bytes)} bytes")
            
            if not pdf_bytes.startswith(b'%PDF'):
                raise Exception("Invalid PDF format")
            
            return pdf_bytes
            
        except httpx.HTTPStatusError as e:
            error_text = e.response.text if hasattr(e.response, 'text') else str(e)
            raise Exception(f"PDF generation failed: {error_text}")
        except Exception as e:
            raise Exception(f"PDF generation error: {str(e)}")
    
    def reset_project(self, project_id: str) -> Dict[str, Any]:
        """
        Reset a stuck project to allow reprocessing.
        
        Args:
            project_id: Project ID to reset
        
        Returns:
            Reset confirmation message
        """
        try:
            response = httpx.post(
                f"{self.base_url}/projects/{project_id}/reset",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Reset project error: {str(e)}")
    
    def wait_for_completion(self, project_id: str, check_interval: float = 2.0, max_wait: float = 300.0) -> str:
        """
        Wait for project processing to complete.
        
        Args:
            project_id: Project ID
            check_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
        
        Returns:
            Final status ('completed' or 'error')
        """
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait:
            project = self.get_project(project_id)
            if not project:
                raise Exception("Project not found")
            
            status = project['status']
            
            if status in ['completed', 'error']:
                return status
            
            time.sleep(check_interval)
        
        raise TimeoutError(f"Processing did not complete within {max_wait} seconds")
