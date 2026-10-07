# RAG Document Q&A

An end-to-end Retrieval-Augmented Generation (RAG) application. Upload your PDFs, ask questions in a React UI, and get answers grounded in your documents with source citations.

**Stack:** Python · FastAPI · Postgres + pgvector · sentence-transformers · Claude API · React · Docker · GitHub Actions · AWS App Runner · Netlify

---

## Table of Contents

1. [How it works](#how-it-works)
2. [Architecture](#architecture)
3. [Tools and their roles](#tools-and-their-roles)
4. [Project structure](#project-structure)
5. [Database schema](#database-schema)
6. [API endpoints](#api-endpoints)
7. [Local setup](#local-setup)
8. [Evaluation](#evaluation)
9. [CI/CD](#cicd)
10. [Deployment](#deployment)
11. [Where things run](#where-things-run)
12. [Build roadmap](#build-roadmap)
13. [Future improvements](#future-improvements)

---

## How it works

The system has two pipelines.

**Ingestion (offline, run when documents change):** PDFs are parsed into text, split into overlapping chunks, converted to vectors by an embedding model, and stored in Postgres with pgvector.

**Query (online, per question):** The user's question is embedded with the same model, the most similar chunks are retrieved from Postgres, and those chunks are passed to an LLM with instructions to answer only from the provided context and cite sources.

---

## Architecture

### System overview

```mermaid
flowchart LR
    U([User]) --> FE[React UI<br/>Netlify]
    FE -->|HTTPS /ask| API[FastAPI backend<br/>Docker on AWS App Runner]
    API --> EMB[Embedding model<br/>BGE-small, in container]
    API --> DB[(Postgres + pgvector<br/>Neon or AWS RDS)]
    API --> LLM[LLM API<br/>Claude]
    S3[(S3 bucket<br/>raw PDFs)] -.-> ING[Ingestion script]
    ING --> EMB
    ING --> DB
    GH[GitHub Actions] -.->|build, push, deploy| API
```

### Ingestion pipeline

```mermaid
flowchart LR
    A[PDF files] --> B[Parse text<br/>pypdf / PyMuPDF]
    B --> C[Clean text]
    C --> D[Chunk<br/>~500 tokens, 50 overlap]
    D --> E[Embed chunks<br/>sentence-transformers]
    E --> F[(pgvector<br/>chunks table)]
    D --> G[Attach metadata<br/>file, page, chunk index]
    G --> F
```

### Query pipeline

```mermaid
sequenceDiagram
    participant U as User (React)
    participant API as FastAPI
    participant E as Embedding model
    participant DB as Postgres/pgvector
    participant L as LLM API

    U->>API: POST /ask {question}
    API->>E: embed(question)
    E-->>API: query vector
    API->>DB: top-k cosine similarity search
    DB-->>API: k chunks + metadata
    API->>L: prompt = instructions + chunks + question
    L-->>API: grounded answer
    API-->>U: answer + sources (file, page)
```

### CI/CD flow

```mermaid
flowchart LR
    Dev[git push] --> GH[GitHub]
    GH --> T[GitHub Actions:<br/>lint + tests + eval smoke test]
    T --> B[Build Docker image]
    B --> ECR[(AWS ECR)]
    ECR --> AR[AWS App Runner<br/>auto-deploy]
    GH -->|frontend build| NL[Netlify]
```

---

## Tools and their roles

| Tool | Role in this project |
|---|---|
| **Python 3.11+** | Language for ingestion, retrieval, backend, and evaluation |
| **pypdf / PyMuPDF** | Extract text and page numbers from PDFs |
| **sentence-transformers** | Runs the embedding model (`BAAI/bge-small-en-v1.5`, 384 dimensions) locally on CPU |
| **Postgres + pgvector** | Stores chunks, metadata, and vectors. Performs similarity search with SQL |
| **SQL** | Schema creation, similarity queries, metadata filtering, query logs |
| **psycopg (v3)** | Python driver for Postgres |
| **Claude API (Anthropic)** | Generates the final answer from retrieved context |
| **FastAPI + Uvicorn** | HTTP backend exposing `/ask` and `/ingest` |
| **Pydantic** | Request/response validation |
| **React (Vite)** | Chat UI that shows answers and source citations |
| **Docker / docker-compose** | Reproducible local environment (Postgres + API) and the deployable image |
| **Git + GitHub** | Version control and hosting of the repo |
| **GitHub Actions** | Automates tests, image build, and deployment |
| **AWS ECR** | Stores the backend Docker image |
| **AWS App Runner** | Runs the backend container with HTTPS and autoscaling |
| **AWS S3** | Stores raw PDFs (optional, for deployed ingestion) |
| **AWS Secrets Manager** | Holds API keys and DB credentials in production |
| **Neon or AWS RDS** | Managed Postgres with pgvector for production |
| **Netlify** | Hosts the React frontend |
| **Ragas / custom eval scripts** | Measures retrieval and answer quality |
| **pytest** | Unit and integration tests |
| **Databricks (optional)** | Can run large-scale or scheduled ingestion as a job. Not required for the core project |

---

## Project structure

```
rag-app/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml          # Postgres+pgvector and API for local dev
├── Dockerfile                  # Backend image
├── requirements.txt
│
├── data/
│   └── raw/                    # Source PDFs (gitignored)
│
├── db/
│   └── init.sql                # Enables pgvector, creates tables and indexes
│
├── ingest/
│   ├── loader.py               # PDF -> text with page numbers
│   ├── chunker.py              # Text -> overlapping chunks
│   ├── embedder.py             # Chunks -> vectors (shared with the API)
│   └── run_ingest.py           # Orchestrates the full ingestion
│
├── app/
│   ├── main.py                 # FastAPI app and routes
│   ├── config.py               # Env var loading (pydantic-settings)
│   ├── db.py                   # Connection pool and queries
│   ├── retriever.py            # Embed question + top-k search
│   ├── prompts.py              # System prompt and context template
│   ├── llm.py                  # Claude API client wrapper
│   └── schemas.py              # Pydantic models
│
├── eval/
│   ├── test_set.json           # 30-50 questions with expected answers/sources
│   ├── eval_retrieval.py       # Hit rate / MRR of retrieved chunks
│   └── eval_answers.py         # Faithfulness and relevance (Ragas or LLM-judge)
│
├── tests/
│   ├── test_chunker.py
│   └── test_api.py
│
├── frontend/                   # React (Vite)
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ChatBox.jsx
│   │   │   └── SourceList.jsx
│   │   └── api.js              # Calls the backend
│   └── netlify.toml
│
└── .github/
    └── workflows/
        ├── ci.yml              # Lint + tests on every push/PR
        └── deploy.yml          # Build image, push to ECR, deploy on main
```

---

## Database schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id          SERIAL PRIMARY KEY,
    filename    TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,          -- detect changed files on re-ingest
    ingested_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chunks (
    id          SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    page        INT,
    content     TEXT NOT NULL,
    embedding   VECTOR(384) NOT NULL     -- must match the embedding model
);

-- Approximate nearest neighbour index using cosine distance
CREATE INDEX chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE query_logs (
    id          SERIAL PRIMARY KEY,
    question    TEXT,
    answer      TEXT,
    chunk_ids   INT[],
    latency_ms  INT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

Retrieval query:

```sql
SELECT c.content, c.page, d.filename,
       1 - (c.embedding <=> %s) AS similarity
FROM chunks c
JOIN documents d ON d.id = c.document_id
ORDER BY c.embedding <=> %s
LIMIT %s;
```

---

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check for App Runner |
| `POST` | `/ask` | Body: `{"question": "..."}`. Returns `{"answer": "...", "sources": [{"file", "page", "snippet"}]}` |
| `POST` | `/ingest` | Triggers ingestion of new or changed documents (protect with an API key) |

---

## Local setup

### Prerequisites
- Python 3.11+, Node 18+, Docker Desktop, Git
- An Anthropic API key

### Steps

```bash
# 1. Clone and configure
git clone https://github.com/<you>/rag-app.git
cd rag-app
cp .env.example .env            # then fill in your keys

# 2. Start Postgres with pgvector
docker compose up -d db

# 3. Install Python deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Ingest documents
cp your_files/*.pdf data/raw/
python -m ingest.run_ingest

# 5. Run the API
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 6. Run the frontend
cd frontend && npm install && npm run dev
```

### `.env.example`

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
ANTHROPIC_API_KEY=your-key-here
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
TOP_K=5
CHUNK_SIZE=500
CHUNK_OVERLAP=50
INGEST_API_KEY=change-me
ALLOWED_ORIGINS=http://localhost:5173
```

### Notes for an 8GB machine
- Use a hosted LLM; do not run a local LLM for this project.
- The embedding model (~130MB) runs fine on CPU.
- Run only the `db` container plus the API while developing, and close other heavy apps.

---

## Evaluation

Create `eval/test_set.json` with 30-50 entries:

```json
[
  {
    "question": "What is the refund window?",
    "expected_answer": "30 days from purchase",
    "expected_source": {"file": "policy.pdf", "page": 4}
  }
]
```

| Metric | What it tells you | How |
|---|---|---|
| **Hit rate @k** | Is the right chunk in the top-k? | `eval_retrieval.py` compares retrieved sources to expected ones |
| **MRR** | How high does the right chunk rank? | Same script |
| **Faithfulness** | Is the answer supported by retrieved context? | Ragas or LLM-as-judge |
| **Answer relevance** | Does the answer address the question? | Ragas or LLM-as-judge |

Tune these using the eval set: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, and the system prompt. Re-run the eval after every change and record the scores.

---

## CI/CD

**`ci.yml`** (every push and pull request)
1. Set up Python, install dependencies
2. Lint (`ruff`) and run `pytest`
3. Optionally run retrieval eval against a small fixture database

**`deploy.yml`** (on push to `main`)
1. Authenticate to AWS (use GitHub OIDC rather than long-lived keys)
2. Build the Docker image and push to ECR
3. App Runner auto-deploys the new image

Store `ANTHROPIC_API_KEY`, `DATABASE_URL`, and AWS role details as GitHub/AWS secrets. Never commit them.

---

## Deployment

### 1. Database (Neon or RDS)
- **Neon (easiest, free tier):** create a project, enable the `vector` extension, run `db/init.sql`, copy the connection string.
- **RDS:** create a Postgres instance, run `CREATE EXTENSION vector;`, run `db/init.sql`. Costs more and needs networking setup.

### 2. Backend (AWS App Runner)
1. Create an ECR repository and push the image.
2. Create an App Runner service from that image, port `8000`.
3. Add environment variables, with secrets from Secrets Manager.
4. Set the health check path to `/health`.
5. Set `ALLOWED_ORIGINS` to your Netlify URL.
6. Run ingestion once against the production database.

### 3. Frontend (Netlify)
1. Connect the GitHub repo, base directory `frontend`.
2. Build command `npm run build`, publish directory `dist`.
3. Set `VITE_API_URL` to the App Runner URL.

### Cost safety
- Set an AWS billing alarm before deploying.
- Set a monthly spend limit on your LLM API account.
- Add basic rate limiting on `/ask`.

---

## Where things run

| Component | Local dev | Production |
|---|---|---|
| LLM (Claude) | Anthropic API | Anthropic API |
| Embedding model | CPU on your laptop | Inside the backend container |
| Vector DB | Docker Postgres | Neon or AWS RDS |
| Raw PDFs | `data/raw/` | S3 (optional) |
| Backend | `uvicorn` / Docker | AWS App Runner |
| Frontend | Vite dev server | Netlify |
| Secrets | `.env` | AWS Secrets Manager / GitHub Secrets |

---

## Build roadmap

- [ ] **1. Ingestion script:** PDFs → chunks → local embeddings → pgvector (Docker Postgres)
- [ ] **2. Query script:** top-k retrieval → Claude API → answer with sources
- [ ] **3. FastAPI + Docker:** `/ask`, `/ingest`, `/health`; Dockerfile and compose
- [ ] **4. React UI:** chat input, answer display, expandable source citations
- [ ] **5. GitHub + Actions:** push the repo, add CI workflow
- [ ] **6. Evaluation:** build the test set, measure retrieval and answer quality, tune
- [ ] **7. Deploy:** Neon/RDS → App Runner → Netlify, then add the deploy workflow

---

## Future improvements

- Hybrid search (vector + Postgres full-text search) and a reranker
- Incremental re-ingestion using `content_hash`
- Streaming responses (Server-Sent Events)
- Conversation memory with query rewriting
- Per-user document access control
- Tracing with Langfuse, caching with Redis
- Scheduled large-scale ingestion with Databricks jobs

---

## License

MIT
