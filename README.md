<div align="center">
  <img src="https://img.shields.io/badge/Status-Active-success.svg?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/License-MIT-purple.svg?style=for-the-badge" alt="License" />

  <h1>V.NOTEBOOK</h1>
  <p><strong>AI-Native Research Workspace & Assistant</strong></p>

  <p>
    An intelligent research workspace combining RAG-powered document analysis <br/>
    with a controlled execution engine for real-world actions.
  </p>

  <img src="assets/notebook-ui.png" alt="V.NOTEBOOK Interface Screenshot" width="1000">
</div>

---

## 📖 Overview

**V.NOTEBOOK** is a full-stack AI workspace built from the ground up. It pairs a comprehensive research notebook (for uploading, querying, and analyzing documents via Retrieval-Augmented Generation) with **V.ASSISTANT** — a controlled execution system connecting directly to Gmail, Google Calendar, and WhatsApp.

Crucially, it utilizes **mandatory human approval** before execution, ensuring that the AI assists you safely without making unauthorized decisions.

The project demonstrates advanced AI/ML engineering concepts including semantic routing, agentic function calling, RAG pipelines, human-in-the-loop safety, and OAuth-based API integrations.

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🗂️ **Multi-Mode Notebook** | Operate in *Fast Mode* (QA), *Grounded Mode* (RAG with citations), or *Deep Research* (web-augmented analysis). |
| 🔍 **RAG Pipeline** | Intelligent document pipeline: Upload PDFs → chunk → embed → index in FAISS → synthesize via LLM. |
| 🕸️ **Knowledge Graph** | Automatically maps out a NetworkX graph of entities and relationships from uploaded documents. |
| 🤖 **V.ASSISTANT** | Controlled execution engine translating natural language into structured actions across APIs. |
| 🛡️ **Human-in-the-Loop** | Every proposed action generates a preview card requiring explicit user approval before execution. |
| 📧 **Gmail Intelligence** | Advanced thread analysis, action-item detection, urgency scoring, and smart reply generation. |
| 🎯 **Goal Tracking** | Persistent sessions featuring automatic goal inference and progression from conversation context. |
| 🎙️ **Studio Tools** | Includes audio overview generation, auto-generated flashcards, mind maps, quizzes, and exports. |
| 🧠 **Cognitive Layer** | Features feedback memory, cross-session insight extraction, and progressive preference learning. |
| 🔑 **Multi-Provider LLM** | Supports OpenAI, Anthropic (Claude), Google (Gemini), and Groq — switch models with one click. |
| 🔐 **1-Click Google OAuth** | Browser-based "Sign in with Google" — no manual credential file setup required. |
| ⚙️ **Settings Dashboard** | Full UI for API keys, model selection, memory stats, and integration management. |

<br>

<div align="center">
  <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
    <img src="assets/assistant-action.png" alt="V.ASSISTANT Preview Card" width="45%">
    <img src="assets/gmail-integration.png" alt="Gmail Integration" width="45%">
  </div>
  <p><em>V.ASSISTANT requiring human approval (Left) and Gmail Intelligence in action (Right).</em></p>
</div>

---

## 🛠️ Technologies Used

### Backend Infrastructure
*   **Python 3.10+ & FastAPI**: Asynchronous API server with integrated lifespan events.
*   **LiteLLM**: Universal LLM router — dynamically routes requests to OpenAI, Anthropic, Google Gemini, Groq, and 100+ providers via a single interface.
*   **Sentence Transformers & FAISS**: Core pipeline for document embedding and rapid vector similarity search.
*   **NetworkX**: Applied for sophisticated knowledge graph construction.
*   **Google OAuth 2.0 APIs**: 1-click browser-based OAuth flow for Gmail and Google Calendar.
*   **DuckDuckGo Search**: Web search module specifically empowering Deep Research mode.
*   **SpeechRecognition**: Real-time audio transcription capabilities.

### Frontend Architecture
*   **Vanilla HTML/CSS/JS**: Zero-framework, fully modular, and ultra-lightweight.
*   **Tailwind CSS (CDN)**: Clean, utility-first styling bound by custom design tokens.
*   **Material Design 3**: Unified iconography and design language execution.

---

## ⚙️ How It Works

### Research Notebook Pipeline
```mermaid
graph TD;
    A[User Query] --> B(Fast Mode)
    A --> C(Grounded Mode)
    A --> D(Deep Research)
    B --> E[LLM Direct Answer]
    C --> F[FAISS Retrieval -> Top-K Chunks -> Synthesis -> Output w/ Citations]
    D --> G[Web Search API -> Multi-Source Analysis -> Structured Report]
```

**Grounded Mode (RAG)** follows this specific execution flow:
1.  **Ingestion**: Document upload → text extraction → recursive chunking.
2.  **Embedding**: Chunks are processed via Sentence Transformers.
3.  **Indexing**: Generated embeddings correctly stored in a FAISS vector index.
4.  **Retrieval**: The user query is embedded → top-K nearest neighbor search triggers.
5.  **Synthesis**: Retrieved context correctly injected into the LLM system prompt for factual synthesis.

### V.ASSISTANT Execution Flow
```text
  User Request 
       │
       ▼
  Intent Parser         ── Extracts structured action (recipient, subject, body, etc.)
       │
       ▼
  Decision Engine       ── Routes to the correct handler (email, calendar, search)
       │
       ▼
  Action Queue          ── Writes action to local state with status: PENDING
       │
       ▼
  UI Preview Card       ── User reviews, edits, APPROVES, or CANCELS
       │
       ▼
  Executor              ── Calls the appropriate provider adapter (Gmail API, Calendar API)
       │
       ▼
  Audit Log             ── Resolves and records the result with timestamp & status
```

### Multi-Provider LLM Routing
```mermaid
graph LR;
    A[User Prompt] --> B[LiteLLM Router]
    B --> C{Provider Prefix}
    C -->|groq/| D[Groq - Llama 3.3 70B]
    C -->|gemini/| E[Google Gemini Pro]
    C -->|openai/| F[OpenAI GPT-4o]
    C -->|anthropic/| G[Anthropic Claude]
    B --> H[Dynamic API Key from .env]
```

---

## 🚀 Setup & Installation

### Prerequisites
*   Python `3.10+` minimum.
*   At least one LLM API Key (free tiers available from multiple providers).

> [!TIP]
> **Free API Key Sources:**
> *   🟢 [Groq](https://console.groq.com) — Free, fastest inference (Llama 3.3 70B)
> *   🔵 [Google AI Studio](https://aistudio.google.com/apikey) — Free Gemini Pro access
> *   ⚫ [OpenAI](https://platform.openai.com/api-keys) — Pay-as-you-go GPT-4o
> *   🟠 [Anthropic](https://console.anthropic.com/) — Pay-as-you-go Claude

### 1. Clone & Install Environment
```bash
git clone https://github.com/VISVA-Ai/V.NOTEBOOK.git
cd V.NOTEBOOK
pip install -r requirements.txt
```

### 2. Configure API Keys

You can configure API keys in **two ways**:

**Option A — Via the Settings UI (Recommended)**
1.  Start the application (see Step 4).
2.  Click the ⚙️ gear icon → **API Keys** tab.
3.  Paste your key(s) for any provider and hit **Save**.

**Option B — Via `.env` file**
```bash
cp .env.example .env
```
```ini
# Pick one or more providers
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=sk-your_openai_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here

# Optional
TAVILY_API_KEY=your_tavily_key_here
```

### 3. (Optional) Google API Setup — Gmail & Calendar

> [!NOTE]
> **1-Click Setup**: V.NOTEBOOK now includes a browser-based OAuth flow. No manual token management required!

1.  Navigate to the [Google Cloud Console](https://console.cloud.google.com).
2.  Create a project and enable the **Gmail API** and **Google Calendar API**.
3.  Configure your **OAuth Consent Screen**.
4.  Generate an **OAuth Client ID** (Desktop App) and download the credential JSON.
5.  Rename it to `credentials.json` and place it in the `backend/` folder.
6.  In the app, go to **Settings → Integrations → Sign in with Google** — done!

### 4. Run the Application

**Quick Start** (using batch files):
```bash
# Terminal 1 — Backend
run_backend.bat

# Terminal 2 — Frontend
run_frontend.bat
```

**Manual Start:**
```bash
# Terminal 1 — Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
python -m http.server 3000
```
Navigate to `http://localhost:3000` to interact with your workspace.

### 5. Select Your Model
Go to **Settings → Preferences** and choose your preferred model:
- `groq/llama-3.3-70b-versatile` (default, fast, free)
- `gemini/gemini-1.5-pro-latest` (Google, free)
- `openai/gpt-4o` (OpenAI, paid)
- `anthropic/claude-sonnet-4-20250514` (Anthropic, paid)

---

## 📁 Repository Structure

```text
V.NOTEBOOK/
├── backend/
│   ├── main.py                    # FastAPI unified app entry point
│   ├── api/
│   │   ├── routes_settings.py     # API key & preferences management
│   │   ├── routes_auth.py         # Google OAuth 2.0 web flow
│   │   ├── routes_notebook.py     # Notebook workspace endpoints
│   │   └── routes_assistant.py    # V.ASSISTANT action endpoints
│   ├── core/                      
│   │   ├── engine.py              # Central orchestrator 
│   │   ├── llm.py                 # LiteLLM-powered multi-provider handler 
│   │   ├── memory.py              # FAISS-backed vector store abstraction 
│   │   ├── decision_engine.py     # V.ASSISTANT intent routing & handling 
│   │   ├── executor.py            # Executable Action dispatching 
│   │   ├── email_intelligence.py  # Gmail cognition & smart replies
│   │   └── adapters/              # Modular API Connections (Gmail/Calendar)
│   └── models/                    # Pydantic structured schemas
├── frontend/
│   ├── index.html                 # Main SPA entry architecture
│   ├── css/                       # Modular UI stylesheets
│   └── js/
│       ├── settings.js            # Settings modal (keys, prefs, integrations)
│       ├── notebook/              # Core Notebook logic scripts
│       └── assistant/             # V.ASSISTANT frontend modules
├── workflows/                     # Declarative n8n workflow templates
└── system_prompt.xml              # Global Constitution & Safety Prompt
```

---

## 🔒 Security Practices

> [!WARNING]
> **Your private API keys and OAuth tokens are NEVER committed to version control.**

This platform enforces a comprehensive local security standard:

| Asset | Protection Mechanism |
| :--- | :--- |
| **API Keys** | Secured in `.env` (Git-ignored). Masked in the Settings UI. |
| **Provider Credentials** | Read from local `credentials.json` (Git-ignored). |
| **OAuth Access Tokens** | Unified in `backend/token.json` (Git-ignored). |
| **Private Chat Sessions** | Constrained entirely to the local `data/` directory. |
| **PKCE State** | Ephemeral `_oauth_pkce_state.json` (auto-cleaned, Git-ignored). |

---

## 🛠️ Advanced Concepts Demonstrated

*   **RAG Engineering**: End-to-end multi-pipeline embedding and retrieval with FAISS and dynamic system context injection.
*   **Semantic Routing**: Categorizes complex natural intent across completely different operational domains (Notebook vs. Assistant vs. Search).
*   **Agentic Function Calling**: Employs deterministic generation, effectively wrapping the LLM behavior to write to local execution queues.
*   **Multi-Provider LLM Routing**: Dynamic model switching via LiteLLM — supports 100+ providers through a single `completion()` interface.
*   **Idempotent Queue Management**: Guarantees zero double-submissions or crashes through atomic JSON state transitions (`Pending` → `Approved` → `Executed`).
*   **Human-in-the-Loop (HITL)**: Prioritizes absolute user supremacy over AI autonomy via the mandatory visual preview card approvals.
*   **Cognitive Learning Subsystem**: Runs isolated analysis tasks across legacy chat sessions to progressively update and adapt user personas.
*   **OAuth 2.0 with PKCE**: Full browser-based Google OAuth flow with disk-persisted code verifiers, supporting both `installed` and `web` client types.

---

## 📋 Known Limitations

*   **WhatsApp Handling**: The existing WhatsApp adapter requires active Meta Business API validation; it defaults to disabled.
*   **Studio Modules**: Audio capabilities require active TTS integrations; video and mindmapping exist as stub architectures for future scaling.
*   **OAuth Scope**: Google sign-in currently supports Gmail and Calendar. Drive integration is planned.

---

<div align="center">
  <p>Available under the <strong>MIT License</strong> — see <a href="LICENSE">LICENSE</a> file directly for usage details.</p>
</div>
