"""
Scaffolds the RAG project skeleton in the current directory.
Usage:  python scaffold.py
Safe to re-run: existing files are never overwritten.
"""
from pathlib import Path

FILES = {}

FILES[".gitignore"] = r"""
.env
.venv/
__pycache__/
*.pyc
data/raw/*
!data/raw/.gitkeep
node_modules/
dist/
.DS_Store
"""

FILES[".env.example"] = r"""
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
ANTHROPIC_API_KEY=your-key-here
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIM=384
TOP_K=5
CHUNK_SIZE=500
CHUNK_OVERLAP=50
INGEST_API_KEY=change-me
ALLOWED_ORIGINS=http://localhost:5173
"""

FILES["requirements.txt"] = r"""
# Install CPU-only torch FIRST (see README/setup steps), then this file.
sentence-transformers
psycopg[binary]
pgvector
pypdf
pydantic-settings
python-dotenv
fastapi
uvicorn[standard]
anthropic
pytest
ruff
"""

FILES["docker-compose.yml"] = r"""
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: rag-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: rag
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d rag"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
"""

FILES["db/init.sql"] = r"""
-- Runs automatically ONLY the first time the db volume is created.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id           SERIAL PRIMARY KEY,
    filename     TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    ingested_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id          SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    page        INT,
    content     TEXT NOT NULL,
    embedding   VECTOR(384) NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS query_logs (
    id         SERIAL PRIMARY KEY,
    question   TEXT,
    answer     TEXT,
    chunk_ids  INT[],
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT now()
);
"""

FILES["app/config.py"] = r"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    anthropic_api_key: str = ""
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50
    ingest_api_key: str = "change-me"
    allowed_origins: str = "http://localhost:5173"


settings = Settings()
"""

FILES["app/db.py"] = r"""
import psycopg
from pgvector.psycopg import register_vector

from app.config import settings


def get_conn() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url)
    register_vector(conn)
    return conn
"""

FILES["scripts/check_setup.py"] = r"""
# Verifies the whole local setup. Run from project root:  python -m scripts.check_setup
import sys

from app.config import settings


def ok(msg):
    print(f"[OK]   {msg}")


def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)


# 1. Database connection + pgvector
try:
    import psycopg

    with psycopg.connect(settings.database_url) as conn:
        ok("Connected to Postgres")
        ext = conn.execute(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        ok("pgvector extension enabled") if ext else fail("pgvector missing")

        tables = {
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ).fetchall()
        }
        needed = {"documents", "chunks", "query_logs"}
        if needed <= tables:
            ok(f"Tables exist: {sorted(needed)}")
        else:
            fail(f"Missing tables: {sorted(needed - tables)}")
except Exception as e:
    fail(f"Database problem: {e}")

# 2. Embedding model
try:
    from sentence_transformers import SentenceTransformer

    print("       Loading embedding model (first run downloads ~130MB)...")
    model = SentenceTransformer(settings.embedding_model)
    vec = model.encode("hello world")
    if len(vec) == settings.embedding_dim:
        ok(f"Embedding model works, dimension = {len(vec)}")
    else:
        fail(f"Dimension mismatch: model={len(vec)}, expected={settings.embedding_dim}")
except Exception as e:
    fail(f"Embedding problem: {e}")

# 3. API key present (no paid call is made)
if settings.anthropic_api_key and settings.anthropic_api_key != "your-key-here":
    ok("ANTHROPIC_API_KEY is set")
else:
    print("[WARN] ANTHROPIC_API_KEY not set yet (needed from step 2 onward)")

print("\nSetup looks good.")
"""

FILES["data/raw/.gitkeep"] = ""
FILES["app/__init__.py"] = ""
FILES["ingest/__init__.py"] = ""
FILES["scripts/__init__.py"] = ""
FILES["eval/.gitkeep"] = ""
FILES["tests/.gitkeep"] = ""


def main():
    for rel, content in FILES.items():
        path = Path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            print(f"skip    {rel} (already exists)")
            continue
        path.write_text(content.lstrip("\n"), encoding="utf-8")
        print(f"created {rel}")
    print("\nDone. Next: copy .env.example to .env, then follow the setup steps.")


if __name__ == "__main__":
    main()
