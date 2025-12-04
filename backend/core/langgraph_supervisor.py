from typing import TypedDict, List, Dict, Any, Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import concurrent.futures
import json


class SupervisorState(TypedDict):
    """Streamlined state for supervisor pattern"""
    # Input
    srs_content: str
    project_name: str
    
    # Outputs from parallel workers
    requirements: Optional[str]
    architecture: Optional[str]
    api_spec: Optional[str]
    database_schema: Optional[str]
    tech_doc: Optional[str]
    
    # Control
    workers_completed: List[str]
    workers_pending: List[str]
    all_workers_done: bool
    
    # Tracking
    error: Optional[str]
    progress_messages: List[str]


class LangGraphSupervisorWorkflow:
    """Supervisor-based parallel workflow for better performance"""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.3):
        """Initialize with multiple LLM clients for true parallel execution"""
        actual_model = "gpt-4o-mini"
        
        # Each worker gets its own client to avoid rate limit bottlenecks
        # Increased timeout to 120s to prevent timeout errors on large documents
        self.llm_requirements = ChatOpenAI(model=actual_model, temperature=temperature, max_retries=2, timeout=120.0)
        self.llm_architecture = ChatOpenAI(model=actual_model, temperature=temperature, max_retries=2, timeout=120.0)
        self.llm_api = ChatOpenAI(model=actual_model, temperature=temperature, max_retries=2, timeout=120.0)
        self.llm_database = ChatOpenAI(model=actual_model, temperature=temperature, max_retries=2, timeout=120.0)
        self.llm_compiler = ChatOpenAI(model=actual_model, temperature=temperature, max_retries=2, timeout=120.0)
        
        self.memory = MemorySaver()
        self.graph = self._build_graph()
        self.progress_callback = None  # Will be set per execution
    
    def _build_graph(self) -> StateGraph:
        """Build simple graph: parallel workers -> compiler -> end"""
        workflow = StateGraph(SupervisorState)
        
        # Single parallel node that runs all workers at once
        workflow.add_node("parallel_workers", self.parallel_workers_node)
        workflow.add_node("compiler", self.compiler_node)
        
        # Simple flow: start -> parallel -> compile -> end
        workflow.set_entry_point("parallel_workers")
        workflow.add_edge("parallel_workers", "compiler")
        workflow.add_edge("compiler", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    def parallel_workers_node(self, state: SupervisorState) -> SupervisorState:
        """Execute all 4 workers in parallel using ThreadPoolExecutor with rate limit management"""
        import time
        
        msg1 = "Starting 4 parallel workers with intelligent chunking..."
        state["progress_messages"].append(msg1)
        if self.progress_callback:
            self.progress_callback(10, 100, msg1)
        
        srs_content = state["srs_content"]
        
        total_chars = len(srs_content)
        msg2 = f"Processing {total_chars:,} characters of SRS content..."
        state["progress_messages"].append(msg2)
        if self.progress_callback:
            self.progress_callback(15, 100, msg2)
        
        # All workers get full SRS content for comprehensive analysis
        full_srs = srs_content
        msg3 = f"Using full document context for all workers (gpt-4o-mini: 200K TPM)"
        state["progress_messages"].append(msg3)
        if self.progress_callback:
            self.progress_callback(20, 100, msg3)
        
        def run_requirements():
            """Extract comprehensive structured requirements"""
            try:
                time.sleep(0.2)  # Stagger by 200ms to avoid simultaneous rate limits
                messages = [
                    SystemMessage(content="""You are a requirements analyst. Extract ALL requirements from the SRS document.

**CRITICAL: Do NOT include the section title 'Requirements Analysis' or 'Requirements' in your output. Start directly with subsections.**

**Output format (adapt to what's in the SRS):**

## Functional Requirements
List ALL functional requirements as numbered items. Be specific and detailed.
Example:
1. **User Authentication**: System must support email/password login with OAuth options
2. **Data Management**: Users can create, read, update, delete their records

## Non-Functional Requirements
### Performance Requirements
- Response time, throughput, scalability targets

### Security Requirements
- Authentication, authorization, data protection measures

### Usability
- UI/UX requirements, accessibility standards

### Reliability and Availability
- Uptime requirements, error handling

### Maintainability and Support Requirements
- Code standards, documentation needs

## User Roles & Permissions
(Only if found in SRS)
List each role with detailed permissions and access levels.

## Business Rules
(Only if found in SRS)
Extract all business logic, validation rules, and constraints.

## System Constraints
(Only if found in SRS)
Technical limitations, dependencies, compliance requirements.

**IMPORTANT**: 
- Adapt structure to match what's actually in the SRS
- If SRS doesn't have user roles, skip that section
- Extract exactly what's in the document, don't fabricate
- Be thorough and detailed"""),
                    HumanMessage(content=f"**Complete SRS Document:**\n\n{full_srs}")
                ]
                response = self.llm_requirements.invoke(messages)
                return ("requirements", response.content)
            except Exception as e:
                return ("requirements", f"Error: {str(e)}")
        
        def run_architecture():
            """Design comprehensive system architecture"""
            try:
                time.sleep(0.4)  # Stagger by 400ms
                messages = [
                    SystemMessage(content="""You are a senior software architect. Design a detailed system architecture based on the SRS.

**CRITICAL: Do NOT include the section title 'System Architecture' or 'Architecture' in your output. Start directly with subsections.**

**Output format:**

## System Architecture
(Brief overview paragraph explaining the chosen architectural approach)

## Server Architecture
(Detailed description of server setup, deployment, infrastructure)

## Environment Strategy
(If relevant: Dev, Staging, UAT, Production environments)

### Development Environment
- Architecture details
- Purpose and use cases

### Production Environment
- Architecture details
- Load balancing, scaling strategy
- Security considerations

## Technology Stack
| Component | Technology | Version | Remarks |
|-----------|------------|---------|----------|
| Backend API | [Framework] | [Version] | [Notes] |
| Frontend | [Framework] | [Version] | [Notes] |
| Database | [Type] | [Version] | [Notes] |
| Server | [Cloud Provider] | - | [Notes] |

## Server and Database
(Detailed explanation of database choice, server infrastructure)

## 3rd Party Integrations
| Name | Usage | Reference | Remarks |
|------|-------|-----------|----------|
| [Service] | [Purpose] | [URL] | [Notes] |

## System Diagrams
(If applicable, describe or use Mermaid diagrams)

```mermaid
graph TD
    [Create relevant architecture diagrams]
```

**IMPORTANT**: Adapt to the SRS content. Only include sections relevant to the project
- **Database**: Type, schema design approach
- **Caching**: Strategy and tools
- **Message Queue**: If needed
- **DevOps**: CI/CD, containerization, orchestration

## 5. Deployment Architecture
- Infrastructure requirements
- Scaling strategy (horizontal/vertical)
- Load balancing approach
- CDN strategy if applicable

## 6. Security Architecture
- Authentication/Authorization approach
- Data encryption (in-transit and at-rest)
- API security measures
- Network security considerations

## 7. Data Flow
Describe how data moves through the system for key operations.

Be specific, detailed, and production-ready."""),
                    HumanMessage(content=f"**Complete SRS Document:**\n\n{full_srs}")
                ]
                response = self.llm_architecture.invoke(messages)
                return ("architecture", response.content)
            except Exception as e:
                return ("architecture", f"Error: {str(e)}")
        
        def run_api():
            """Generate comprehensive software architecture with technical specs"""
            try:
                time.sleep(0.6)  # Stagger by 600ms
                state["progress_messages"].append("💻 Documenting software architecture and technical specifications...")
                messages = [
                    SystemMessage(content="""You are a software architect. Document comprehensive software architecture based on the SRS, matching this exact format:

**CRITICAL: Do NOT include section title 'Software Architecture' in your output. Start directly with component subsections.**

**You will create separate detailed sections for EACH component mentioned in the SRS (typically Server/API, Backend/CMS, WebApp/Frontend). Follow this template for EACH component:**

---
## [Component Name] (e.g., "Server/API" or "Backend/CMS" or "WebApp")

### Technical Specification

#### [Component Name] Technical Specification
| Title | Value | Version |
|-------|-------|----------|
| IDE | [IDE names] | |
| Language | [Programming Language] | |
| Framework | [Framework Name] | [Version if available] |
| Architecture | [e.g., GraphQL, REST, MVC] | |
| Supported [Runtime] Version | [e.g., Node 22.x, Python 3.11] | |
| Analytics | [If applicable, e.g., GA4] | |
| Dependency Management | [Package manager] | |

**Additional details:**

- **Programming language**: [Full details about the language and why it was chosen]

- **Framework**: [Full name, version, and its benefits]

- **Supported [Runtime] Version**: [Exact version and compatibility notes]

- **[Other relevant tech details]**: [Additional technical information]

### Folder Structure

[Provide detailed explanation of the folder structure approach, e.g., "The entire codebase is built using mono repository pattern..."]

**Directory layout:**
```
folder-name/
    Brief description of this folder
    
    subfolder-1/
        Description of what this contains
        • item-1 — Detailed description
        • item-2 — Detailed description
        
    subfolder-2/
        Description
        • item — Description
```

**Explain each major folder with bullet points describing contents**

### Architecture

[1-2 paragraph overview explaining the architectural approach, components, principles like SOLID, separation of concerns, loose coupling, etc.]

#### Layers in the [Component Name]

**[Layer 1 Name] (e.g., "Services" or "Resolvers" or "Presentation Layer")**

[Detailed paragraph explaining the purpose and responsibility of this layer]

**Examples:**
- example-file-1.js
- example-file-2.js

**Responsibilities:**
- Responsibility 1 with detailed explanation
- Responsibility 2 with detailed explanation
- Responsibility 3 with detailed explanation
- Responsibility 4 with detailed explanation
- Continue with more responsibilities...

**[Layer 2 Name]**

[Detailed explanation paragraph]

**Examples:**
- example-file-1.js
- example-file-2.js

**Responsibilities:**
- List all responsibilities with detailed explanations
- Each on its own line
- Continue with more...

**[Continue for all layers: typically 3-5 layers]**
- Services/Business Logic Layer
- Resolvers/Controllers/Presentation Layer
- Entities/Repositories/Data Access Layer
- Schema/Types/DTOs Layer
- etc.

---

**REPEAT the above structure for EACH component mentioned in the SRS**

For example, if SRS mentions:
1. Backend API (Node.js/NestJS)
2. Backend CMS (React)
3. WebApp (Next.js)

You should create THREE separate sections, each with:
- Technical Specification table
- Folder Structure with detailed descriptions
- Architecture explanation
- Layered Architecture Details with examples and responsibilities

**CRITICAL FORMATTING RULES:**
1. ALWAYS put "**Examples:**" on its own line, followed by a blank line
2. ALWAYS put "**Responsibilities:**" on its own line, followed by a blank line
3. Each example item MUST be on a new line starting with "- "
4. Each responsibility MUST be on a new line starting with "- "
5. NEVER put multiple items on the same line
6. Use standard markdown bullets (- ) for ALL lists
7. Extract ALL technical details from SRS (IDE, languages, frameworks, versions)
8. Each layer description should be 2-3 sentences minimum
9. Responsibilities should have 4-6 bullet points minimum per layer
10. Be extremely comprehensive - this is the detailed implementation section"""),
                    HumanMessage(content=f"**Complete SRS Document:**\n\n{full_srs}")
                ]
                response = self.llm_api.invoke(messages)
                state["progress_messages"].append("Software architecture documentation completed")
                return ("api_spec", response.content)
            except Exception as e:
                return ("api_spec", f"Error: {str(e)}")
        
        def run_database():
            """Extract comprehensive database design if present in SRS"""
            try:
                time.sleep(0.8)  # Stagger by 800ms
                state["progress_messages"].append("🗄️ Documenting database design and schema...")
                messages = [
                    SystemMessage(content="""You are a database architect. Extract and document database design from the SRS.

**CRITICAL: Do NOT include the section title 'Database Design' in your output. Start directly with subsections.**

**ONLY include database sections IF the SRS mentions database design, schemas, or entity relationships. If the SRS has no database details, return an empty string.**

**If database info exists, use this format:**

## Database Overview
[2-3 paragraphs explaining:
- Database type chosen (SQL/NoSQL and specific engine)
- Rationale for the choice based on project requirements
- Hosting approach (cloud service, managed database)
- Key configuration decisions]

## Entity Relationship Diagram (ERD)

[If the SRS describes entities, relationships, or data models, create a detailed Mermaid ERD]

**CRITICAL MERMAID ERD SYNTAX RULES:**

1. **NO constraint keywords in attribute definitions** - Mermaid doesn't support UNIQUE, NOT NULL, etc. in ERD syntax
2. Use only: `datatype fieldname` or `datatype fieldname PK` or `datatype fieldname FK`
3. Comments/descriptions are optional but must not contain special keywords

**CORRECT Mermaid ERD format:**

```mermaid
erDiagram
    ENTITY1 ||--o{ ENTITY2 : "relationship"
    ENTITY1 {
        datatype fieldname PK
        datatype fieldname FK
        datatype fieldname
    }
    ENTITY2 {
        datatype fieldname PK
    }
```

**VALID Examples:**
```mermaid
erDiagram
    User ||--o{ Post : "creates"
    User {
        UUID id PK
        VARCHAR email
        VARCHAR password
        TIMESTAMP created_at
    }
    Post {
        UUID id PK
        UUID user_id FK
        TEXT content
    }
```

**INVALID (DO NOT USE):**
```
User {
    VARCHAR email UNIQUE "Email address"  ❌ WRONG - no UNIQUE keyword
    VARCHAR name NOT NULL                  ❌ WRONG - no NOT NULL keyword  
}
```

**Rules:**
- Only use PK or FK after field names
- NO other constraint keywords (UNIQUE, NOT NULL, AUTO_INCREMENT, DEFAULT, etc.)
- Keep it simple: `datatype fieldname` or `datatype fieldname PK/FK`
- Document constraints in the Tables section instead

## Tables

**CRITICAL FORMATTING RULES:**
- Each table section MUST start on a NEW LINE
- "**Purpose**:" must be on its own line
- "**Columns**:" must be on its own line with empty line BEFORE the table
- Markdown tables need blank lines before AND after
- Each subsection (Indexes, Foreign Keys, etc.) on separate lines

For EACH table, provide:

### [Table Name] Table

**Purpose**: [Brief description of what this table stores]

**Columns**:

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| id | UUID/BIGINT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | Last update timestamp |
| ... | ... | ... | ... |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on frequently queried fields
- UNIQUE INDEX on unique constraints
- COMPOSITE INDEX for multi-column queries

**Foreign Keys**:
- `{foreign_key}` REFERENCES `{other_table}(id)` ON DELETE {CASCADE/SET NULL/RESTRICT}

**Constraints**:
- CHECK constraints for data validation
- UNIQUE constraints
- NOT NULL constraints

## 4. Relationships
Detailed explanation of all table relationships:
- One-to-Many: User → Posts (one user has many posts)
- Many-to-Many: Students ↔ Courses (junction table: Enrollments)
- One-to-One: User ↔ Profile

## 5. Data Types Rationale
Explain why specific data types were chosen for critical fields.

## 6. Indexing Strategy
- Primary indexes
- Secondary indexes for query optimization
- Full-text search indexes if needed
- Rationale for each index

## 7. Data Integrity
- Referential integrity rules
- Cascading delete/update policies
- Data validation rules
- Soft delete strategy if applicable

## 8. Performance Considerations
- Partitioning strategy
- Archival strategy
- Query optimization notes
- Caching recommendations

## 9. Sample Queries
Provide SQL examples for common operations if relevant.

**CRITICAL FORMATTING REQUIREMENTS:**
1. If SRS has NO database design details, return empty string
2. Mermaid diagrams MUST use ```mermaid code fence (triple backticks + mermaid)
3. Every table section MUST have proper spacing:
   - Blank line before table heading
   - "**Purpose**:" on separate line
   - "**Columns**:" on separate line
   - BLANK LINE before markdown table
   - BLANK LINE after markdown table
   - Each subsection (Indexes, Foreign Keys, Relationships) on new lines
4. Extract ALL entities, fields, relationships from SRS
5. Be extremely thorough - this is implementation-ready documentation"""),
                    HumanMessage(content=f"**Complete SRS Document:**\n\n{full_srs}")
                ]
                response = self.llm_database.invoke(messages)
                state["progress_messages"].append("Database documentation completed")
                return ("database_schema", response.content)
            except Exception as e:
                return ("database_schema", f"Error: {str(e)}")
        
        # Execute all 4 workers in parallel with proper progress tracking
        try:
            start_time = time.time()
            msg = "Starting parallel processing of 4 documentation sections..."
            state["progress_messages"].append(msg)
            if self.progress_callback:
                self.progress_callback(25, 100, msg)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(run_requirements),
                    executor.submit(run_architecture),
                    executor.submit(run_api),
                    executor.submit(run_database)
                ]
                
                # Track progress with actual percentages
                completed_count = 0
                total_workers = 4
                worker_labels = {
                    "requirements": "Technical Requirements",
                    "architecture": "System Design", 
                    "api_spec": "Software Architecture",
                    "database_schema": "Database Schema"
                }
                
                for future in concurrent.futures.as_completed(futures):
                    worker_name, result = future.result()
                    state[worker_name] = result
                    completed_count += 1
                    
                    # Calculate percentage: 25%, 50%, 75%, 100%
                    progress_percentage = int((completed_count / total_workers) * 100)
                    
                    label = worker_labels.get(worker_name, worker_name)
                    # Check if result is an error
                    if result.startswith("Error:"):
                        msg = f"⚠️ {label} failed: {result[:100]}"
                        state["progress_messages"].append(msg)
                        # Emit progress immediately
                        if self.progress_callback:
                            self.progress_callback(progress_percentage, 100, msg)
                    else:
                        chars = len(result)
                        msg = f"{label} completed ({chars:,} chars) - {progress_percentage}% done"
                        state["progress_messages"].append(msg)
                        # Emit progress immediately
                        if self.progress_callback:
                            self.progress_callback(progress_percentage, 100, msg)
            
            elapsed = time.time() - start_time
            state["all_workers_done"] = True
            total_chars = len(state.get('requirements', '')) + len(state.get('architecture', '')) + len(state.get('api_spec', '')) + len(state.get('database_schema', ''))
            msg = f"All 4 sections generated in {elapsed:.1f}s - Total: {total_chars:,} characters"
            state["progress_messages"].append(msg)
            # Emit immediately
            if self.progress_callback:
                self.progress_callback(100, 100, msg)
            
        except Exception as e:
            state["error"] = f"Parallel execution failed: {str(e)}"
            state["progress_messages"].append(f"❌ Error in parallel execution: {str(e)}")
        
        return state
    
    def compiler_node(self, state: SupervisorState) -> SupervisorState:
        """Compile all outputs into final documentation matching exact sample format"""
        msg = "Compiling final technical documentation..."
        state["progress_messages"].append(msg)
        # Emit immediately
        if self.progress_callback:
            self.progress_callback(95, 100, msg)
        
        try:
            # Extract project info for header
            project_name = state.get('project_name', 'Project')
            
            # EXACT format from sample with header section
            tech_doc = f"""# {project_name} - Technical Documentation

## Quick Links

| Item | Link |
|------|------|
| Project | {project_name} |

## About This Document

The purpose of this technical document is to provide comprehensive technical specifications and architecture documentation for {project_name}. This document highlights all technical deliverables, infrastructure decisions, and implementation details.

## Overview of the Project

{project_name} is documented herein with complete technical specifications extracted from the Software Requirements Specification (SRS) document.

---

# Technical Requirements

{state.get('requirements', 'Requirements analysis pending...')}

---

# System Design

{state.get('architecture', 'System architecture pending...')}

---

# Software Architecture

{state.get('api_spec', 'Software architecture pending...')}

{state.get('database_schema', '')}

---

## Useful Links

[Additional project resources and documentation links can be added here]
"""
            
            state["tech_doc"] = tech_doc
            msg = "Final documentation compiled successfully"
            state["progress_messages"].append(msg)
            # Emit immediately
            if self.progress_callback:
                self.progress_callback(100, 100, msg)
            
        except Exception as e:
            state["error"] = f"Compilation failed: {str(e)}"
            state["progress_messages"].append(f"❌ Compilation error: {str(e)}")
        
        return state
    
    def process_srs(self, srs_content: str, project_name: str, thread_id: str, progress_callback=None) -> Dict[str, Any]:
        """Execute the parallel workflow with real-time progress updates"""
        # Store callback for use in nodes
        self.progress_callback = progress_callback
        
        initial_state: SupervisorState = {
            "srs_content": srs_content,
            "project_name": project_name,
            "requirements": None,
            "architecture": None,
            "api_spec": None,
            "database_schema": None,
            "tech_doc": None,
            "workers_completed": [],
            "workers_pending": ["requirements", "architecture", "api_spec", "database_schema"],
            "all_workers_done": False,
            "error": None,
            "progress_messages": []
        }
        
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 10  # Much lower since no loops
        }
        
        # Execute workflow
        final_state = self.graph.invoke(initial_state, config)
        
        return final_state
