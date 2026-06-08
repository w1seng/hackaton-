# UniNexus AI — Smart Student Ecosystem

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005863?style=for-the-badge&logo=fastapi&logoColor=white)
![Groq AI](https://img.shields.io/badge/Groq_AI-F55036?style=for-the-badge&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logoColor=white)

## About

**UniNexus AI** is an intelligent student assistant that combines a university schedule parser with a RAG-powered AI chatbot. Upload your lecture PDFs and ask the AI questions about the material — it searches through your documents and answers using only the relevant content.

## Features

- **Schedule parser** — scrapes the NUNG university timetable and serves it via REST API
- **RAG knowledge base** — upload PDFs; the backend indexes them with FAISS for fast semantic search
- **AI assistant (Llama 3.3 via Groq)** — answers questions strictly from uploaded documents
- **Smart routing** — an agent decides whether to search docs or just chat
- **Query refinement** — a lightweight model rewrites the search query for better retrieval

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI, LangChain, FAISS |
| AI | Groq API (Llama 3.3 70B), HuggingFace Embeddings |
| Frontend server | Node.js, Express, Cheerio |
| Frontend UI | HTML/CSS/JS (served via Express) |

## Project structure

```
uninexus/
├── main.py              # FastAPI backend (RAG + AI)
├── requirements.txt
├── .env.example
├── knowledge_base/      # Sample lecture PDFs (loaded on startup)
└── Frontend/
    ├── index.html       # Main UI
    ├── shed.js          # Express server (schedule scraper)
    └── package.json
```

## Setup

### Backend

```bash
# 1. Clone the repo
git clone https://github.com/your-username/uninexus.git
cd uninexus

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Groq API key
cp .env.example .env
# Edit .env → paste your GROQ_API_KEY
# Get a free key at https://console.groq.com

# 5. Start the backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. PDFs in `knowledge_base/` are indexed automatically on startup.

### Frontend

```bash
cd Frontend
npm install
node shed.js
```

The schedule server runs at `http://localhost:3000`.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ask` | Ask the AI a question |
| `POST` | `/api/upload` | Upload a PDF to the knowledge base |
| `GET` | `/api/status` | Check if the vector store is ready |
| `POST` | `/api/clear` | Clear the vector store and all PDFs |

### Example request

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Що таке інкапсуляція?"}'
```

## How it works

1. **Upload** — PDFs are split into 800-character chunks and embedded with `intfloat/multilingual-e5-small`
2. **Ask** — the agent routes the query: `DOCS` (search knowledge base) or `GENERAL` (free chat)
3. **Retrieve** — the query is refined by a fast model, then top-4 chunks are fetched from FAISS
4. **Answer** — Llama 3.3 generates a response strictly from the retrieved context
