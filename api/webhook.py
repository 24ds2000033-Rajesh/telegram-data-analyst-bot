from http.server import BaseHTTPRequestHandler
import json
import os
import requests
import re
import duckdb
import pandas as pd

# Load environment configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AIPIPE_TOKEN = os.environ.get("AIPIPE_TOKEN")
HOST_URL = os.environ.get("VERCEL_URL")  # Auto-populated by Vercel (e.g., app-name.vercel.app)

if HOST_URL and not HOST_URL.startswith("http"):
    HOST_URL = f"https://{HOST_URL}"

LOG_FILE = "/tmp/run.jsonl"

def append_log(data_dict):
    """Appends a log line entry to /tmp/run.jsonl"""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(data_dict) + "\n")
    except Exception as e:
        print(f"Log Error: {e}")

def query_aipipe_llm(prompt: str) -> str:
    """Calls AI Pipe endpoint to process prompt with an LLM."""
    url = "https://aipipe.org/openrouter/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are an expert Data Analyst Agent. "
        "Your job is to read the user query, solve data questions (including SQL/MOSPI/CSV parsing), "
        "and output ONLY a valid JSON structure that answers the user prompt as requested."
    )
    
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0
    }
    
    res = requests.post(url, headers=headers, json=payload, timeout=45)
    res_json = res.json()
    
    append_log({"type": "llm_query", "prompt": prompt, "response": res_json})
    
    return res_json['choices'][0]['message']['content']

def parse_and_process_task(user_text: str):
    """Processes user text and extracts the requested answer object."""
    # 1. Ask LLM to extract data fetching requirement or execute directly
    llm_raw_response = query_aipipe_llm(
        f"Analyze this request and answer the question in the requested JSON structure.\n\nMessage: {user_text}\n\n"
        "Return ONLY the raw JSON object corresponding to the answer payload requested."
    )
    
    # 2. Extract valid JSON from LLM output
    match = re.search(r'\{.*\}', llm_raw_response, re.DOTALL)
    if match:
        answer_json = json.loads(match.group(0))
    else:
        answer_json = {"result": llm_raw_response}
        
    return answer_json

def send_telegram_reply(chat_id, answer_obj):
    """Sends the formatted JSON reply back to the Telegram chat."""
    log_url = f"{HOST_URL}/run.jsonl"
    
    # Construct required exact output schema
    final_payload = {
        "answer": answer_obj,
        "log_url": log_url
    }
    
    reply_text = json.dumps(final_payload)
    
    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(telegram_api_url, json={
        "chat_id": chat_id,
        "text": reply_text
    })

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            update = json.loads(body.decode('utf-8'))
            append_log({"type": "telegram_update", "payload": update})
            
            # Extract message details
            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                user_text = update["message"]["text"]
                
                # Solve task
                answer_data = parse_and_process_task(user_text)
                
                # Send exact requested response format
                send_telegram_reply(chat_id, answer_data)
                
        except Exception as e:
            append_log({"type": "error", "error_message": str(e)})

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
