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
