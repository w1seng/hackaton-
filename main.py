import os
import requests
from dotenv import load_dotenv 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil # Додай це нагорі до імпортів
from fastapi import FastAPI, HTTPException, UploadFile, File # Додай UploadFile, File

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
vector_store = None
retriever = None

# =========================
# CONFIG
# =========================
XAI_API_KEY = os.getenv("XAI_API_KEY") 

if not XAI_API_KEY:
    # Краще викидати помилку одразу, щоб сервер не працював вхолосту
    raise ValueError("❌ Помилка: XAI_API_KEY не знайдено у файлі .env")
KNOWLEDGE_BASE_DIR = "./knowledge_base"

def load_all_documents():
    global vector_store, retriever
    
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        os.makedirs(KNOWLEDGE_BASE_DIR)
        print(f"📁 Папка {KNOWLEDGE_BASE_DIR} створена.")
        return

    all_docs = []
    pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("⚠️ У папці knowledge_base немає PDF.")
        return

    print(f"📚 Індексація {len(pdf_files)} файлів...")
    for file_name in pdf_files:
        try:
            loader = PyPDFLoader(os.path.join(KNOWLEDGE_BASE_DIR, file_name))
            docs = loader.load()
            for doc in docs:
                doc.metadata["file_name"] = file_name
            all_docs.extend(docs)
        except Exception as e:
            print(f"❌ Помилка файлу {file_name}: {e}")

    if all_docs:
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
        chunks = splitter.split_documents(all_docs)
        embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")
        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(search_kwargs={"k": 4})
        print("✅ База знань готова!")
app = FastAPI(title="UniNexus Grok Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def startup_event():
    load_all_documents()
#
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

def route_query(query: str):
    """Агент-диспетчер: вирішує, чи потрібні нам документи."""
    router_prompt = f"""
    Ти — диспетчер запитів UniNexus. Твоє завдання — вирішити, чи потребує питання пошуку в базі знань (лекції, методички), чи це просто загальне спілкування.

    ПИТАННЯ: "{query}"

    Відповідай ТІЛЬКИ одним словом:
    - DOCS: якщо питання стосується навчання, конкретних тем з лекцій, формул або методичок.
    - GENERAL: якщо це привітання ("Привіт", "Як справи"), загальне питання, жарт або прохання, яке не стосується твоїх PDF.

    ВІДПОВІДЬ:
    """
    messages = [{"role": "user", "content": router_prompt}]
    # Викликаємо Groq, щоб він прийняв рішення
    decision = call_grok(messages).strip().upper()
    
    # Повертаємо рішення
    if "DOCS" in decision:
        return "DOCS"
    return "GENERAL"
# =========================
# ASK AI
# =========================
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    global vector_store, retriever
    
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        loader = PyPDFLoader(temp_file_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""],
            add_start_index=True
            
        )

        chunks = splitter.split_documents(docs)
        
        # --- МАГІЯ: ВИЗНАЧЕННЯ НАЗВИ ЧЕРЕЗ GROQ ---
        # Беремо перші 1000 символів документу (титулку)
        first_page_content = chunks[0].page_content[:1000]
        
        title_messages = [
            {
                "role": "system", 
                "content": "Ти — асистент UniNexus. Прочитай текст титульної сторінки та витягни коротку офіційну назву роботи або предмету (макс 3-5 слів) українською мовою. Поверни ТІЛЬКИ назву."
            },
            {"role": "user", "content": first_page_content}
        ]
        
        # Викликаємо твій Groq
        nice_title = call_grok(title_messages)
        nice_title = nice_title.strip().replace('"', '') # чистимо лапки
        # ------------------------------------------

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(search_kwargs={"k": 4})

        # ПОВЕРТАЄМО НАЗВУ ФРОНТЕНДУ
        return {
            "message": "Вивчено!", 
            "extracted_title": nice_title 
        }
        
    except Exception as e:
        print(f"❌ Помилка RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
@app.post("/api/ask")
async def ask_ai(request: ChatRequest):
    global retriever
    
    # 1. Агент аналізує запит
    decision = route_query(request.query)
    print(f"🤖 Агент прийняв рішення: {decision}")

    # 2. Вибір логіки на основі рішення
    if decision == "DOCS" and retriever:
        # ШЛЯХ RAG: Шукаємо в документах
        docs = retriever.invoke(request.query)
        context = ""
        for d in docs:
            fname = d.metadata.get("file_name", "Документ")
            page = d.metadata.get("page", 0) + 1
            context += f"\n[Джерело: {fname}, стор. {page}]\n{d.page_content}\n"

        system_prompt = f"""
        Ти — інтелектуальний асистент UniNexus. 
        Давай відповіді ТІЛЬКИ на основі наданого контексту з навчальних матеріалів. 
        Обов'язково вказуй назву файлу та номер сторінки.
        КОНТЕКСТ:
        {context}
        """
    else:
        # ШЛЯХ GENERAL: Просто спілкуємося
        system_prompt = """
        Ти — дружній AI-асистент UniNexus. 
        Зараз ти спілкуєшся на загальні теми (привітання, розмова). 
        Будь корисним, використовуй емодзі. 
        Якщо запитають щось складне по навчанню, скажи, що можеш пошукати це в завантажених методичках.
        """

    # 3. Формуємо фінальний запит до ШІ
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.query}
    ]
    
    try:
        answer = call_grok(messages)
        return {
            "answer": answer,
            "agent_decision": decision  # Корисно для фронтенду
        }
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