import os
import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
import telegram
from agent import solve_data_question

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HOST_DOMAIN = os.getenv("HOST_DOMAIN")  # e.g., https://your-app.onrender.com

app = FastAPI()
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

LOG_FILE = "run.jsonl"

def append_to_jsonl(log_entries: list[dict]):
    """Appends execution steps as JSON lines into run.jsonl"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for entry in log_entries:
            f.write(json.dumps(entry) + "\n")

@app.on_event("startup")
async def startup_event():
    # Set Telegram webhook automatically upon deployment startup
    if bot and HOST_DOMAIN:
        webhook_url = f"{HOST_DOMAIN}/webhook"
        await bot.set_webhook(url=webhook_url)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = telegram.Update.de_json(data, bot)

    if update and update.message and update.message.text:
        chat_id = update.message.chat_id
        question_text = update.message.text.strip()

        # Execute Agent Logic
        answer_data, execution_logs = solve_data_question(question_text)

        # Log trace to JSONL
        append_to_jsonl(execution_logs)

        # Construct exact required output payload
        log_url = f"{HOST_DOMAIN}/run.jsonl"
        final_payload = {
            "answer": answer_data,
            "log_url": log_url
        }

        # Telegram reply must strictly be ONE JSON string object
        await bot.send_message(
            chat_id=chat_id,
            text=json.dumps(final_payload, ensure_ascii=False)
        )

    return Response(status_code=200)

@app.get("/run.jsonl")
async def get_logs():
    """Serves the JSONL run logs for grading verification."""
    if os.path.exists(LOG_FILE):
        return FileResponse(LOG_FILE, media_type="application/x-ndjson")
    return Response(content="", media_type="application/x-ndjson")

@app.get("/")
async def root():
    return {"status": "bot is running"}