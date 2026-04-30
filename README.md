# <img src="https://raw.githubusercontent.com/Tarik02/Tarik02/main/assets/sparkles.gif" width="30"> UniNexus AI: Smart Student Ecosystem

<p align="center">
  <img src="https://private-user-images.githubusercontent.com/206721479/585964283-9669128a-b149-4439-ad9f-9533bba6d607.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3Nzc1NDY0MjMsIm5iZiI6MTc3NzU0NjEyMywicGF0aCI6Ii8yMDY3MjE0NzkvNTg1OTY0MjgzLTk2NjkxMjhhLWIxNDktNDQzOS1hZDlmLTk1MzNiYmE2ZDYwNy5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwNDMwJTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDQzMFQxMDQ4NDNaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT1iNDUyYjYzNWFlOWY2ODRlZGUzZmQwYzBlNDMzZjkyZDU4ZjgwZjIzN2MxZDRjNWY5MzhmOTQzY2I1MzI2MGZjJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCZyZXNwb25zZS1jb250ZW50LXR5cGU9aW1hZ2UlMkZwbmcifQ._tifhuwyIB2OPurqiWd86bXLVchMrIsR25WMsOaGcAA" alt="UniNexus Banner" width="800">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-005863?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq_AI-F55036?style=for-the-badge&logo=google-cloud&logoColor=white" />
  <img src="https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=chainlink&logoColor=white" />
</p>

---

## 🌟 Про проєкт
**UniNexus AI** — це інтелектуальна система управління навчанням (LMS 2.0), яка перетворює статичний університетський розклад на інтерактивну екосистему. Проєкт автоматично збирає знання всієї групи та надає AI-асистента для допомоги у навчанні.

### 🎥 [Демо-відео] | 🌐 [Живий сайт (link)]

---

## 🚀 Основні функції
- 📅 **Dynamic Schedule:** Синхронізація з БД університету та миттєві Push-сповіщення про зміни.
- 🧠 **RAG Knowledge Base:** Завантажуйте PDF та тексту. AI проіндексує їх для швидкого пошуку.
- 💬 **AI Assistant (Llama 3.3):** Ставте питання по лекціях: *"Що було на 5-й парі?"*.
- 🤝 **Collective Memory:** Спільний доступ до конспектів та ресурсів для всієї групи.
- 🌓 **Modern UI/UX:** Темна та світла теми, адаптовані для зручного використання під час занять.

---

## 🛠 Технічний стек
| Напрям | Технології |
| :--- | :--- |
| **Backend** | Python, FastAPI, SQLAlchemy, Supabase |
| **Frontend** | React, Next.js, Tailwind CSS |
| **AI / ML** | Groq API, LangChain, FAISS (Vector DB), Sentence Transformers |
| **DevOps** | GitHub Actions, Docker, Vercel |

---

## ⚙️ Швидкий запуск

### 1. Клонування та налаштування
```bash
git clone https://github.com/w1seng/hackaton-.git
cd hackaton-
2. Встановлення залежностей
ls

"fastapi`nuvicorn`nrequests`nlangchain`nlangchain-community`nlangchain-text-splitters`nfaiss-cpu`nsentence-transformers`npython-dotenv" | Out-File -FilePath requirements.txt -Encoding utf8

pip install -r requirements.txt

