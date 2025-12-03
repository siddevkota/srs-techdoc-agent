# SRS to Technical Document Agent

AI-powered tool that converts Software Requirements Specification (SRS) documents into comprehensive technical documentation.

## Problem Statement

Converting SRS documents into detailed technical documentation is time-consuming and requires deep analysis. This tool automates the process using AI to parse requirements and generate structured technical documentation with architecture diagrams, API specifications, and database schemas.

## Features

- **Multi-format Support** - Upload SRS documents in PDF, DOCX, TXT, or Markdown
- **AI-Powered Analysis** - Automatically extracts functional/non-functional requirements, user roles, and use cases
- **Technical Documentation** - Generates complete tech docs with architecture diagrams, API specs, and database schemas
- **Human-in-the-Loop** - Edit documentation manually or refine with AI prompts
- **Export Options** - Download as Markdown or PDF with rendered diagrams
- **Real-time Processing** - Live progress tracking during document analysis

## Tech Stack

- **Backend** - FastAPI, Python 3.10+
- **Frontend** - Streamlit
- **AI** - OpenAI
- **PDF Generation** - WeasyPrint
- **Diagrams** - Mermaid.js

## How to Run

### Prerequisites

- Python 3.10+
- OpenAI API key
- System dependencies for PDF generation:
  ```bash
  # macOS
  brew install pango gdk-pixbuf libffi
  ```

### Setup

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env file
```

### Run

```bash
# Terminal 1 - Start backend
cd srs_agent
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 - Start frontend
cd srs_agent
source .venv/bin/activate
streamlit run frontend/app.py
```

Open `http://localhost:8501` in your browser and upload an SRS document to get started.
