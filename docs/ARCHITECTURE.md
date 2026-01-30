# Ready4Uni Architecture

This document explains the architecture decisions and design patterns used in Ready4Uni.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     UI Layer (Streamlit)                        │
│                         app.py                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Services Layer                               │
│   chat_service.py │ transcript_service.py │ major_service.py    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Core Layer    │  │   Tools Layer   │  │  Clients Layer  │
│ orchestrator.py │  │ major_tools.py  │  │  pdf_client.py  │
│   router.py     │  │ transcript_tools│  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI Layer                                   │
│              llm_service.py (Gemini API + Langfuse)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Config Layer                                 │
│         settings.py │ prompts.py (centralized config)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. UI Layer (`app.py`)
- Streamlit-based chat interface
- File upload handling
- Session state management
- User interaction flow

### 2. Services Layer (`services/`)
- **chat_service.py**: Orchestrates conversation flow, coordinates with agent
- **major_service.py**: Interest-to-major matching, major search, similarity scoring
- **transcript_service.py**: Grade analysis, gap calculation, readiness assessment
- **resource_service.py**: Study resource recommendations

### 3. Core Layer (`core/`)
- **orchestrator.py**: Main agent loop (observe → plan → act → respond)
- **router.py**: Intent classification (major_discovery, transcript_analysis, etc.)

### 4. Tools Layer (`tools/`)
Function calling tools exposed to the LLM:
- `parse_transcript`: PDF grade extraction
- `get_major_info`: Major details lookup
- `get_major_suggestions`: Interest-based matching
- `analyze_grades`: Requirement comparison
- `find_study_resources`: Resource recommendations

### 5. AI Layer (`ai/`)
- **llm_service.py**: Gemini API wrapper with:
  - Retry logic with exponential backoff
  - Langfuse tracing integration
  - Structured output generation
  - Token usage tracking

### 6. Config Layer (`config/`)
- **settings.py**: API keys, model names, constants
- **prompts.py**: System prompts, tool definitions, JSON schemas

---

## Design Decisions

### Why This Architecture?

| Decision | Justification |
|----------|---------------|
| **Layered architecture** | Separation of concerns, easier testing, maintainability |
| **Centralized config** | Single source of truth for prompts and settings |
| **Function calling** | Structured tool execution vs. free-form LLM output |
| **Retry with backoff** | Graceful handling of API rate limits and transient errors |
| **Langfuse integration** | Observability for debugging LLM behavior in production |

### Trade-offs Considered

1. **Streamlit vs. FastAPI + React**
   - Chose Streamlit for rapid prototyping and simplicity
   - Trade-off: Less customizable UI, but faster development

2. **JSON files vs. Database**
   - Used JSON (`data/majors.json`) for curated major data
   - Trade-off: Not scalable for large datasets, but sufficient for MVP

3. **Gemini vs. OpenAI**
   - Chose Gemini for free tier availability
   - Trade-off: Slightly different API patterns

---

## Data Flow Example

**User asks: "What majors match my interest in programming?"**

```
1. app.py receives message
2. chat_service.process_message() called
3. router.classify_intent() → "major_discovery"
4. orchestrator.run() starts agent loop
5. LLM decides to call get_major_suggestions tool
6. major_tools.get_major_suggestions() executes
7. major_service.match_interests_to_majors() performs matching
8. Results returned to orchestrator
9. LLM synthesizes final response
10. Response displayed in Streamlit UI
```

---

## Observability

All LLM calls are traced via Langfuse:
- Prompt inputs and outputs
- Token usage and latency
- Tool call sequences
- Error tracking

Access traces at: https://cloud.langfuse.com

---

## Safety & Crisis Detection

Ready4Uni includes a safety feature to detect and respond to users expressing self-harm thoughts.

### How It Works

1. **Keyword Detection**: Before any LLM call, `router.py` checks for crisis keywords
2. **Early Return**: If detected, `chat_service.py` immediately returns a compassionate response
3. **No Agent Processing**: Crisis messages bypass the entire agent loop for speed and reliability

### Configuration

Crisis keywords and response message are centralized in `config/settings.py`:
- `CRISIS_KEYWORDS`: List of phrases triggering safety response
- `CRISIS_RESPONSE`: Compassionate message with Portugal helplines

### Design Rationale

| Decision | Justification |
|----------|---------------|
| **Keyword-based (not LLM)** | Fast, reliable, no false negatives from LLM interpretation |
| **Pre-agent check** | Safety response in <100ms vs. seconds for LLM processing |
| **Centralized config** | Easy to update helplines or add keywords |

