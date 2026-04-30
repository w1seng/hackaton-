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
def classify_subject_by_ai(file_path: str) -> str:
    """Аналізує першу сторінку PDF і визначає назву навчального предмета."""
    try:
        loader = PyPDFLoader(file_path)
        # Завантажуємо лише першу сторінку для економії часу та токенів
        pages = loader.load_and_split()
        first_page_text = pages[0].page_content[:1000] # беремо перші 1000 символів

        classifier_prompt = f"""Проаналізуй текст першої сторінки навчального документа і визнач назву навчальної дисципліни (предмета).
Відповідь має бути ОДНИМ словом у називному відмінку українською мовою (наприклад: Математика, Фізика, Програмування, Філософія).
Якщо предмет важко визначити, напиши "Загальне".

ТЕКСТ:
{first_page_text}

ПРЕДМЕТ:"""

        messages = [{"role": "user", "content": classifier_prompt}]
        subject = call_groq(messages, model="llama-3.1-8b-instant")
        
        # Очищаємо назву від зайвих символів
        clean_subject = subject.strip().replace(".", "").replace('"', '').title()
        return clean_subject
    except Exception as e:
        print(f"❌ Помилка класифікації: {e}")
        return "Загальне"
    
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
    
    # 1. Завантажуємо існуючу базу
    if os.path.exists(DB_FAISS_PATH):
        vector_store = FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
        for doc_id in vector_store.docstore._dict:
            source = vector_store.docstore._dict[doc_id].metadata.get("source")
            if source: loaded_docs_names.add(source)

    # 2. Скануємо підпапки предметів
    all_chunks = []
    
    # Перевіряємо кожну папку в knowledge_base
    for subject_name in os.listdir(KNOWLEDGE_BASE_DIR):
        subject_path = os.path.join(KNOWLEDGE_BASE_DIR, subject_name)
        
        if os.path.isdir(subject_path):
            files = [f for f in os.listdir(subject_path) if f.endswith('.pdf')]
            for file_name in files:
                if file_name not in loaded_docs_names:
                    print(f"⏳ Новий файл у предметі [{subject_name}]: {file_name}")
                    file_path = os.path.join(subject_path, file_name)
                    
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                    for d in docs: 
                        d.metadata["source"] = file_name
                        d.metadata["subject"] = subject_name # ДОДАЄМО ПРЕДМЕТ
                    
                    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
                    all_chunks.extend(splitter.split_documents(docs))
                    loaded_docs_names.add(file_name)

    if all_chunks:
        if vector_store is None:
            vector_store = FAISS.from_documents(all_chunks, embeddings)
        else:
            vector_store.add_documents(all_chunks)
        vector_store.save_local(DB_FAISS_PATH)
        print("✅ База знань по предметах оновлена!")

# =========================
# API ENDPOINTS
# =========================

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    global vector_store, loaded_docs_names
    
    # 1. Тимчасово зберігаємо файл, щоб AI міг його прочитати
    temp_path = os.path.join(KNOWLEDGE_BASE_DIR, f"temp_{file.filename}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 2. AI визначає предмет
        subject = classify_subject_by_ai(temp_path)
        print(f"📦 AI визначив предмет для '{file.filename}': {subject}")

        # 3. Створюємо динамічну папку предмета
        subject_dir = os.path.join(KNOWLEDGE_BASE_DIR, subject)
        os.makedirs(subject_dir, exist_ok=True)
        
        # 4. Переносимо файл з темп-папки в папку предмета
        final_path = os.path.join(subject_dir, file.filename)
        shutil.move(temp_path, final_path)
        
        # 5. Індексуємо файл для RAG
        loader = PyPDFLoader(final_path)
        docs = loader.load()
        for doc in docs: 
            doc.metadata["source"] = file.filename
            doc.metadata["subject"] = subject
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_documents(docs)

        if vector_store is None:
            vector_store = FAISS.from_documents(chunks, embeddings)
        else:
            vector_store.add_documents(chunks)
        
        vector_store.save_local(DB_FAISS_PATH)
        loaded_docs_names.add(file.filename)
        
        return {
            "message": "Файл успішно класифіковано та додано",
            "detected_subject": subject,
            "file": file.filename
        }
        
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ask")
async def ask_ai(request: ChatRequest):
    global vector_store
    
    decision = route_query(request.query)

    if decision == "DOCS" and vector_store:
        search_query = refine_query_for_search(request.query)
        docs = vector_store.similarity_search(search_query, k=4)

        # Формуємо контекст із зазначенням ПРЕДМЕТА
        context_parts = []
        found_subjects = set()
        for d in docs:
            subj = d.metadata.get('subject', 'Загальне')
            src = d.metadata.get('source', 'Невідомий')
            found_subjects.add(subj)
            context_parts.append(f"[ПРЕДМЕТ: {subj} | ФАЙЛ: {src}]\n{d.page_content}")
            
        context = "\n\n".join(context_parts)

        system_prompt = f"""Ти — академічний асистент UniNexus. 
Ти знайшов інформацію у матеріалах з таких предметів: {', '.join(found_subjects)}.

Відповідай виключно на основі КОНТЕКСТУ. 
Якщо питання стосується одного предмета, а інформація знайдена в іншому — попередь про це.
Обов'язково вказуй [Предмет | Файл].

КОНТЕКСТ:
{context}
"""
    else:
        system_prompt = "Ти — дружній асистент UniNexus. Спілкуйся на загальні теми."

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": request.query}]
    answer = call_groq(messages)
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