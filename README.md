# Ready4Uni 🎓

Your intelligent companion for navigating university major selection and academic readiness.

## Overview

Choosing a university major is one of the most significant decisions a student faces. **Ready4Uni** bridges the gap between student interests and academic reality.

Unlike standard chatbots, Ready4Uni is an **Agentic System**. It actively processes user inputs, whether natural language descriptions of hobbies or uploaded **High School Transcripts (PDF)** to provide data-driven advice. It identifies grade gaps and generates actionable, personalized study plans to help students meet entry requirements.

## Features

- 🎯 **Interest-Based Major Discovery**: Describe your hobbies, favorite subjects, and career dreams. The AI suggests the top 3-5 best-fitting university majors.
- 📄 **Transcript Analysis (PDF Support)**: Upload your school records. The system extracts grade data to evaluate academic strengths and weaknesses.
- 📉 **Gap Analysis**: Compare your current grades against typical requirements for recommended majors.
- 📚 **Personalized Resource Recommendations**: Get curated study topics and external resources (Khan Academy, Coursera) to improve readiness.
- 🛡️ **Safety & Crisis Detection**: The app detects sensitive messages and provides compassionate crisis helpline resources.

## Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python 3.10+, Google Gemini API (2.5 Flash) |
| **PDF Processing** | pdfplumber |
| **Frontend** | Streamlit |
| **Observability** | Langfuse (tracing, monitoring, debugging) |
| **AI Features** | Function Calling, Structured Outputs |

## Architecture

Ready4Uni follows a **layered architecture** with clear separation of concerns:

| Layer | Description |
|-------|-------------|
| **UI** (`app.py`) | Streamlit chat interface, file uploads, session state |
| **Services** (`services/`) | Business logic: gap analysis, major matching, resources |
| **Core** (`core/`) | Agent orchestrator, intent router, crisis detection |
| **Tools** (`tools/`) | LLM-invokable functions for transcripts, majors, resources |
| **AI** (`ai/`) | Gemini API wrapper with Langfuse tracing |
| **Config** (`config/`) | Centralized settings, prompts, and constants |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture decisions.

## Installation & Setup

### Prerequisites
- Python 3.10+
- Google Gemini API key
- Langfuse account (for observability)

### Installation Steps

1. **Clone the repository:**
```bash
git clone https://github.com/<your-username>/ready4uni.git
cd ready4uni
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required environment variables:**
```
GOOGLE_API_KEY=your_gemini_api_key_here
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

4. **Run the application:**
```bash
streamlit run app.py
```

The app will start on `http://localhost:8501`.

## Usage

### Interest-Based Major Discovery
1. Describe your interests: *"I love maths and physics and want something with research."*
2. The agent classifies interests and suggests matching majors
3. Get a ranked list (e.g., Physics, Engineering, Data Science) with explanations

### Transcript Analysis
1. Upload your high school transcript PDF
2. The system extracts and analyzes your grades
3. Compare against requirements for specific majors
4. Get personalized study resource recommendations

## Deployment

**Live Application:** https://ready4uni.streamlit.app  
**Platform:** Streamlit Community Cloud

To deploy your own instance:
1. Fork this repository
2. Set environment variables in your deployment platform
3. Configure start command: `streamlit run app.py`

## Project Structure

```
ready4uni/
├── app.py                  # Streamlit entry point
├── requirements.txt        # Dependencies
├── .env.example            # Environment template
│
├── config/                 # ⚙️ Centralized configuration
│   ├── settings.py         # API keys, model params, crisis keywords
│   └── prompts.py          # System prompts, tool definitions
│
├── ai/                     # 🧠 LLM infrastructure
│   └── llm_service.py      # Gemini API + Langfuse tracing
│
├── core/                   # 🎯 Agent logic
│   ├── router.py           # Intent classification + crisis detection
│   └── orchestrator.py     # Agent loop (plan → act → respond)
│
├── services/               # 👔 Business logic
│   ├── chat_service.py     # Main coordinator
│   ├── major_service.py    # Interest matching
│   ├── transcript_service.py
│   └── resource_service.py
│
├── tools/                  # 🛠️ Function calling tools
│   ├── transcript_tools.py
│   ├── major_tools.py
│   └── resource_tools.py
│
├── clients/                # 🔌 Utility clients
│   └── pdf_client.py       # PDF text extraction
│
├── data/                   # 📊 Reference data
│   └── majors.json
│
├── docs/                   # 📄 Documentation
│   ├── ARCHITECTURE.md
│   └── TOOLS.md
│
└── tests/                  # ✅ Tests
    └── fixtures/
```

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Architecture decisions and design patterns
- [TOOLS.md](docs/TOOLS.md) - Function calling tool specifications

## Team

- Phat Ma 


## License

MIT License
