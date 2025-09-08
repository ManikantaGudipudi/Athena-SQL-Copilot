import os
import requests
import streamlit as st
from dotenv import load_dotenv

# load .env from repo root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

QUERY_API_BASE = os.getenv("QUERY_API_BASE", "http://127.0.0.1:8000")
AGENT_ENTRYPOINT = "agent_cli.agent"

st.set_page_config(page_title="Athena Copilot", layout="wide")

st.title("🦾 Athena SQL Copilot (Chunk 4 UI)")

st.sidebar.header("Settings")
db = st.sidebar.text_input("Glue Database", os.getenv("GLUE_DATABASE", "nyc_taxi_db"))
execute_mode = st.sidebar.radio("Run Mode", ["Direct SQL", "Natural Language → SQL"], index=0)

st.sidebar.markdown("---")
st.sidebar.write(f"🔗 Query API: {QUERY_API_BASE}")

# --- helpers ---
def run_sql(sql: str, database: str):
    url = f"{QUERY_API_BASE}/sql"
    try:
        r = requests.post(url, json={"query": sql, "database": database}, timeout=120)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error running SQL: {e}")
        return None

def list_tables(database: str):
    url = f"{QUERY_API_BASE}/tables?db={database}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json().get("tables", [])
    except Exception as e:
        st.error(f"Error listing tables: {e}")
        return []

# --- UI ---
if execute_mode == "Direct SQL":
    st.subheader("✍️ Enter SQL")
    tables = list_tables(db)
    if tables:
        st.caption(f"Tables in {db}: {tables}")

    sql = st.text_area("SQL", height=150, placeholder="SELECT * FROM lookup LIMIT 5;")
    if st.button("Run SQL"):
        if sql.strip():
            result = run_sql(sql, db)
            if result:
                st.success(f"✅ {result['row_count']} rows | {result['bytes_scanned']} bytes | {result['engine_ms']} ms")
                st.dataframe(result["rows"])
else:
    st.subheader("💬 Ask a question")
    question = st.text_input("Natural language question", placeholder="e.g., Count trips per payment type")
    if st.button("Ask"):
        if question.strip():
            with st.spinner("Generating SQL via agent..."):
                agent_api_url = os.getenv("AGENT_API_URL")  # set this in EB env
                try:
                    r = requests.post(agent_api_url, json={"question": question}, timeout=120)
                    r.raise_for_status()
                    result = r.json()
                    st.json(result)   # show SQL + result JSON
                except Exception as e:
                    st.error(f"Agent failed: {e}")