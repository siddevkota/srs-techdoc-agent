from weasyprint import HTML, CSS
from typing import Optional
import os
import re
import base64
from datetime import datetime
import subprocess
import tempfile
from pathlib import Path


class PDFGenerator:
    """Generate professional PDFs from technical documentation."""
    
    def __init__(self):
        """Initialize PDF generator."""
        self.css_style = self._get_css_style()
    
    def _get_css_style(self) -> str:
        """Get minimal, professional CSS styling for PDF."""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: counter(page);
                font-size: 9pt;
                color: #888;
            }
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #2c3e50;
            background: white;
        }
        
        h1 {
            color: #1a1a1a;
            font-size: 24pt;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 0.8cm;
            padding-bottom: 0.3cm;
            border-bottom: 1px solid #e1e4e8;
            page-break-after: avoid;
        }
        
        h2 {
            color: #2c3e50;
            font-size: 16pt;
            font-weight: 600;
            margin-top: 1.2cm;
            margin-bottom: 0.4cm;
            page-break-after: avoid;
        }
        
        h3 {
            color: #34495e;
            font-size: 13pt;
            font-weight: 600;
            margin-top: 0.8cm;
            margin-bottom: 0.3cm;
            page-break-after: avoid;
        }
        
        h4 {
            color: #4a5568;
            font-size: 11pt;
            font-weight: 600;
            margin-top: 0.6cm;
            margin-bottom: 0.3cm;
            page-break-after: avoid;
        }
        
        p {
            margin-bottom: 0.4cm;
            text-align: left;
        }
        
        ul, ol {
            margin-bottom: 0.4cm;
            padding-left: 1.2cm;
        }
        
        li {
            margin-bottom: 0.15cm;
        }
        
        code {
            background-color: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
            font-size: 9pt;
            color: #24292e;
        }
        
        pre {
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 4px;
            padding: 0.4cm;
            page-break-inside: avoid;
            margin-bottom: 0.5cm;
        }
        
        pre code {
            background-color: transparent;
            padding: 0;
            color: #24292e;
            font-size: 8.5pt;
        }
        
        /* WeasyPrint-compatible table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 0.8cm;
            margin-top: 0.4cm;
            font-size: 9pt;
            border: 1px solid #d0d7de;
            page-break-inside: auto;
        }
        
        thead {
            display: table-header-group;
        }
        
        tbody {
            display: table-row-group;
        }
        
        tr {
            page-break-inside: avoid;
            page-break-after: auto;
        }
        
        th {
            background-color: #f6f8fa;
            color: #24292e;
            font-weight: 600;
            padding: 8px 12px;
            text-align: left;
            border: 1px solid #d0d7de;
            vertical-align: middle;
        }
        
        td {
            padding: 8px 12px;
            border: 1px solid #d0d7de;
            vertical-align: top;
            word-wrap: break-word;
        }
        
        tr:nth-child(even) {
            background-color: #f6f8fa;
        }
        
        blockquote {
            border-left: 3px solid #dfe2e5;
            padding-left: 0.5cm;
            margin-left: 0;
            margin-right: 0;
            color: #6a737d;
        }
        
        .cover-page {
            text-align: center;
            padding-top: 8cm;
            page-break-after: always;
        }
        
        .cover-title {
            font-size: 32pt;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 0.5cm;
        }
        
        .cover-subtitle {
            font-size: 16pt;
            color: #6a737d;
            margin-bottom: 3cm;
            font-weight: 400;
        }
        
        .cover-info {
            font-size: 10pt;
            color: #959da5;
        }
        
        hr {
            border: none;
            border-top: 1px solid #e1e4e8;
            margin: 1cm 0;
        }
        """
    
    def _check_mermaid_cli(self) -> bool:
        """Check if mermaid-cli is installed."""
        try:
            result = subprocess.run(['mmdc', '--version'], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def _render_mermaid_to_image(self, mermaid_code: str) -> Optional[str]:
        """Render mermaid diagram to base64 encoded PNG."""
        mmd_file_path = None
        output_path = None
        
        try:
            # Use mermaid-cli (mmdc) to convert to image
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as mmd_file:
                mmd_file.write(mermaid_code)
                mmd_file_path = mmd_file.name
            
            output_path = mmd_file_path.replace('.mmd', '.png')
            
            # Run mmdc command
            result = subprocess.run(
                ['mmdc', '-i', mmd_file_path, '-o', output_path, '-b', 'transparent'],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                
                # Cleanup
                os.unlink(mmd_file_path)
                os.unlink(output_path)
                
                return f"data:image/png;base64,{img_data}"
            
        except Exception:
            pass
        
        # Cleanup on failure
        try:
            if mmd_file_path and os.path.exists(mmd_file_path):
                os.unlink(mmd_file_path)
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)
        except:
            pass
        
        return None
    
    def _replace_mermaid_with_images(self, markdown_content: str) -> str:
        """Replace mermaid code blocks with rendered images."""
        # Check if mermaid-cli is available
        if not self._check_mermaid_cli():
            # Keep mermaid as code blocks if mmdc not available
            return markdown_content
        
        def replace_mermaid(match):
            mermaid_code = match.group(1)
            img_data = self._render_mermaid_to_image(mermaid_code)
            
            if img_data:
                return f'<img src="{img_data}" style="max-width: 100%; height: auto; margin: 1cm 0;" />'
            else:
                # Fallback to code block if rendering fails
                return f'<pre><code>{mermaid_code}</code></pre>'
        
        pattern = r'```mermaid\n(.*?)```'
        return re.sub(pattern, replace_mermaid, markdown_content, flags=re.DOTALL)
    
    def markdown_to_html(self, markdown_content: str, project_name: str) -> str:
        """Convert markdown to styled HTML."""
        import markdown
        from markdown.extensions import tables, fenced_code, codehilite
        
        # Replace mermaid diagrams with images
        markdown_content = self._replace_mermaid_with_images(markdown_content)
        
        # Add minimal cover page matching sample format
        current_date = datetime.now().strftime("%B %d, %Y")
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{project_name} - Technical Documentation</title>
        </head>
        <body>
            <div class="cover-page">
                <div class="cover-title">{project_name}</div>
                <div class="cover-subtitle">Technical Documentation</div>
            </div>
        """
        
        # Convert markdown to HTML
        md = markdown.Markdown(extensions=['tables', 'fenced_code', 'codehilite'])
        content_html = md.convert(markdown_content)
        
        html += content_html
        html += """
        </body>
        </html>
        """
        
        return html
    
    def generate_pdf(
        self,
        markdown_content: str,
        output_path: str,
        project_name: str = "Project"
    ) -> str:
        """
        Generate PDF from markdown content.
        
        Args:
            markdown_content: Markdown text to convert
            output_path: Path where PDF should be saved
            project_name: Name of the project for cover page
        
        Returns:
            Path to generated PDF file
        """
        try:
            # Convert markdown to HTML
            html_content = self.markdown_to_html(markdown_content, project_name)
            
            # Generate PDF
            HTML(string=html_content).write_pdf(
                output_path,
                stylesheets=[CSS(string=self.css_style)]
            )
            
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate PDF: {str(e)}")
    
    def generate_pdf_bytes(
        self,
        markdown_content: str,
        project_name: str = "Project"
    ) -> bytes:
        """
        Generate PDF as bytes without saving to disk.
        
        Args:
            markdown_content: Markdown text to convert
            project_name: Name of the project for cover page
        
        Returns:
            PDF file as bytes
        """
        try:
            # Convert markdown to HTML
            html_content = self.markdown_to_html(markdown_content, project_name)
            
            # Generate PDF bytes
            pdf_bytes = HTML(string=html_content).write_pdf(
                stylesheets=[CSS(string=self.css_style)]
            )
            
            # Validate PDF
            if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
                raise RuntimeError("Generated PDF is invalid or empty")
            
            if len(pdf_bytes) < 1000:
                raise RuntimeError(f"Generated PDF is suspiciously small: {len(pdf_bytes)} bytes")
            
            return pdf_bytes
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate PDF: {str(e)}")
