# NyayaFlow ⚖️

### AI-Powered Legal Navigator for Indian Citizens and SMBs

> **Live:** [nyayaflow-five.vercel.app](https://nyayaflow-five.vercel.app) · **Backend:** [nyayaflow.mooo.com](https://nyayaflow.mooo.com/api/health)

NyayaFlow is a production-ready B2C SaaS legal assistant that answers questions grounded in Indian law — with section-level precision, real-time streaming responses, and verifiable citations linking directly to official government documents. It doesn't just search a static database: it autonomously fetches, validates, and permanently learns any Indian Act it hasn't seen before.

---

## ✨ What Makes It Different

Most legal chatbots either hallucinate or are limited to a fixed set of documents. NyayaFlow solves both problems:

- **Self-expanding knowledge** — when asked about an Act not in the database, it searches indiacode.nic.in via DuckDuckGo, downloads the official PDF, validates it, extracts the relevant sections using embedding-based retrieval, answers the query, and permanently ingests the document for future use — all automatically.
- **Section-level precision** — relevance-based chunk retrieval finds the exact section inside a 500-page Act instead of truncating to the first few pages.
- **Verifiable citations** — every answer links directly to the official PDF on indiacode.nic.in so users can verify the source themselves.
- **Honest confidence signals** — green (from database), amber (fetched live), red (low confidence) badges tell users exactly how reliable each answer is.

---

## 🚀 Features

| Feature | Details |
|---|---|
| **Legal Q&A** | RAG pipeline over 14,000+ vectors across 20+ Indian Acts |
| **Agentic fetch** | Autonomously finds and ingests unknown Acts from indiacode.nic.in |
| **Streaming responses** | Token-by-token SSE with live status ("Searching indiacode.nic.in…") |
| **Source links** | Every citation links to the official government PDF |
| **Confidence badges** | DB / Fetched live / Low confidence — honest about answer quality |
| **Voice input** | Hindi/Hinglish/English via Groq Whisper transcription |
| **Document Builder** | Generates legally formatted PDFs (rental agreements, NDAs, affidavits, etc.) |
| **Token economy** | 100 free tokens on signup; Razorpay UPI/card top-up |
| **Auth** | Email/password + Google OAuth (JWT) |
| **Chat history** | Persistent per-user chat history |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Groq API — Llama 3.3 70B Versatile |
| **Embeddings** | Cohere `embed-multilingual-light-v3.0` |
| **Vector DB** | Qdrant Cloud (14,000+ vectors, cosine similarity) |
| **Chunking** | LangChain RecursiveCharacterTextSplitter |
| **Agentic search** | DuckDuckGo Search API (no key needed) |
| **Backend** | Flask 3 + Flask-CORS + Flask-JWT-Extended |
| **Streaming** | Server-Sent Events (SSE) via Flask `Response` |
| **Database** | Supabase PostgreSQL (users, chat history, transactions) |
| **PDF generation** | ReportLab |
| **Voice** | Groq Whisper API |
| **Payments** | Razorpay (UPI, cards, net banking) |
| **Frontend** | React 18 + Vite |
| **Auth** | JWT + Google OAuth (Google Identity Services / FedCM) |
| **Deployment** | AWS EC2 (gunicorn + nginx) + Vercel |
| **SSL** | Let's Encrypt via Certbot (auto-renewing) |

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────┐
│              Flask Backend (AWS EC2)         │
│                                             │
│  1. Embed query (Cohere)                    │
│  2. Search Qdrant (top-6 chunks)            │
│  3. Similarity check (< 0.65 → agent path) │
│  4a. DB path: LLM answers from chunks       │
│  4b. Agent path:                            │
│      → Identify Act (Groq)                  │
│      → DuckDuckGo search indiacode.nic.in   │
│      → Download + validate PDF              │
│      → Relevance-based chunk retrieval      │
│      → LLM answers from relevant chunks     │
│      → Background ingest to Qdrant          │
│  5. Stream tokens via SSE                   │
└─────────────────────────────────────────────┘
    │
    ▼
React Frontend (Vercel)
    │
    ├── Live status messages during agent fetch
    ├── Token-by-token streaming render
    ├── Confidence badge (DB / Fetched live / Low)
    └── Source link → official PDF on indiacode.nic.in
```

---

## 📁 Project Structure

```
nyayaflow/
├── backend/
│   ├── app.py              # Flask server + SSE streaming endpoint
│   ├── agent.py            # Agentic pipeline (fetch → validate → answer → ingest)
│   ├── rag.py              # RAG engine (Qdrant + Cohere + Groq)
│   ├── ingest.py           # PDF → chunks → embeddings → Qdrant
│   ├── source_links.py     # Official PDF URL registry
│   ├── auth.py             # JWT auth + Google OAuth + Razorpay
│   ├── models.py           # SQLAlchemy models (User, ChatMessage, Transaction)
│   ├── document_gen.py     # Legal PDF generation (ReportLab)
│   ├── whisper_utils.py    # Voice transcription (Groq Whisper)
│   ├── requirements.txt
│   └── data/
│       ├── pdfs/           # Downloaded legal PDFs (auto-populated by agent)
│       └── source_urls.json # Maps PDF filenames → official indiacode.nic.in URLs
├── frontend/
│   ├── src/
│   │   ├── api.js              # Axios client + SSE stream generator
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx        # Legal Q&A with streaming
│   │   │   ├── DocBuilderPage.jsx  # Document wizard
│   │   │   └── AuthPage.jsx        # Login / Register / Google OAuth
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   └── components/
│   │       └── VoiceMicButton.jsx
│   └── vite.config.js
└── README.md
```

---

## ⚡ Quick Start (Local)

### 1. Clone and set up backend

```bash
git clone https://github.com/lalith301/Nyayaflow.git
cd Nyayaflow/backend

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in: GROQ_API_KEY, COHERE_API_KEY, QDRANT_URL, QDRANT_API_KEY,
#          DATABASE_URL, JWT_SECRET_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
```

### 2. Ingest seed documents

```bash
# Drop PDFs into data/pdfs/ then:
python ingest.py

# Single file:
python ingest.py --file data/pdfs/consumer_protection.pdf

# Reset and re-ingest everything:
python ingest.py --reset
```

### 3. Start the backend

```bash
python app.py
# → http://localhost:8000
```

### 4. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 🔌 API Reference

### `POST /api/chat/stream` *(SSE)*
Streams the answer token-by-token with live status updates.

```
# Events emitted:
{ "type": "status",  "message": "Searching indiacode.nic.in for Motor Vehicles Act..." }
{ "type": "token",   "content": "According to Section 166..." }
{ "type": "done",    "sources": [...], "used_agent": true, "law_fetched": "Motor Vehicles Act 1988" }
{ "type": "tokens_remaining", "value": 94 }
```

### `POST /api/chat`
Non-streaming fallback. Returns full JSON response.

### `POST /api/generate-doc`
Generates a downloadable legal PDF. Supported `doc_type` values:
`rental_agreement`, `nda`, `freelance_contract`, `employment_offer`, `affidavit`

### `POST /api/transcribe`
Accepts audio (WAV/MP3/M4A/WebM), returns transcribed text + detected language.

### `POST /api/auth/register` · `POST /api/auth/login` · `POST /api/auth/google`
JWT auth endpoints. Google OAuth verifies the GSI credential server-side.

### `GET /api/tokens/plans` · `POST /api/tokens/order` · `POST /api/tokens/verify`
Razorpay token purchase flow.

---

## 🧠 How the Agent Works

When a query's similarity score against the existing database is below 0.65 (wrong Act retrieved), the agentic pipeline activates:

1. **Identify the Act** — Groq LLM identifies which Indian Act the query requires
2. **Targeted DB search** — checks if the Act already exists in Qdrant by filename/year matching
3. **DuckDuckGo search** — searches `site:indiacode.nic.in` and `site:legislative.gov.in`
4. **Download & validate** — downloads the PDF, checks it's actually the right Act (not a gazette notification), rejects garbage
5. **Relevance retrieval** — splits the document into 2,000-char chunks, embeds all (capped at 80 chunks for speed), picks the 8 most relevant to the query
6. **Answer** — Groq LLM answers from the relevant chunks only
7. **Background ingest** — the full PDF is chunked and ingested into Qdrant permanently using a separate Cohere API key (to avoid rate-limit collisions with live queries)

---

## 🌐 Production Deployment

| Component | Details |
|---|---|
| **Frontend** | Vercel (auto-deploys on `git push main`) |
| **Backend** | AWS EC2 t3.micro, Mumbai (ap-south-1) |
| **Process manager** | gunicorn (1 worker, 300s timeout) via systemd |
| **Reverse proxy** | nginx (handles SSL termination, proxy buffering off for SSE) |
| **SSL** | Let's Encrypt (Certbot, auto-renews every 90 days) |
| **Domain** | nyayaflow.mooo.com (FreeDNS) |
| **Database** | Supabase PostgreSQL |
| **Vectors** | Qdrant Cloud |

---

## 📄 Supported Document Types

| Template | Fields |
|---|---|
| Rental Agreement | Landlord, Tenant, Property, Rent, Deposit, Duration, State |
| NDA | Disclosing Party, Receiving Party, Purpose, Duration |
| Freelance Contract | Client, Freelancer, Scope, Rate, Deliverables |
| Employment Offer | Candidate, Role, Salary, Start Date, Location |
| Affidavit | Deponent, Statement, Date, Place |

---

## 🤝 Contributing

Pull requests welcome. For major changes, open an issue first.

---

## 📜 License

MIT License

---

<p align="center">
  Built with ⚖️ for Indian citizens · Powered by Groq · Grounded in official Indian legal corpus
</p>