from http.server import BaseHTTPRequestHandler
import json
import os

# Shared in-memory or storage log path
LOG_FILE = "/tmp/run.jsonl"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                self.wfile.write(f.read().encode('utf-8'))
        else:
            # Default fallback initial log object
            sample_log = json.dumps({"status": "initialized", "agent": "data-analyst-bot"}) + "\n"
            self.wfile.write(sample_log.encode('utf-8'))
