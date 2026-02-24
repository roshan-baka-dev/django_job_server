# mock_server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        # 1. Parse the incoming JSON sent by Celery
        try:
            request_json = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            request_json = {}

        print("\n----- RECEIVED POST REQUEST -----")
        print(f"Path: {self.path}")
        print(f"Body: {post_data.decode('utf-8')}")

        # --- THE POLLING LOGIC ---
        # 2. Extract the current state (Django sends this)
        # If it's the first run, it will be {}
        polling_state = request_json.get('polling_state', {})
        if not isinstance(polling_state, dict):
            polling_state = {}
            
        current_row = polling_state.get('last_row_index', 0)
        
        # 3. Simulate processing 100 rows
        new_row = current_row + 100
        
        # 4. Stop the polling loop after 300 rows
        is_done = new_row >= 300

        print(f"--> Simulated processing: Row {current_row} to {new_row}")
        print(f"--> Is Job Done? {is_done}")
        print("---------------------------------\n")

        # 5. Create the dynamic response
        response_dict = {
            "status": "success",
            "message": "Mock Node Server processed batch",
            "polling_state": {
                "last_row_index": new_row
            },
            "done": is_done
        }

        # Send back the 200 OK response with the dynamic JSON
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_dict).encode('utf-8'))

print("Starting Mock Node Server on port 3000...")
httpd = HTTPServer(('127.0.0.1', 3000), MockHandler)
httpd.serve_forever()