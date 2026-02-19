# mock_server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        print("\n----- RECEIVED POST REQUEST -----")
        print(f"Path: {self.path}")
        print(f"Body: {post_data.decode('utf-8')}")
        print("---------------------------------\n")

        # Send back a 200 OK response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "success", "message": "Mock Node Server received payload"}')

print("Starting Mock Node Server on port 3000...")
httpd = HTTPServer(('127.0.0.1', 3000), MockHandler)
httpd.serve_forever()