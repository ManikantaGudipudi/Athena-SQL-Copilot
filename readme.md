Perfect 👍 let’s lock this down into a **clean “Getting Started” guide** for your repo. If someone clones your fork fresh, these are the exact steps they’ll follow to get Chunks 1–4 running.

---

# 🦾 Athena SQL Copilot — Setup & Run Guide

This project is split into 4 chunks:

1. **Chunk 1** — setup/seed.py → upload NYC Taxi dataset to S3 + create Glue DB/tables
2. **Chunk 2** — query\_api → FastAPI service that exposes `/health`, `/tables`, `/sql`
3. **Chunk 3** — agent\_cli → CLI agent that converts natural language → SQL (via LLM) → executes via Chunk 2
4. **Chunk 4** — ui → Streamlit app to interact with Athena using SQL or questions

---

## 0. Prerequisites

* **AWS CLI installed** & configured with an IAM user that has S3/Glue/Athena rights
* **Python 3.10+** (recommended 3.11 or 3.12)
* **Ollama** installed (for local LLM, e.g. DeepSeek-R1 7B)

  * Install via Homebrew: `brew install ollama`
  * Start server: `ollama serve`
  * Pull a model: `ollama pull deepseek-r1:7b`

---

## 1. Clone repo & create virtual environment

```bash
git clone https://github.com/<your-username>/Athena-SQL-Copilot.git
cd Athena-SQL-Copilot

# create base venv for Chunk 1 setup
python -m venv .venv
source .venv/bin/activate
pip install boto3 python-dotenv requests
```

---

## 2. Configure environment

Copy the template and edit with your values:

```bash
cp .env.example .env
nano .env
```

Typical `.env` (example):

```
AWS_REGION=us-east-1
AWS_PROFILE=copilot-dev
S3_BUCKET=athena-copilot007
S3_PREFIX=athena-copilot
GLUE_DATABASE=nyc_taxi_db
ATHENA_WORKGROUP=copilot_wg
ATHENA_OUTPUT_S3=s3://athena-copilot007/athena-copilot/results/
QUERY_API_BASE=http://127.0.0.1:8000
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=deepseek-r1:7b
```

Load the env into your shell:

```bash
export $(grep -v '^#' .env | xargs)
```

---

## 3. Chunk 1 — Seed the dataset

This uploads NYC Yellow Taxi Jan 2019 + zone lookup to S3, creates a Glue DB & crawler, and registers tables.

```bash
cd setup
python seed.py
cd ..
```

Verify in AWS Console → Glue → Databases → `nyc_taxi_db` → Tables (`2019`, `lookup`).
Also test in Athena Query Editor:

```sql
SELECT * FROM "nyc_taxi_db"."lookup" LIMIT 5;
```

---

## 4. Chunk 2 — Run Query API

```bash
cd query_api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ..
export $(grep -v '^#' .env | xargs)

uvicorn query_api.app:app --reload --port 8000
```

Test endpoints:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/tables?db=${GLUE_DATABASE}"
```

---

## 5. Chunk 3 — Run Agent CLI (Natural Language → SQL)

1. Make sure **Ollama server** is running:

   ```bash
   ollama serve
   ollama pull deepseek-r1:7b
   ```

   Ollama API will be at `http://127.0.0.1:11434/v1`.

2. Run the agent:

   ```bash
   cd agent_cli
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cd ..
   export $(grep -v '^#' .env | xargs)

   # Example: just generate SQL
   python -m agent_cli.agent --db "$GLUE_DATABASE" --question "Show 5 rows from lookup"

   # Example: generate SQL and execute via Query API
   python -m agent_cli.agent --db "$GLUE_DATABASE" \
     --question "Count trips per payment type" --execute
   ```

Expected output:

```
-- Proposed SQL --
SELECT payment_type, COUNT(*) AS trips
FROM "2019"
GROUP BY payment_type;

-- Execution result --
rows: 4 | bytes_scanned: 134445150
{'payment_type': '1', 'trips': '5486027'}
...
```

---

## 6. Chunk 4 — Run Streamlit UI

```bash
cd ui
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ..
export $(grep -v '^#' .env | xargs)

streamlit run ui/app.py
```

Go to [http://localhost:8501](http://localhost:8501)

* **Direct SQL mode** → type SQL and view results/metrics.
* **Natural Language mode** → type a question → UI spawns the agent → SQL → runs via Query API.

---

## 7. Optional improvements

* Run **CTAS → Parquet** queries (chunk 1.5) to reduce bytes scanned.
* Add charts in Streamlit (bar for payment type, line chart for daily trips).
* Deploy API (FastAPI) + UI (Streamlit) to ECS/EKS with secrets in AWS Secrets Manager.

---

✅ That’s the full lifecycle: from setup → API → agent → UI.
Would you like me to also create a **README.md** file with these instructions so you can commit it directly to your repo?

