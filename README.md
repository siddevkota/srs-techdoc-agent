# SRS to Technical Document Agent

AI-powered tool that converts Software Requirements Specification (SRS) documents into comprehensive technical documentation using a multi-agent LangGraph workflow.

## Problem Statement

Converting SRS documents into detailed technical documentation is time-consuming and requires deep analysis. This tool automates the process using AI agents to parse requirements and generate structured technical documentation with architecture diagrams, API specifications, and database schemas.

## Features

- **Multi-format Support** - Upload SRS documents in PDF, DOCX, TXT, or Markdown
- **Multi-Agent AI System** - Uses LangGraph to orchestrate parallel worker agents for faster processing
- **Comprehensive Analysis** - Extracts functional/non-functional requirements, user roles, and use cases
- **Technical Documentation** - Generates architecture diagrams, API specs, and database schemas with Mermaid.js
- **Real-time Progress** - Live SSE streaming shows detailed progress during document analysis
- **Export Options** - Download as Markdown or PDF with rendered diagrams
- **Project Management** - Organize and track multiple SRS documents

## Tech Stack

- **Backend** - FastAPI with SSE streaming, Python 3.10+
- **Frontend** - Streamlit with multi-page navigation
- **AI Framework** - LangGraph with OpenAI (gpt-4o-mini)
- **PDF Generation** - WeasyPrint
- **Diagrams** - Mermaid.js

## Prerequisites

- Python 3.10+
- OpenAI API key
- System dependencies for PDF generation (macOS):
  ```bash
  brew install pango gdk-pixbuf libffi
  ```

## Setup

```bash
# Clone or navigate to project directory
cd srs-techdoc-agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create a .env file in the project root with:
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

## Running the Application

**Terminal 1 - Backend:**
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
source .venv/bin/activate
streamlit run frontend/app.py
```

### Access the Application
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Environment Variables

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (with defaults)
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3
```

## If Error:

- Use AI to debug

## LangGraph Architecture

### Workflow Graph

```
                    [START]
                       │
                       ▼
         ┌──────────────────────────┐
         │  PARALLEL WORKERS NODE   │
         │  (ThreadPoolExecutor)    │
         └─────────┬────────────────┘
                   │
       ┌───────────┼───────────┬───────────┐
       │           │           │           │
       ▼           ▼           ▼           ▼
  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Req.   │ │ System   │ │ Software │ │ Database │
  │ Parser │ │ Arch.    │ │ Arch.    │ │ Designer │
  └────────┘ └──────────┘ └──────────┘ └──────────┘
       │           │           │           │
       └───────────┼───────────┴───────────┘
                   │
                   ▼
            ┌─────────────┐
            │  COMPILER   │
            │    NODE     │
            └──────┬──────┘
                   │
                   ▼
                 [END]
```

**Simple Linear Flow:**

1. **Parallel Workers Node** - Runs 4 workers simultaneously using ThreadPoolExecutor:
   - Requirements Parser - Extracts functional/non-functional requirements
   - Architecture Designer - Creates system architecture and tech stack
   - Software Architect - Documents technical specifications and folder structure
   - Database Designer - Generates database schemas and ERD diagrams

2. **Compiler Node** - Combines all worker outputs into final documentation

All workers process the full SRS content simultaneously for comprehensive analysis, then results are compiled into structured markdown.

------------------------------------------
Created to learn!