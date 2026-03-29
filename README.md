<p align="center">
  <strong>V.NOTEBOOK</strong>
</p>
<h1 align="center">V.NOTEBOOK — AI-Native Researcher & Assistant</h1>
<p align="center">
  An intelligent research workspace combining RAG-powered document analysis with a controlled execution engine for real-world actions.
</p>

---

## Overview

**V.NOTEBOOK** is a full-stack AI workspace built from the ground up. It pairs a research notebook (for uploading, querying, and analyzing documents via Retrieval-Augmented Generation) with **V.ASSISTANT**, a controlled execution system that connects to Gmail, Google Calendar, and WhatsApp — with mandatory human approval before every action.

The project demonstrates advanced AI/ML engineering concepts including semantic routing, agentic function calling, RAG pipelines, human-in-the-loop safety, and OAuth-based API integrations.

---

## Key Features

| Feature | Description |
| --- | --- |
| **Multi-Mode Research Notebook** | Three operating modes — *Fast Mode* (general Q&A), *Grounded Mode* (RAG with citations), *Deep Research* (web-augmented analysis) |
| **RAG Pipeline** | Upload PDFs → chunk → embed with Sentence Transformers → index in FAISS → retrieve & synthesize with LLM |
| **Knowledge Graph** | Automatically builds a NetworkX graph of entities and relationships from uploaded documents |
| **V.ASSISTANT** | A controlled execution engine that parses natural language into structured actions (email, calendar, messaging) |
| **Human-in-the-Loop Gating** | Every action generates a preview card requiring explicit user approval before execution |
| **Gmail Intelligence** | Thread analysis, action-item detection, urgency classification, smart reply generation |
| **Session & Goal Tracking** | Persistent sessions with automatic goal inference from conversation context |
| **Studio Tools** | Audio overview generation, flashcard creation, mind map, quiz, and draft export |
| **Cognitive Layer** | Feedback memory, insight extraction, and preference learning across sessions |

---

## Technologies Used

### Backend
- **Python 3.10+** with **FastAPI** — async API server with lifespan events
- **Groq API** (Llama-3.3-70b) — primary LLM inference (chosen for its free tier; any OpenAI-compatible provider can be swapped in)
- **OpenRouter** — automatic fallback provider when all Groq keys are exhausted
- **Sentence Transformers** — document embedding for semantic search
- **FAISS** — vector similarity index for fast retrieval
- **NetworkX** — knowledge graph construction
- **Google APIs** — Gmail and Calendar via OAuth 2.0
- **DuckDuckGo Search** — web search for Deep Research mode
- **SpeechRecognition** — audio transcription

### Frontend
- **Vanilla HTML/CSS/JS** — no framework, fully modular
- **Tailwind CSS** (CDN) — utility-first styling with custom design tokens
- **Material Design 3** — icon system and design language

---

## How It Works

### Research Notebook Pipeline

```
User Query
    │
    ├─ Fast Mode ──────────── LLM (direct answer)
    │
    ├─ Grounded Mode ──────── FAISS Retrieval → Top-K Chunks → LLM Synthesis → JSON with Citations
    │
    └─ Deep Research ──────── Web Search (DuckDuckGo) → Multi-Source Analysis → Structured Report
```

**Grounded Mode (RAG)** follows this flow:
1. **Ingestion**: PDF upload → text extraction (PyPDF) → recursive chunking
2. **Embedding**: Chunks are embedded using Sentence Transformers
3. **Indexing**: Embeddings stored in a FAISS vector index
4. **Retrieval**: User query is embedded → top-K nearest neighbor search
5. **Synthesis**: Retrieved context is injected into the LLM system prompt → response with evidence citations

### V.ASSISTANT Execution Flow

```
User Request
    │
    ▼
Intent Parser (LLM) ── Extracts structured action (to, subject, body, etc.)
    │
    ▼
Decision Engine ─────── Routes to correct handler (email, calendar, search)
    │
    ▼
Action Queue ────────── Writes action with status: PENDING
    │
    ▼
UI Preview Card ─────── User reviews, edits, approves, or cancels
    │
    ▼
Executor ────────────── Calls provider adapter (Gmail API, Calendar API)
    │
    ▼
Audit Log ───────────── Records result with timestamp and status
```

---

## Setup

### Prerequisites
- Python 3.10+
- An LLM API key — [Groq](https://console.groq.com) is recommended (free tier), but any OpenAI-compatible provider works (see [Using Other LLM Providers](#using-other-llm-providers))
- (Optional) Google Cloud project with Gmail and Calendar APIs enabled

### 1. Clone & Install

```bash
git clone https://github.com/<your-username>/V.NOTEBOOK.git
cd V.NOTEBOOK
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```ini
# Required — LLM Provider (get a free key at https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Optional — Additional Groq keys for rate-limit rotation
GROQ_API_KEY_2=your_second_key_here
GROQ_API_KEY_3=your_third_key_here

# Optional — Fallback LLM Provider (https://openrouter.ai)
OPENROUTER_API_KEY=your_openrouter_key_here
```

### Using Other LLM Providers

This project uses **Groq** as the default LLM provider because it offers a generous free tier, but the architecture is provider-agnostic. You can swap in any LLM provider by modifying `backend/core/llm.py`:

| Provider | What to change |
| --- | --- |
| **OpenAI** | Replace the `Groq` client with `OpenAI` from the `openai` package (same API shape) |
| **Anthropic (Claude)** | Use the `anthropic` package and update the `get_response()` method |
| **Google Gemini** | Use `google-genai` and adapt the request format |
| **Ollama (Local)** | Point the OpenAI-compatible client to `http://localhost:11434/v1` |
| **Any OpenAI-compatible API** | The Groq SDK is OpenAI-compatible — just change the `base_url` and API key |

The key file to modify is [`backend/core/llm.py`](backend/core/llm.py) — it centralizes all LLM calls, so a single-file change switches the entire application.

### 3. (Optional) Google API Credentials

To enable Gmail and Calendar integrations:

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the **Gmail API** and **Google Calendar API**
3. Configure the **OAuth Consent Screen** (Desktop App)
4. Create **OAuth Client ID** credentials and download the JSON
5. Rename to `credentials.json` and place in the project root
6. On first run, a browser window will open for OAuth authorization

### 4. Run

**Start the backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Start the frontend** (in a separate terminal):
```bash
cd frontend
python -m http.server 3000
```

Open `http://localhost:3000` in your browser.

---

## Folder Structure

```
V.NOTEBOOK/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── api/
│   │   ├── routes_common.py       # Shared endpoints (health, sessions)
│   │   ├── routes_notebook.py     # Notebook endpoints (query, upload, flashcards)
│   │   ├── routes_assistant.py    # Assistant endpoints (chat, actions, dashboard)
│   │   └── webhooks.py            # Webhook receivers (email, status)
│   ├── core/
│   │   ├── engine.py              # Central orchestrator — routes queries through RAG/LLM
│   │   ├── llm.py                 # Groq client with multi-key rotation & OpenRouter fallback
│   │   ├── memory.py              # FAISS-backed vector store for RAG retrieval
│   │   ├── ingestion.py           # PDF text extraction and chunking
│   │   ├── graph.py               # NetworkX knowledge graph builder
│   │   ├── personas.py            # System prompt assembly per mode
│   │   ├── session.py             # Session persistence and management
│   │   ├── goals.py               # Goal inference and tracking
│   │   ├── feedback.py            # User preference learning
│   │   ├── insights.py            # Cross-session insight extraction
│   │   ├── decision_engine.py     # V.ASSISTANT — intent routing & action generation
│   │   ├── assistant_chat.py      # NLP parser for assistant commands
│   │   ├── email_intelligence.py  # Thread analysis, urgency scoring, smart replies
│   │   ├── actions.py             # Atomic action queue with state machine
│   │   ├── executor.py            # Action executor with provider dispatch
│   │   ├── context_manager.py     # Conversation context tracking
│   │   ├── research/              # Deep Research module (web search + synthesis)
│   │   └── adapters/
│   │       ├── gmail_adapter.py   # Gmail API adapter (OAuth, send, read, reply)
│   │       ├── calendar_adapter.py # Google Calendar adapter
│   │       └── whatsapp_adapter.py # WhatsApp Business API adapter
│   └── models/                    # Pydantic models (request/response schemas)
├── frontend/
│   ├── index.html                 # Main SPA entry point
│   ├── css/                       # Stylesheets
│   └── js/
│       ├── app.js                 # Application initializer
│       ├── api.js                 # Backend API client
│       ├── router.js              # Hash-based SPA router
│       ├── state.js               # Global state manager with pub/sub
│       ├── sidebar.js             # Source/History panel logic
│       ├── notebook/              # Notebook workspace modules
│       │   ├── chat.js            # Chat UI, message rendering, markdown
│       │   ├── modes.js           # Mode selector (Fast/Grounded/Deep)
│       │   ├── sources.js         # Uploaded document management
│       │   ├── history.js         # Session history panel
│       │   ├── goals.js           # Active goals display
│       │   ├── flashcards.js      # Flashcard generator UI
│       │   ├── studio.js          # Studio tools (audio, video, mindmap)
│       │   └── audio-player.js    # Audio overview player
│       └── assistant/
│           └── dashboard.js       # V.ASSISTANT chat UI & action cards
├── workflows/                     # n8n workflow templates (Gmail watch, send reply)
├── system_prompt.xml              # Master system prompt (Prompt Constitution)
├── .env.example                   # Environment variable template
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
├── LICENSE                        # MIT License
└── README.md                      # This file
```

---

## Security Notes

> [!IMPORTANT]
> **Your API keys and tokens are NEVER committed to the repository.**

This project uses a layered security approach:

| What | How it's protected |
| --- | --- |
| Groq / OpenRouter API keys | Stored in `.env` (gitignored) |
| Google OAuth credentials | `credentials.json` (gitignored) |
| Gmail / Calendar tokens | `data/gmail_token.json`, `data/calendar_token.json` (gitignored via `data/`) |
| Session data | `data/` directory (gitignored) |

**Before pushing to GitHub**, verify:
```bash
git status   # Make sure .env, credentials.json, and data/ are NOT listed
```

If you accidentally committed secrets, rotate your API keys immediately and use `git filter-branch` or BFG Repo Cleaner to remove them from history.

---

## Advanced Concepts Demonstrated

This project covers the following engineering topics:

### 1. Retrieval-Augmented Generation (RAG)
End-to-end RAG pipeline: PDF ingestion → text chunking → embedding with Sentence Transformers → FAISS vector indexing → semantic retrieval → LLM synthesis with source citations. Implements both naive top-K retrieval and experimental LLM-based reranking.

### 2. Semantic Routing & Intent Parsing
Uses LLMs (Llama-3 via Groq) to parse unstructured natural language into structured JSON actions. The Decision Engine classifies user intent across multiple domains (email, calendar, search, general chat) and routes to the appropriate handler with extracted parameters.

### 3. Agentic Function Calling & Execution
Implements a deterministic execution engine where the AI generates *proposed* actions, but a human must approve before any real-world side effect occurs. Supports compound (multi-step) actions, follow-up context resolution, and action editing.

### 4. Human-in-the-Loop (HITL) Safety
Every action passes through a mandatory approval gate. The UI renders interactive preview cards showing exactly what will happen (recipient, subject, body). Users can edit parameters inline, approve, or cancel — ensuring the AI never acts autonomously.

### 5. Idempotent Queue Management
Actions are persisted in an atomic JSON file store with strict state transitions: `Pending → Approved → Executed` (or `Cancelled` / `Failed`). Each action has a unique ID, timestamps, and a full audit trail. The system is crash-safe and idempotent.

### 6. OAuth 2.0 Integration
Implements the full OAuth 2.0 authorization code flow for Google APIs (Gmail, Calendar). Handles token persistence, automatic refresh, and graceful degradation when credentials are not configured.

### 7. Multi-Key API Rotation & Fallback
The LLM handler supports multiple API keys with automatic rotation on rate-limit errors (HTTP 429). When all Groq keys are exhausted, it falls back to OpenRouter with a different model — ensuring uninterrupted service.

### 8. Cognitive Layer (Goal Inference & Feedback Learning)
The system automatically infers research goals from conversation context, tracks progress, and learns user preferences over time. Insights are extracted cross-session and injected into future prompts to improve relevance.

### 9. Prompt Engineering (Prompt Constitution)
A structured XML-based system prompt defines the AI's identity, decision modes, safety policies, and response formatting rules. Mode-specific overrides (Fast, Grounded, Deep Research, Assistant) are layered on top dynamically.

### 10. Knowledge Graph Construction
Uploaded documents are processed into a NetworkX graph capturing entity relationships, enabling graph-based exploration and cross-document linking.

---

## Known Limitations

- **Settings & Profile**: The settings gear icon and profile avatar in the top navigation bar are UI placeholders — they are not yet wired to any functionality.
- **WhatsApp Integration**: The WhatsApp adapter is implemented but requires a Meta Business API account and is not enabled by default.
- **Audio/Video Studio**: The audio overview feature requires a TTS engine; the video and mind map tools are stubbed for future implementation.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
