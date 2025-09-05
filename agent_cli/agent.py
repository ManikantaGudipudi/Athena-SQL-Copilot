import argparse
import json
import re
import requests
from typing import List, Dict

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from .config import settings
from .glue_catalog import get_tables_and_columns
from .prompts import SYSTEM, FEWSHOTS


# --- Helpers ---
def _quote_if_needed(name: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return name
    return f'"{name}"'

def auto_quote_numeric_table_names(sql: str, table_names: List[str]) -> str:
    patched = sql
    for t in table_names:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
            patched = re.sub(rf'(?<!")\b{re.escape(t)}\b(?!")', f'"{t}"', patched)
    return patched

def clean_llm_output(text: str) -> str:
    """Strip <think> blocks, fences, and return the first SQL statement."""
    # Remove <think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

    # Look inside fenced blocks
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            if re.search(r"\b(select|with|create|describe|show)\b", p, flags=re.IGNORECASE):
                return re.sub(r"^\s*sql", "", p.strip(), flags=re.IGNORECASE)

    # Fallback regex
    m = re.search(r"(?is)\b(select|with|create|describe|show)\b.*?;", text)
    if m:
        return m.group(0).strip()

    return text


# --- Tool: run SQL via Chunk 2 API ---
def run_sql_via_api(sql: str, database: str) -> Dict:
    if not settings.query_api_base:
        return {"error": "QUERY_API_BASE not set in .env"}
    
    url = f"{settings.query_api_base}/sql"
    try:
        r = requests.post(url, json={"query": sql, "database": database}, timeout=120)
    except Exception as e:
        return {"error": f"HTTP error: {e}"}

    if r.status_code != 200:
        return {"error": r.text}

    return r.json()


# --- Build schema string for prompt ---
def schema_string(tables: List[Dict]) -> str:
    return "\n".join(
        f'- {_quote_if_needed(t["table"])}(columns={t["columns"]}, partitions={t["partitions"]})'
        for t in tables
    )


# --- Main LangChain agent ---
def run_langchain_agent(question: str, database: str, max_retries: int = 3) -> None:
    tables = get_tables_and_columns(database)
    if not tables:
        print(f"No tables found in Glue database '{database}'.")
        return

    schema_info = schema_string(tables)

    # Build prompt
    template = (
        SYSTEM + "\n\n"
        "Here are some examples:\n"
        f"{FEWSHOTS}\n\n"
        f"Schema:\n{schema_info}\n\n"
        "Q: {question}\n"
        "SQL:"
    )
    prompt = ChatPromptTemplate.from_template(template)

    # Initialize Ollama LLM
    llm = ChatOpenAI(
        model=settings.model,  # deepseek-r1:7b
        base_url=settings.openai_base_url,  # http://127.0.0.1:11434/v1
        api_key=settings.openai_api_key,    # "ollama"
        temperature=0,
    )

    # Retry loop
    last_error = None
    for attempt in range(1, max_retries + 1):
        print(f"\n=== Attempt {attempt} ===")

        # Generate SQL
        messages = prompt.format_messages(question=question)
        raw_reply = llm.invoke(messages).content
        sql = clean_llm_output(raw_reply)
        sql = auto_quote_numeric_table_names(sql, [t["table"] for t in tables])

        print(f"[Raw LLM reply]: {raw_reply}")
        print(f"[Cleaned SQL]: {sql}")

        # Run SQL
        result = run_sql_via_api(sql, database)
        if "error" in result:
            print("\n[exec error]", result["error"])
            last_error = result["error"]
            # feed error back into loop
            question = f"{question}\nFix the SQL based on this error: {last_error}"
            continue

        # Success
        print("\n-- Execution result --")
        print("rows:", result.get("row_count"), "| bytes_scanned:", result.get("bytes_scanned"))
        for row in result.get("rows", [])[:5]:
            print(row)
        return

    print("\n❌ Could not produce a working query after", max_retries, "attempts.")
    if last_error:
        print("Last error:", last_error)


# --- Entry point ---
def main():
    ap = argparse.ArgumentParser(description="LangChain Athena Copilot")
    ap.add_argument("--db", default=settings.glue_database)
    ap.add_argument("--question", required=True)
    ap.add_argument("--max-retries", type=int, default=5)
    args = ap.parse_args()

    run_langchain_agent(args.question, args.db, max_retries=args.max_retries)


if __name__ == "__main__":
    main()
