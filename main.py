import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


# =========================
# CONFIG
# =========================
XAI_API_KEY = os.environ["XAI_API_KEY"]

if not XAI_API_KEY:
    print("❌ Set XAI_API_KEY in environment")

app = FastAPI(title="UniNexus Grok Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# MODELS
# =========================
class ChatRequest(BaseModel):
    query: str
    image_base64: Optional[str] = None


class ScheduleChangeRequest(BaseModel):
    original_event: str
    change_reason: str


# =========================
# GLOBAL RAG
# =========================
vector_store = None
retriever = None


# =========================
# INIT RAG (LOCAL EMBEDDINGS)
# =========================
@app.on_event("startup")
def init_rag():
    global vector_store, retriever

    pdf_path = "notes.pdf"

    if not os.path.exists(pdf_path):
        print("⚠️ notes.pdf not found")
        return

    print("📚 Loading PDF...")

    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = FAISS.from_documents(chunks, embeddings)
    retriever = vector_store.as_retriever(k=3)

    print("✅ RAG READY")


# =========================
# GROK CALL (xAI API)
# =========================
GROQ_MODEL = "llama-3.3-70b-versatile"
def call_grok(messages):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}", # твій gsk_ ключ
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.2 # для RAG краще менша температура
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            return f"Помилка API: {response.text}"
            
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Помилка зв'язку: {str(e)}"


# =========================
# ASK AI
# =========================
@app.post("/api/ask")
async def ask_ai(request: ChatRequest):
    global retriever

    context = "Empty knowledge base."

    if retriever:
        docs = retriever.invoke(request.query)
        context = "\n\n".join([d.page_content for d in docs])

    messages = [
        {
            "role": "system",
            "content": f"""
You are a smart student assistant.

Knowledge base:
{context}

Answer clearly and structured.
"""
        },
        {
            "role": "user",
            "content": request.query
        }
    ]

    try:
        answer = call_grok(messages)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# SCHEDULE ALERT
# =========================
@app.post("/api/schedule-alert")
async def schedule_alert(request: ScheduleChangeRequest):

    messages = [
        {
            "role": "system",
            "content": "You are a friendly AI assistant that writes short funny notifications."
        },
        {
            "role": "user",
            "content": f"""
Schedule: {request.original_event}
Change: {request.change_reason}

Write 2-3 sentences with emojis.
"""
        }
    ]

    try:
        result = call_grok(messages)
        return {"alert_message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# RUN
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)