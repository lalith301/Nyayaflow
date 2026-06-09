# NyayaFlow ⚖️
### AI-Powered Legal & Document Navigator for Indian Citizens and SMBs

> Built with Flask · ChromaDB · Groq (Llama 3.3 70B) · React · Whisper

---

## Project Structure

```
nyayaflow/
├── backend/
│   ├── app.py              # Flask server (3 API endpoints)
│   ├── ingest.py           # PDF → chunks → embeddings → ChromaDB
│   ├── rag.py              # Retrieval-Augmented Generation engine
│   ├── document_gen.py     # LLM document drafting + ReportLab PDF
│   ├── whisper_utils.py    # OpenAI Whisper transcription
│   ├── requirements.txt
│   ├── .env.example
│   └── data/
│       └── pdfs/           # ← Put your legal PDFs here
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js          # Axios client
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx        # Legal Q&A chat
│   │   │   └── DocBuilderPage.jsx  # Document wizard
│   │   ├── components/
│   │   │   └── VoiceMicButton.jsx  # Mic → Whisper
│   │   └── hooks/
│   │       └── useVoiceRecorder.js
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual env
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# → Edit .env and add your GROQ_API_KEY
#   Get one free at: https://console.groq.com
```

### 2. Add Legal PDFs

Drop any of these public-domain Indian legal PDFs into `backend/data/pdfs/`:

| Document | Source |
|----------|--------|
| Consumer Protection Act, 2019 | https://consumeraffairs.nic.in |
| Bhartiya Nyaya Sanhita summary | https://legislative.gov.in |
| Standard rental agreement template | (any public template) |

### 3. Run the Ingestion Pipeline

```bash
cd backend
python ingest.py

# To re-ingest from scratch:
python ingest.py --reset

# To ingest a single file:
python ingest.py --file data/pdfs/consumer_protection.pdf
```

You should see output like:
```
[ingest] Found 3 PDFs in ./data/pdfs
[ingest] Loading embedding model: BAAI/bge-small-en-v1.5
  → consumer_protection.pdf: 87 pages → 340 chunks
  → bns_summary.pdf: 45 pages → 178 chunks
[ingest] ✓ Done. Collection 'legal_docs' now has 518 vectors.
```

### 4. Start the Flask Server

```bash
cd backend
python app.py
# → http://localhost:5000
```

Test it:
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are my rights if I receive a defective product?"}'
```

### 5. Start the React Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## API Endpoints

### `POST /api/chat`
Legal Q&A via RAG pipeline.
```json
// Request
{ "query": "Can my landlord evict me without notice?" }

// Response
{
  "answer": "Under the Tamil Nadu Buildings (Lease and Rent Control) Act...",
  "sources": [
    { "source": "tenancy_act.pdf", "page": 12, "similarity": 0.91 }
  ],
  "query": "Can my landlord evict me without notice?"
}
```

### `POST /api/generate-doc`
Draft and download a legal PDF.
```json
// Request
{
  "doc_type": "rental_agreement",
  "fields": {
    "landlord_name": "Ramesh Kumar",
    "tenant_name": "Priya Sharma",
    "property_address": "12, Anna Nagar, Chennai - 600040",
    "monthly_rent": "25000",
    "security_deposit": "50000",
    "start_date": "01 August 2025",
    "duration_months": "11",
    "state": "Tamil Nadu"
  }
}
// Response: PDF file download
```

Supported `doc_type` values:
- `rental_agreement`
- `nda`
- `freelance_contract`
- `employment_offer`
- `vendor_agreement`
- `partnership_deed`
- `affidavit`

### `POST /api/transcribe`
Whisper voice transcription (Hinglish/Hindi/English).
```
# Request: multipart/form-data
audio: <file> (WAV / MP3 / M4A / WebM)

# Response
{ "text": "mera landlord deposit wapas nahi de raha...", "language": "hi" }
```

---

## Testing the RAG Engine

```bash
cd backend
python rag.py
# Runs a test query and prints the answer with sources
```

## Testing Document Generation

```bash
cd backend
python -c "
from document_gen import generate_legal_document
pdf = generate_legal_document('rental_agreement', {
    'landlord_name': 'Test Landlord',
    'tenant_name': 'Test Tenant',
    'property_address': '123, Test Street, Chennai',
    'monthly_rent': '20000',
    'security_deposit': '40000',
    'start_date': '01 July 2025',
    'duration_months': '11',
    'state': 'Tamil Nadu',
})
open('test_output.pdf', 'wb').write(pdf)
print('PDF written to test_output.pdf')
"
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq API — Llama 3.3 70B |
| Embeddings | BAAI/bge-small-en-v1.5 (SentenceTransformers) |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Backend | Flask 3 + Flask-CORS |
| PDF Generation | ReportLab |
| Voice | OpenAI Whisper (base model) |
| Frontend | React 18 + Vite + Tailwind CSS |
| HTTP Client | Axios |

---

## Next Steps (Production Hardening)

- [ ] Add JWT authentication (`/api/auth/register`, `/api/auth/login`)
- [ ] Store chat history per user in PostgreSQL
- [ ] Add Razorpay webhook for paid PDF downloads
- [ ] Upgrade Whisper to `medium` or `large` model for better Hindi accuracy
- [ ] Deploy Flask to Render / AWS EC2, React to Vercel
- [ ] Add more legal corpora (state-specific tenancy acts, GST rules, labour laws)
- [ ] Add re-ranking step (cross-encoder) for better RAG accuracy
