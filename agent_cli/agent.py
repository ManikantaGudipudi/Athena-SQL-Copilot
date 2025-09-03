import argparse
import json
import re
from typing import List, Dict
import requests

from .config import settings
from .glue_catalog import get_tables_and_columns
from .prompts import SYSTEM, FEWSHOTS

import re

def _strip_think(text: str) -> str:
    """Remove DeepSeek-style <think>...</think> blocks (and similar)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)

def _extract_sql_only(text: str) -> str:
    """
    Return exactly ONE SQL statement.
    Strategy:
      1) Strip <think> blocks.
      2) If there are ``` fences, pick the first fence that looks like SQL.
      3) Otherwise, regex-grab the first statement starting with SELECT/WITH/CREATE/DESCRIBE/SHOW up to the first semicolon.
    """
    cleaned = _strip_think(text).strip()

    # 2) Handle fenced code blocks first
    if "```" in cleaned:
        parts = cleaned.split("```")
        for p in parts:
            # remove optional language tag like "sql"
            body = re.sub(r"^\s*sql\s*", "", p.strip(), flags=re.IGNORECASE)
            if re.search(r"\b(select|with|create|describe|show)\b", body, flags=re.IGNORECASE):
                # keep only up to the first semicolon, if present
                m = re.search(r"(?is)\b(select|with|create|describe|show)\b.*?;", body)
                return (m.group(0) if m else body).strip()

    # 3) No fences: grab first SQL-looking statement up to semicolon
    m = re.search(r"(?is)\b(select|with|create|describe|show)\b.*?;", cleaned)
    if m:
        return m.group(0).strip()

    # Fallback: return whole thing (last resort)
    return cleaned

def _quote_if_needed(name: str) -> str:
    """Quote Athena identifiers that are not simple [A-Za-z_][A-Za-z0-9_]* or that start with a digit."""
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return name
    return f'"{name}"'

def auto_quote_numeric_table_names(sql: str, table_names: List[str]) -> str:
    """If the schema contains numeric-leading tables (e.g., 2019), ensure they're quoted in SQL."""
    patched = sql
    for t in table_names:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
            # replace occurrences of the bare word t with "t"
            # word boundary approach keeps simple; also handle FROM/JOIN
            patched = re.sub(rf'(?<!")\b{re.escape(t)}\b(?!")', f'"{t}"', patched)
    return patched

def build_messages(tables: List[Dict], question: str) -> list:
    tbl_str = "\n".join(
        f'- {_quote_if_needed(t["table"])}(columns={t["columns"]}, partitions={t["partitions"]})'
        for t in tables
    )
    user = f"Tables:\n{tbl_str}\n\nQ: {question}\nSQL:"
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": FEWSHOTS},
        {"role": "user", "content": user},
    ]

def ask_llm(messages: list) -> str:
    url = f"{settings.openai_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": settings.model, "messages": messages, "temperature": 0.1}
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"].strip()

    # Use our robust extractor to remove <think> and keep only SQL
    return _extract_sql_only(content)

def maybe_execute(sql: str, database: str) -> None:
    if not settings.query_api_base:
        print("\n[exec skipped] Set QUERY_API_BASE in .env to run SQL via Chunk 2.")
        return
    url = f"{settings.query_api_base}/sql"
    r = requests.post(url, json={"query": sql, "database": database}, timeout=120)
    if r.status_code != 200:
        print("\n[exec error]", r.status_code, r.text)
        return
    data = r.json()
    print("\n-- Execution result --")
    print("rows:", data.get("row_count"), "| bytes_scanned:", data.get("bytes_scanned"))
    sample = data.get("rows", [])[:5]
    for row in sample:
        print(row)

def main():
    ap = argparse.ArgumentParser(description="Question -> Athena SQL (and optional execute)")
    ap.add_argument("--db", default=settings.glue_database)
    ap.add_argument("--question", required=True)
    ap.add_argument("--execute", action="store_true", help="Run the SQL via Chunk 2 API")
    args = ap.parse_args()

    # 1) discover schema
    tables = get_tables_and_columns(args.db)
    table_names = [t["table"] for t in tables]
    if not tables:
        print(f"No tables found in Glue database '{args.db}'.")
        return

    # 2) prompt the LLM
    msgs = build_messages(tables, args.question)
    try:
        sql = ask_llm(msgs)
    except requests.RequestException as e:
        print("[LLM error] Could not reach the OpenAI-compatible server:", e)
        return

    # 3) patch numeric-leading table names (e.g., 2019 -> "2019")
    sql_patched = auto_quote_numeric_table_names(sql, table_names)

    print("\n-- Proposed SQL --\n" + sql_patched)

    # 4) optional execute via Query API
    if args.execute:
        maybe_execute(sql_patched, args.db)

if __name__ == "__main__":
    main()
