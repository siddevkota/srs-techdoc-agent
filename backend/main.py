from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import logging
import asyncio
import json
import os
from collections import defaultdict
from queue import Queue
from dotenv import load_dotenv

load_dotenv()

from backend.core.langgraph_pipeline import LangGraphPipeline
from backend.core.models import ProjectMetadata, ParsedSRS
from backend.storage.project_store import ProjectStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SRS Agent API",
    description="AI-powered SRS to Technical Documentation converter with LangGraph multi-agent workflow",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

project_store = ProjectStore()
langgraph_pipeline = LangGraphPipeline()

progress_queues: Dict[str, Queue] = defaultdict(Queue)


class ProjectResponse(BaseModel):
    """Project metadata response."""
    id: str
    name: str
    file_name: str
    file_size: int
    status: str
    uploaded_at: datetime
    progress_message: Optional[str] = None
    current_chunk: Optional[int] = None
    total_chunks: Optional[int] = None
    
    class Config:
        from_attributes = True


class RequirementsResponse(BaseModel):
    """Requirements summary response."""
    functional_count: int
    non_functional_count: int
    user_roles_count: int
    use_cases_count: int
    features_count: int


class ProcessingStatus(BaseModel):
    """Processing status response."""
    project_id: str
    status: str
    message: str
    progress_message: Optional[str] = None
    current_chunk: Optional[int] = None
    total_chunks: Optional[int] = None



@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "SRS Agent API",
        "status": "operational",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Reset any stuck projects on startup."""
    try:
        all_projects = project_store.list_projects()
        stuck_count = 0
        for project in all_projects:
            if project.status in ['processing', 'parsing']:
                project.status = 'error'
                project.progress_message = 'Processing interrupted - backend restarted'
                project_store.save_project(project)
                stuck_count += 1
                logger.warning(f"Reset stuck project: {project.id}")
        
        if stuck_count > 0:
            logger.info(f"Reset {stuck_count} stuck project(s) on startup")
    except Exception as e:
        logger.error(f"Startup reset failed: {e}")


@app.on_event("startup")
async def startup_event():
    """Reset any stuck projects on startup."""
    try:
        all_projects = project_store.list_projects()
        stuck_count = 0
        for project in all_projects:
            if project.status in ['processing', 'parsing']:
                project.status = 'error'
                project.progress_message = 'Processing interrupted - backend restarted'
                project_store.save_project(project)
                stuck_count += 1
                logger.warning(f"Reset stuck project: {project.id}")
        
        if stuck_count > 0:
            logger.info(f"Reset {stuck_count} stuck project(s) on startup")
    except Exception as e:
        logger.error(f"Startup reset failed: {e}")


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "pipeline": "langgraph",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/projects/upload", response_model=ProjectResponse)
async def upload_srs(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload an SRS document and create a project.
    
    Supported formats: PDF, DOCX, MD, TXT
    """
    try:
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
        
        if not file.filename or '.' not in file.filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename. File must have an extension."
            )
        
        file_ext = '.' + file.filename.rsplit('.', 1)[-1].lower()
        logger.info(f"Upload attempt: {file.filename}, extension: {file_ext}")
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
            )
        
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
        
        project_id = str(uuid.uuid4())
        project_name = file.filename.rsplit('.', 1)[0]
        
        project = ProjectMetadata(
            id=project_id,
            name=project_name,
            file_name=file.filename,
            file_size=file_size,
            status="uploaded",
            uploaded_at=datetime.now()
        )
        
        project_store.save_project(project)
        project_store.save_file(project_id, file_content, file.filename)
        
        logger.info(f"Project created: {project_id} - {file.filename}")
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            file_name=project.file_name,
            file_size=project.file_size,
            status=project.status,
            uploaded_at=project.uploaded_at
        )
        
    except HTTPException as he:
        logger.warning(f"Upload rejected: {he.detail} - File: {file.filename if file else 'unknown'}")
        raise
    except Exception as e:
        logger.error(f"Upload failed: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@app.post("/projects/{project_id}/process", response_model=ProcessingStatus)
async def process_project(project_id: str, background_tasks: BackgroundTasks):
    """
    Process an uploaded SRS document.
    
    This triggers the AI pipeline to parse and generate technical documentation.
    """
    try:
        project = project_store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.status == "completed":
            return ProcessingStatus(
                project_id=project_id,
                status="completed",
                message="Project already processed"
            )
        
        # Start processing in background
        background_tasks.add_task(process_project_task, project_id)
        
        # Update status
        project.status = "processing"
        project_store.save_project(project)
        
        return ProcessingStatus(
            project_id=project_id,
            status="processing",
            message="Processing started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process initiation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/progress-stream")
async def stream_progress(project_id: str):
    """
    Stream real-time progress updates using Server-Sent Events.
    Uses sse-starlette for proper SSE implementation.
    """
    async def event_generator():
        """Generate SSE events for progress updates."""
        try:
            # Verify project exists
            project = project_store.get_project(project_id)
            if not project:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Project not found"})
                }
                return
            
            # Get or create queue for this project
            queue = progress_queues[project_id]
            
            # Send initial state
            yield {
                "event": "progress",
                "data": json.dumps({
                    "status": project.status,
                    "progress_message": project.progress_message or "Starting...",
                    "current_chunk": project.current_chunk or 0,
                    "total_chunks": project.total_chunks or 0,
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            max_duration = 300  # 5 minutes
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < max_duration:
                try:
                    try:
                        event = queue.get_nowait()
                        
                        # Send event to client
                        yield {
                            "event": event.get("event", "progress"),
                            "data": json.dumps(event.get("data", {}))
                        }
                        
                        # Stop streaming if completed or error
                        if event.get("data", {}).get("status") in ["completed", "error"]:
                            logger.info(f"SSE stream ending for project {project_id}: {event.get('data', {}).get('status')}")
                            break
                    
                    except:
                        # Queue is empty, wait a bit and send heartbeat
                        await asyncio.sleep(1.5)
                        
                        # Check if project finished while we were waiting
                        project = project_store.get_project(project_id)
                        if project and project.status in ["completed", "error"]:
                            # Send final status and exit
                            yield {
                                "event": "progress",
                                "data": json.dumps({
                                    "status": project.status,
                                    "progress_message": project.progress_message or "Done",
                                    "current_chunk": project.current_chunk or 0,
                                    "total_chunks": project.total_chunks or 0,
                                    "timestamp": datetime.now().isoformat()
                                })
                            }
                            break
                        
                        # Send heartbeat to keep connection alive
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({"timestamp": datetime.now().isoformat()})
                        }
                        
                except Exception as e:
                    logger.error(f"SSE error in loop: {e}")
                    break
                        
        except Exception as e:
            logger.error(f"SSE stream error for {project_id}: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
        finally:
            # Cleanup
            if project_id in progress_queues:
                del progress_queues[project_id]
            logger.debug(f"SSE stream closed for project {project_id}")
    
    return EventSourceResponse(event_generator())


async def process_project_task(project_id: str):
    """Background task to process project - runs in thread pool to avoid blocking."""
    try:
        project = project_store.get_project(project_id)
        logger.info(f"Starting processing for project: {project_id}")
        
        # Update status
        project.status = "parsing"
        project.progress_message = "Starting processing..."
        project_store.save_project(project)
        
        # Get file content
        file_content = project_store.get_file(project_id)
        
        # Create temporary file-like object
        from io import BytesIO
        file_obj = BytesIO(file_content)
        file_obj.name = project.file_name
        
        # Progress callback with SSE broadcasting
        def update_progress(current: int, total: int, message: str):
            """Update project progress and broadcast via SSE."""
            project.current_chunk = current
            project.total_chunks = total
            project.progress_message = message
            project_store.save_project(project)
            logger.info(f"Progress [{current}/{total}]: {message}")
            
            # Broadcast to SSE clients
            if project_id in progress_queues:
                event = {
                    "event": "progress",
                    "data": {
                        "status": project.status,
                        "progress_message": message,
                        "current_chunk": current,
                        "total_chunks": total,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                progress_queues[project_id].put(event)
        
        # Run pipeline in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        logger.info(f"Using LangGraph multi-agent pipeline for {project_id}")
        parsed_srs, tech_doc = await loop.run_in_executor(
            None,
            langgraph_pipeline.run_from_uploaded_file,
            file_obj,
            project.name,
            update_progress
        )
        
        # Update project
        project.parsed_srs = parsed_srs
        project.tech_doc = tech_doc
        project.status = "completed"
        project.progress_message = "✅ Processing completed!"
        project_store.save_project(project)
        
        # Broadcast completion
        if project_id in progress_queues:
            event = {
                "event": "progress",
                "data": {
                    "status": "completed",
                    "progress_message": "✅ Processing completed!",
                    "current_chunk": project.total_chunks or 0,
                    "total_chunks": project.total_chunks or 0,
                    "timestamp": datetime.now().isoformat()
                }
            }
            progress_queues[project_id].put(event)
        
        logger.info(f"Processing completed for project: {project_id}")
        
    except Exception as e:
        logger.error(f"Processing failed for project {project_id}: {e}", exc_info=True)
        project = project_store.get_project(project_id)
        if project:
            project.status = "error"
            project.progress_message = f"❌ Error: {str(e)}"
            project_store.save_project(project)
            
            # Broadcast error
            if project_id in progress_queues:
                event = {
                    "event": "progress",
                    "data": {
                        "status": "error",
                        "progress_message": f"❌ Error: {str(e)}",
                        "current_chunk": project.current_chunk or 0,
                        "total_chunks": project.total_chunks or 0,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                progress_queues[project_id].put(event)


@app.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """Get list of all projects."""
    try:
        projects = project_store.list_projects()
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                file_name=p.file_name,
                file_size=p.file_size,
                status=p.status,
                uploaded_at=p.uploaded_at,
                progress_message=getattr(p, 'progress_message', None),
                current_chunk=getattr(p, 'current_chunk', None),
                total_chunks=getattr(p, 'total_chunks', None)
            )
            for p in projects
        ]
    except Exception as e:
        logger.error(f"List projects failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project details."""
    try:
        project = project_store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            file_name=project.file_name,
            file_size=project.file_size,
            status=project.status,
            uploaded_at=project.uploaded_at,
            progress_message=getattr(project, 'progress_message', None),
            current_chunk=getattr(project, 'current_chunk', None),
            total_chunks=getattr(project, 'total_chunks', None)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get project failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/requirements")
async def get_requirements(project_id: str):
    """Get parsed requirements for a project."""
    try:
        project = project_store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.parsed_srs:
            raise HTTPException(
                status_code=400,
                detail="Project not yet processed"
            )
        
        return project.parsed_srs.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get requirements failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/techdoc")
async def get_techdoc(project_id: str):
    """Get generated technical documentation for a project."""
    try:
        project = project_store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.tech_doc:
            raise HTTPException(
                status_code=400,
                detail="Technical documentation not yet generated"
            )
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "content": project.tech_doc,
            "word_count": len(project.tech_doc.split()),
            "generated_at": project.uploaded_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tech doc failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/pdf")
async def generate_pdf(project_id: str):
    """Generate PDF from technical documentation."""
    try:
        project = project_store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.tech_doc:
            raise HTTPException(
                status_code=400,
                detail="Technical documentation not yet generated"
            )
        
        # Get Homebrew prefix dynamically
        import subprocess
        try:
            brew_prefix = subprocess.check_output(['brew', '--prefix'], text=True).strip()
            lib_path = f"{brew_prefix}/lib"
            if os.path.exists(lib_path):
                os.environ["DYLD_LIBRARY_PATH"] = lib_path
                logger.info(f"Set DYLD_LIBRARY_PATH to: {lib_path}")
        except Exception as e:
            logger.warning(f"Could not get brew prefix: {e}")
        
        # Import PDF generator here to avoid loading WeasyPrint at startup
        from backend.core.pdf_generator import PDFGenerator
        
        # Run PDF generation in thread pool to avoid blocking
        def _generate_pdf():
            pdf_generator = PDFGenerator()
            return pdf_generator.generate_pdf_bytes(project.tech_doc, project.name)
        
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(None, _generate_pdf)
        
        logger.info(f"PDF generated for project: {project_id}, size: {len(pdf_bytes)} bytes, valid: {pdf_bytes.startswith(b'%PDF')}")
        
        # Extract clean project name (remove file extensions like .pdf, .txt, .docx, etc.)
        import re
        clean_name = re.sub(r'\s*-\s*SRS$', '', project.name, flags=re.IGNORECASE)  # Remove " - SRS" suffix
        clean_name = re.sub(r'\.(pdf|txt|docx?|srs)$', '', clean_name, flags=re.IGNORECASE)  # Remove file extensions
        clean_name = clean_name.strip()
        
        # Sanitize filename for header
        safe_filename = clean_name.replace('"', '').replace('/', '-').replace('\\', '-')
        
        # Return PDF as binary response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}_Technical_Documentation.pdf"',
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")


@app.post("/pdf/generate")
async def generate_pdf_from_content(content: str = Body(...), filename: str = Body("document")):
    """Generate PDF from custom markdown content."""
    try:
        # Get Homebrew prefix dynamically
        import subprocess
        try:
            brew_prefix = subprocess.check_output(['brew', '--prefix'], text=True).strip()
            lib_path = f"{brew_prefix}/lib"
            if os.path.exists(lib_path):
                os.environ["DYLD_LIBRARY_PATH"] = lib_path
                logger.info(f"Set DYLD_LIBRARY_PATH to: {lib_path}")
        except Exception as e:
            logger.warning(f"Could not get brew prefix: {e}")
        
        from backend.core.pdf_generator import PDFGenerator
        
        def _generate_pdf():
            pdf_generator = PDFGenerator()
            return pdf_generator.generate_pdf_bytes(content, filename)
        
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(None, _generate_pdf)
        
        safe_filename = filename.replace('"', '').replace('/', '-').replace('\\', '-')
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"PDF generation from content failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")


@app.post("/projects/{project_id}/reset")
async def reset_project(project_id: str):
    """Reset a stuck project to allow reprocessing."""
    try:
        project = project_store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Reset to uploaded state
        project.status = 'uploaded'
        project.progress_message = 'Ready to process'
        project.current_chunk = None
        project.total_chunks = None
        project.parsed_srs = None
        project.tech_doc = None
        project_store.save_project(project)
        
        # Clear progress queue
        if project_id in progress_queues:
            del progress_queues[project_id]
        
        logger.info(f"Reset project: {project_id}")
        return {"message": "Project reset successfully", "status": project.status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset failed for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    try:
        success = project_store.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project deleted: {project_id}")
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete project failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
