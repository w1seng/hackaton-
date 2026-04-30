import os
import requests
import shutil
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# =========================
# CONFIG
# =========================
load_dotenv() # Завантажуємо змінні з .env файлу

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ Помилка: GROQ_API_KEY не знайдено у файлі .env")

DB_FAISS_PATH = "vectorstore/db_faiss"
EMBEDDINGS_MODEL = "intfloat/multilingual-e5-small" 
KNOWLEDGE_BASE_DIR = "knowledge_base"

# Створюємо папки, якщо їх нема
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_FAISS_PATH), exist_ok=True)

app = FastAPI(title="UniNexus Grok Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальні змінні для RAG
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)
vector_store = None
loaded_docs_names = set()

class ChatRequest(BaseModel):
    query: str
    image_base64: Optional[str] = None
    history: Optional[List[dict]] = []

# =========================
# CORE FUNCTIONS
# =========================

def call_groq(messages, model="llama-3.3-70b-versatile"): # Використовуємо легшу модель, щоб не ловити ліміти
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        result = response.json()
        if response.status_code != 200:
            print(f"❌ Groq Error: {result}")
            return f"Помилка API Groq: {result.get('error', {}).get('message', 'Невідома помилка')}"
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return "Помилка зв'язку з сервером AI. Перевірте консоль."

def refine_query_for_search(query: str) -> str:
    """Використовує AI для витягування ключових слів для кращого пошуку."""
    refiner_prompt = f"""Витягни з питання користувача ключові терміни для пошуку в базі документів. 
Відповідь має бути короткою, 2-4 слова.
Питання: "{query}"
Ключові терміни:"""
    
    messages = [{"role": "user", "content": refiner_prompt}]
    refined_query = call_groq(messages, model="llama-3.1-8b-instant")
    print(f"🔍 Початковий запит: '{query}' -> Пошуковий запит: '{refined_query.strip()}'")
    return refined_query.strip()

@app.on_event("startup")
async def startup_event():
    global vector_store, loaded_docs_names
    
    # 1. Завантажуємо існуючу векторну базу з диска
    if os.path.exists(DB_FAISS_PATH):
        vector_store = FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
        for doc_id in vector_store.docstore._dict:
            source = vector_store.docstore._dict[doc_id].metadata.get("source")
            if source: loaded_docs_names.add(source)

    # 2. Синхронізуємо папку knowledge_base з базою
    all_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
    new_files = [f for f in all_files if f not in loaded_docs_names]

    if new_files:
        print(f"⏳ Знайдено нові файли ({len(new_files)}). Додаю до бази...")
        all_chunks = []
        for file_name in new_files:
            file_path = os.path.join(KNOWLEDGE_BASE_DIR, file_name)
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            for d in docs: d.metadata["source"] = file_name
            
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            all_chunks.extend(splitter.split_documents(docs))
            loaded_docs_names.add(file_name)

        if all_chunks:
            if vector_store is None:
                vector_store = FAISS.from_documents(all_chunks, embeddings)
            else:
                vector_store.add_documents(all_chunks)
            vector_store.save_local(DB_FAISS_PATH)
            print("✅ База оновлена і збережена на диск!")

def route_query(query: str):
    """Агент-диспетчер: вирішує, чи потрібні документи."""
    router_prompt = f"""Ти — диспетчер запитів. Виріши, чи потребує питання пошуку в базі знань, чи це просто спілкування.
ПИТАННЯ: "{query}"
Відповідай ТІЛЬКИ одним словом:
- DOCS: якщо питання стосується навчання, лекцій, конспектів.
- GENERAL: якщо це привітання, жарт, загальне питання.
ВІДПОВІДЬ:"""
    messages = [{"role": "user", "content": router_prompt}]
    decision = call_groq(messages, model="llama-3.3-70b-versatile").strip().upper()
    return "DOCS" if "DOCS" in decision else "GENERAL"

# =========================
# API ENDPOINTS
# =========================

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    global vector_store, loaded_docs_names
    
    file_path = os.path.join(KNOWLEDGE_BASE_DIR, file.filename)
    
    # Зберігаємо файл у постійну папку
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        for doc in docs: doc.metadata["source"] = file.filename
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_documents(docs)

        if vector_store is None:
            vector_store = FAISS.from_documents(chunks, embeddings)
        else:
            vector_store.add_documents(chunks)
        
        vector_store.save_local(DB_FAISS_PATH)
        loaded_docs_names.add(file.filename)
        return {"message": "Success", "extracted_title": file.filename, "all_docs": list(loaded_docs_names)}
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ask")
async def ask_ai(request: ChatRequest):
    global vector_store
    
    decision = route_query(request.query)
    print(f"🤖 Агент прийняв рішення: {decision}")

    if decision == "DOCS" and vector_store:
        # --- НОВА ЛОГІКА ---
        # 1. Покращуємо запит для пошуку
        search_query = refine_query_for_search(request.query)
        
        # 2. Шукаємо по покращеному запиту
        docs = vector_store.similarity_search(search_query, k=4)
        # --------------------

        if not docs:
            context = "Контекст порожній. Нічого не знайдено."
        else:
            context = "\n\n".join([f"[Файл: {d.metadata.get('source', 'Невідомий')}]\n{d.page_content}" for d in docs])

        system_prompt = f"""Ти — суворий AI-асистент UniNexus. 
Твоя задача — відповідати виключно на основі наданого контексту.

ПРАВИЛА:
1. Проаналізуй КОНТЕКСТ. Чи містить він відповідь на запит: "{request.query}"?
2. ЯКЩО ТАК: Дай чітку відповідь, використовуючи ТІЛЬКИ інформацію з КОНТЕКСТУ.
3. ЯКЩО НІ: (контекст нерелевантний або порожній) — Не вигадуй. Відповідай: "На жаль, у моїй базі знань немає інформації на тему '{request.query}'. Будь ласка, завантажте відповідний PDF."
4. ЗАБОРОНЕНО: Використовувати свої загальні знання.

КОНТЕКСТ З ДОКУМЕНТІВ:
{context}
"""
    else:
        # ПРОСТО СПІЛКУЄМОСЯ
        system_prompt = "Ти — дружній AI-асистент UniNexus. Спілкуйся на загальні теми."

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": request.query})
    
    answer = call_groq(messages, model="llama-3.3-70b-versatile")
    return {"answer": answer, "agent_decision": decision}

@app.get("/api/status")
async def get_status():
    return {"is_ready": vector_store is not None, "documents": list(loaded_docs_names)}

@app.post("/api/clear")
async def clear_db():
    global vector_store, loaded_docs_names
    if os.path.exists("vectorstore"): shutil.rmtree("vectorstore")
    if os.path.exists(KNOWLEDGE_BASE_DIR):
        shutil.rmtree(KNOWLEDGE_BASE_DIR)
        os.makedirs(KNOWLEDGE_BASE_DIR) # Створюємо папку заново
    vector_store = None
    loaded_docs_names.clear()
    return {"status": "cleared"}

@app.post("/api/schedule-alert")
async def schedule_alert(request: dict):
    return {"alert_message": f"Система готова! База знань містить {len(loaded_docs_names)} файлів."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)