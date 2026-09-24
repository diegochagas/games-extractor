#!/usr/bin/env python3
"""Tiny local HTTP sink used with the in-app browser: pages that block plain
downloads (Cloudflare, hotlink checks) are read inside the browser with
fetch() and the bytes are POSTed here.

    upload_server.py OUT_DIR [PORT]

POST /upload?name=<file name>   body = raw bytes   -> OUT_DIR/<file name>
POST /text?name=<file name>     body = utf-8 text  -> OUT_DIR/<file name>
GET  /list                      -> JSON list of saved files
CORS is open (the browser page has another origin).
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "uploads")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
os.makedirs(OUT, exist_ok=True)


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Name")
        self.send_header("Access-Control-Allow-Private-Network", "true")  # Chrome private-network-access preflight

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        body = json.dumps(sorted(os.listdir(OUT))).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        u = urlparse(self.path)
        name = parse_qs(u.query).get("name", ["file"])[0]
        name = os.path.basename(name).replace("..", "_") or "file"
        n = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(n)
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("saving to", OUT, "on port", PORT, flush=True)
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
