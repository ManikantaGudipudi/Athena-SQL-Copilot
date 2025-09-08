import json
from .agent import (
    clean_llm_output,
    auto_quote_numeric_table_names,
    run_sql_via_api,
    schema_string,
    ask_bedrock,
)
from .glue_catalog import get_tables_and_columns
from .prompts import SYSTEM, FEWSHOTS
from .config import settings

def _build_prompt(schema_info: str, question: str) -> str:
    return (
        SYSTEM + "\n\n"
        "Here are some examples:\n"
        f"{FEWSHOTS}\n\n"
        f"Schema:\n{schema_info}\n\n"
        f"Q: {question}\n"
        "SQL:"
    )

def handler(event, context):
    try:
        # Parse JSON body from API Gateway
        if "body" in event and isinstance(event["body"], str):
            body = json.loads(event["body"])
        elif isinstance(event, dict):
            body = event
        else:
            body = {}

        question = body.get("question")
        database = body.get("db", settings.glue_database)

        if not question:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'question' in request body."})
            }

        # Discover schema
        tables = get_tables_and_columns(database)
        if not tables:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"No tables found in Glue database '{database}'."})
            }
        table_names = [t["table"] for t in tables]
        schema_info = schema_string(tables)

        # Ask Bedrock → SQL
        prompt = _build_prompt(schema_info, question)
        raw_reply = ask_bedrock(prompt)
        sql = clean_llm_output(raw_reply)
        sql = auto_quote_numeric_table_names(sql, table_names)

        # Run SQL via Query API
        result = run_sql_via_api(sql, database)

        response = {"sql": sql, "result": result}

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
