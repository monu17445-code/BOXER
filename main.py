import json
import time
import requests
import http.server
import socketserver
import threading
import pytz
from datetime import datetime
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, health_response, **kwargs):
        self.health_response = health_response
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(self.health_response.encode())

def execute_server(port, health_response):
    with socketserver.TCPServer(("", port), lambda *args, **kwargs: HealthHandler(*args, health_response=health_response, **kwargs)) as httpd:
        httpd.serve_forever()

def send_messages_forever(config):
    # Prepare headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; Samsung Galaxy S9 Build/OPR6.170623.017; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.125 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'referer': 'www.google.com'
    }
    requests.packages.urllib3.disable_warnings()
    tz = pytz.timezone('Asia/Kolkata')

    # Load messages
    messages = []
    try:
        with open(config['messages_file'], 'r', encoding='utf-8') as f:
            messages = [line.strip() for line in f if line.strip()]
        if not messages:
            logger.error("No messages found in file")
            return
    except Exception as e:
        logger.error(f"Failed to load messages: {e}")
        return

    # Infinite loop
    while True:
        for message in messages:
            for convo_id in config['conversation_ids']:
                for token in config['tokens']:
                    try:
                        payload = {
                            'access_token': token,
                            'message': f"{config['target_name']} {message}"
                        }
                        url = f"https://graph.facebook.com/v15.0/t_{convo_id}/"
                        response = requests.post(url, json=payload, headers=headers)
                        current_time = datetime.now(tz).strftime("%I:%M %p")
                        if response.ok:
                            logger.info(f"Sent message to {convo_id} at {current_time}")
                        else:
                            logger.error(f"API error for {convo_id}: {response.status_code} at {current_time}")
                    except Exception as e:
                        logger.error(f"Failed to send message to {convo_id}: {e} at {datetime.now(tz).strftime('%I:%M %p')}")
                    time.sleep(config['delay_seconds'])  # Delay between each send

def main():
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config.json: {e}")
        return

    # Start HTTP server
    server_thread = threading.Thread(
        target=execute_server,
        args=(config['server_port'], config['health_response']),
        daemon=True
    )
    server_thread.start()

    # Start message loop
    try:
        send_messages_forever(config)
    except KeyboardInterrupt:
        logger.info("Stopping by user request")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    main()
