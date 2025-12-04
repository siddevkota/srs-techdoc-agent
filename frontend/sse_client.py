import requests
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_progress_stream(project_id: str, base_url: str = "http://localhost:8000", timeout: int = 5) -> Optional[Dict[str, Any]]:
    """
    Get one progress update from SSE stream (non-blocking).
    
    Args:
        project_id: Project ID to get progress for
        base_url: Backend URL
        timeout: Timeout in seconds for single read
        
    Returns:
        Progress data dict or None if error/timeout
    """
    url = f"{base_url}/projects/{project_id}/progress-stream"
    
    try:
        # Make request with short timeout
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        
        # Read just the first event (initial state)
        event_type = None
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
                
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    data = json.loads(data_str)
                    response.close()  # Close connection after first event
                    return data
                except json.JSONDecodeError:
                    pass
        
        return None
        
    except requests.exceptions.Timeout:
        logger.debug(f"SSE timeout for project {project_id}")
        return None
    except Exception as e:
        logger.error(f"SSE error: {e}")
        return None
