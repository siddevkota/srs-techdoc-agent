import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.api.client import APIClient
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api = APIClient()


def refine_with_ai(current_content: str, user_prompt: str) -> str:
    """Use LLM to refine documentation based on user prompt."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical documentation expert. You will receive a complete technical document and user instructions to modify it. Your task is to return the COMPLETE MODIFIED DOCUMENT with all sections intact. Never return only a portion of the document - always return the entire document from start to finish with the requested changes applied."
                },
                {
                    "role": "user",
                    "content": f"""Here is the COMPLETE technical documentation:

{current_content}

User's modification request: {user_prompt}

IMPORTANT: Return the ENTIRE document with all sections, making only the changes requested above. Do not truncate or omit any sections. Return the complete modified document as markdown without any explanations or wrapper text."""
                }
            ],
            temperature=0.7,
        )
        
        refined = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if the LLM wrapped the output
        if refined.startswith("```markdown"):
            refined = refined[len("```markdown"):].strip()
        if refined.startswith("```"):
            refined = refined[3:].strip()
        if refined.endswith("```"):
            refined = refined[:-3].strip()
        
        return refined
    except Exception as e:
        st.error(f"AI refinement failed: {str(e)}")
        return current_content


def render_project_card(project):
    """Render an appealing project card"""
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([6, 2, 1, 1])
        
        with col1:
            st.markdown(f"### {project['name']}")
            if project.get('file_name'):
                st.caption(f"📄 {project['file_name']}")
        
        with col2:
            status = project["status"]
            if status == "completed":
                st.success("✅ Completed")
            elif status == "processing":
                st.info("⏳ Processing")
            else:
                st.error("❌ Failed")
        
        with col3:
            if status == "completed":
                if st.button("View", key=f"view_{project['id']}", use_container_width=True):
                    st.session_state.selected_project_id = project["id"]
                    st.rerun()
        
        with col4:
            if st.button("Delete", key=f"delete_{project['id']}", use_container_width=True, help="Delete project"):
                if api.delete_project(project['id']):
                    st.rerun()
                else:
                    st.error("Failed to delete")


def render_project_details(project_id: str):
    """Result display with review and edit capabilities"""
    try:
        project = api.get_project(project_id)
        srs = api.get_requirements(project_id)
        tech_doc = api.get_techdoc(project_id)
        md_content = tech_doc.get("content", "") if isinstance(tech_doc, dict) else tech_doc
        
        # Initialize edit mode state
        if f'edit_mode_{project_id}' not in st.session_state:
            st.session_state[f'edit_mode_{project_id}'] = False
        if f'edited_content_{project_id}' not in st.session_state:
            st.session_state[f'edited_content_{project_id}'] = md_content
        
        # Back button
        if st.button("← Back to Projects"):
            if "selected_project_id" in st.session_state:
                del st.session_state.selected_project_id
            st.rerun()
        
        st.title(project['name'])
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.session_state[f'edit_mode_{project_id}']:
                if st.button("Preview", use_container_width=True):
                    st.session_state[f'edit_mode_{project_id}'] = False
                    st.rerun()
            else:
                if st.button("Edit", use_container_width=True):
                    st.session_state[f'edit_mode_{project_id}'] = True
                    st.rerun()
        
        with col2:
            if st.button("AI Refine", use_container_width=True):
                st.session_state[f'show_ai_prompt_{project_id}'] = True
                st.rerun()
        
        with col3:
            current_content = st.session_state[f'edited_content_{project_id}']
            st.download_button(
                "Download MD",
                data=current_content,
                file_name=f"{project['name']}_techdoc.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col4:
            # Auto-generate and download PDF
            current_content = st.session_state[f'edited_content_{project_id}']
            
            # Generate PDF on first load or if content changed
            if f'pdf_bytes_{project_id}' not in st.session_state or \
               f'last_content_{project_id}' not in st.session_state or \
               st.session_state[f'last_content_{project_id}'] != current_content:
                try:
                    with st.spinner("Generating PDF..."):
                        pdf_bytes = api.generate_pdf_from_content(current_content, f"{project['name']}_techdoc")
                        st.session_state[f'pdf_bytes_{project_id}'] = pdf_bytes
                        st.session_state[f'last_content_{project_id}'] = current_content
                except Exception as e:
                    st.error(f"PDF generation failed: {str(e)}")
            
            # Show download button
            if f'pdf_bytes_{project_id}' in st.session_state:
                st.download_button(
                    "Download PDF",
                    data=st.session_state[f'pdf_bytes_{project_id}'],
                    file_name=f"{project['name']}_techdoc.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        
        st.divider()
        
        # AI Refine prompt area
        if st.session_state.get(f'show_ai_prompt_{project_id}', False):
            with st.container(border=True):
                st.markdown("### AI Refinement")
                ai_prompt = st.text_area(
                    "What would you like to change?",
                    placeholder="e.g., Add more details to the API section, Simplify the architecture diagram, etc.",
                    height=100
                )
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("Apply Changes", type="primary"):
                        if ai_prompt:
                            with st.spinner("AI is refining the documentation..."):
                                # Call LLM to refine content
                                refined_content = refine_with_ai(
                                    st.session_state[f'edited_content_{project_id}'],
                                    ai_prompt
                                )
                                st.session_state[f'edited_content_{project_id}'] = refined_content
                                st.session_state[f'show_ai_prompt_{project_id}'] = False
                                st.success("Changes applied!")
                                st.rerun()
                        else:
                            st.error("Please enter your instructions")
                
                with col2:
                    if st.button("Cancel"):
                        st.session_state[f'show_ai_prompt_{project_id}'] = False
                        st.rerun()
            
            st.divider()
        
        # Edit mode or preview
        if st.session_state[f'edit_mode_{project_id}']:
            st.markdown("### Edit Documentation")
            edited = st.text_area(
                "Edit the content below:",
                value=st.session_state[f'edited_content_{project_id}'],
                height=600,
                key=f"editor_{project_id}"
            )
            
            if edited != st.session_state[f'edited_content_{project_id}']:
                st.session_state[f'edited_content_{project_id}'] = edited
                st.success("Changes saved locally")
        else:
            st.divider()
        
        import re
        
        # Use edited content if available
        display_content = st.session_state[f'edited_content_{project_id}']
        
        # Split content by mermaid blocks
        parts = re.split(r'(```mermaid\n.*?```)', display_content, flags=re.DOTALL)
        
        for i, part in enumerate(parts):
            if part.startswith('```mermaid'):
                # Extract mermaid code
                mermaid_code = part.replace('```mermaid\n', '').replace('```', '').strip()
                # Render using HTML with mermaid.js with proper scaling
                html_code = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <script type="module">
                        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                        mermaid.initialize({{ 
                            startOnLoad: true, 
                            theme: 'default',
                            flowchart: {{ useMaxWidth: true, htmlLabels: true }}
                        }});
                    </script>
                    <style>
                        html, body {{ 
                            margin: 0; 
                            padding: 0; 
                            overflow: hidden;
                            width: 100%;
                            height: 100%;
                        }}
                        .mermaid {{ 
                            display: flex; 
                            justify-content: center;
                            align-items: center;
                            width: 100%;
                            height: 100%;
                            padding: 10px;
                            box-sizing: border-box;
                        }}
                        .mermaid svg {{
                            max-width: 100% !important;
                            max-height: 100% !important;
                            width: auto !important;
                            height: auto !important;
                        }}
                    </style>
                </head>
                <body>
                    <div class="mermaid">
                    {mermaid_code}
                    </div>
                </body>
                </html>
                """
                st.components.v1.html(html_code, height=500)
            else:
                # Regular markdown
                if part.strip():
                    st.markdown(part)
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        if st.button("← Back"):
            if "selected_project_id" in st.session_state:
                del st.session_state.selected_project_id
            st.rerun()


# Check if viewing specific project
if "selected_project_id" in st.session_state:
    render_project_details(st.session_state.selected_project_id)
else:
    # Project list
    st.title("Project History")
    
    try:
        projects = api.list_projects()
        
        if not projects:
            st.info("🎯 No projects yet. Upload a document to get started!")
            if st.button("Upload Document"):
                st.switch_page("pages/home.py")
        else:
            st.caption(f"Total: {len(projects)} project(s)")
            st.write("")  # spacing
            
            for project in projects:
                render_project_card(project)
                st.write("")  # spacing between cards
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
