import streamlit as st
import time
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.api.client import APIClient
from frontend.sse_client import get_progress_stream


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def init_session_state():
    """Initialize session state."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    if 'processing_project_id' not in st.session_state:
        st.session_state.processing_project_id = None
    if 'monitoring' not in st.session_state:
        st.session_state.monitoring = False


def get_live_progress(project_id: str) -> dict:
    """Get latest progress - non-blocking, always returns cached or new data."""
    cache_key = f'progress_cache_{project_id}'
    
    if cache_key not in st.session_state:
        st.session_state[cache_key] = {
            "status": "processing",
            "progress_message": "Connecting to backend...",
            "current_chunk": 0,
            "total_chunks": 0
        }
    
    try:
        progress = get_progress_stream(project_id, timeout=1)
        if progress and isinstance(progress, dict):
            st.session_state[cache_key].update(progress)
    except Exception:
        pass
    
    return st.session_state[cache_key]


@st.fragment(run_every=2)
def monitor_processing_inline():
    """Fragment that shows inline progress below upload section."""
    project_id = st.session_state.get('processing_project_id')
    if not project_id or not st.session_state.get('monitoring', False):
        return
    
    progress = get_live_progress(project_id)
    
    status = progress.get('status', 'processing')
    msg = progress.get('progress_message', 'Processing...')
    current = progress.get('current_chunk', 0)
    total = progress.get('total_chunks', 0)
    
    if total > 0 and current > 0:
        progress_val = current / total
        st.progress(progress_val, text=f"{msg}")
    else:
        st.progress(0, text=msg)
    
    # Check if done
    if status == 'completed':
        st.session_state.monitoring = False
        # Auto-show result
        st.session_state.selected_project_id = project_id
        st.session_state.processing_project_id = None
        st.switch_page("pages/projects.py")
    elif status == 'error':
        st.session_state.monitoring = False
        st.session_state.processing_project_id = None
        st.error(f"❌ Error: {msg}")
        st.rerun()


init_session_state()

st.title("SRS to Technical Documentation")
st.caption("Upload your Software Requirements Specification document")

st.divider()

st.subheader("Upload Document")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "docx", "doc", "txt", "md"],
    help="Supported: PDF, DOCX, TXT, MD"
)

if uploaded_file:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.text(f"File: {uploaded_file.name}")
        st.text(f"Size: {format_file_size(uploaded_file.size)}")
    
    with col2:
        if st.button("Process", use_container_width=True, type="primary"):
            with st.spinner("Uploading..."):
                # Upload and start processing
                file_bytes = uploaded_file.read()
                uploaded_file.seek(0)
                
                response = st.session_state.api_client.upload_file(
                    file_bytes=file_bytes,
                    filename=uploaded_file.name
                )
                project_id = response['id']
                
                # Store project name
                st.session_state[f'project_name_{project_id}'] = uploaded_file.name
                
                # Initialize progress cache
                cache_key = f'progress_cache_{project_id}'
                st.session_state[cache_key] = {
                    "status": "processing",
                    "progress_message": "Starting processing...",
                    "current_chunk": 0,
                    "total_chunks": 0
                }
                
                # Start processing
                try:
                    st.session_state.api_client.process_project(project_id)
                except:
                    pass
                
                # Set monitoring
                st.session_state.processing_project_id = project_id
                st.session_state.monitoring = True
                st.rerun()

# Show inline progress if processing
if st.session_state.get('monitoring', False) and st.session_state.get('processing_project_id'):
    st.divider()
    monitor_processing_inline()
