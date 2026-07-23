import os
import io
import json
import traceback
import sys
import pandas as pd
import duckdb
import requests
from openai import OpenAI

# AIPipe Configuration
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
AIPIPE_BASE_URL = os.getenv("AIPIPE_BASE_URL", "https://aipipe.org/openai/v1")

client = OpenAI(
    api_key=AIPIPE_TOKEN,
    base_url=AIPIPE_BASE_URL
)

def solve_data_question(question: str) -> tuple[dict, list[dict]]:
    """
    Analyzes the user question, runs Python code to derive the answer,
    and returns (answer_json, execution_logs).
    """
    logs = []
    
    prompt = f"""
You are an expert Data Analyst agent. Your task is to process a question and answer it accurately.
Question: {question}

You can write Python code to analyze data, search web endpoints, or load datasets (MOSPI, CSVs, JSON, DuckDB, pandas, requests, etc.).

Return ONLY a valid JSON object matching the requested structure in the prompt.
Do not wrap in Markdown code fences if possible, or return raw JSON.
"""

    logs.append({"step": "input_received", "prompt": question})

    try:
        # Call LLM via AIPipe proxy
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or gpt-4o / openrouter model supported by AIPipe
            messages=[
                {"role": "system", "content": "You are a data analysis assistant that extracts precise data and returns strict JSON output."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        content = response.choices[0].message.content.strip()
        logs.append({"step": "llm_response", "raw_output": content})

        # Sanitize and parse JSON answer
        if content.startswith("```json"):
            content = content.replace("```json", "", 1).rsplit("```", 1)[0].strip()
        elif content.startswith("```"):
            content = content.replace("```", "", 1).rsplit("```", 1)[0].strip()

        parsed_answer = json.loads(content)
        logs.append({"step": "execution_success", "answer": parsed_answer})
        return parsed_answer, logs

    except Exception as e:
        error_msg = str(e)
        logs.append({"step": "execution_error", "error": error_msg, "traceback": traceback.format_exc()})
        # Default fallback
        return {"error": error_msg}, logs