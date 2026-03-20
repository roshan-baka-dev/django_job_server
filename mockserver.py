from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import csv
import itertools

class MondayUploadMockHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request_json = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            request_json = {}

        # 1. Extract payload and state
        payload = request_json.get('payload', {})
        file_path = payload.get('data', {}).get('file_path', 'sample_test_data.csv')
        board_id = payload.get('board_id', 'Unknown Board')
        
        polling_state = request_json.get('polling_state', {})
        current_row = polling_state.get('last_row_index', 0)
        
        BATCH_SIZE = 500  # Process 500 rows at a time
        
        print(f"\n--- MONDAY.COM UPLOAD JOB ---")
        print(f"Target Board: {board_id}")
        
        # 2. Read the specific chunk from the CSV
        rows_processed = 0
        try:
            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                # Skip the header and the rows we already processed
                start_index = current_row + 1 if current_row == 0 else current_row
                
                # Grab exactly the next BATCH_SIZE rows
                batch = list(itertools.islice(reader, start_index, start_index + BATCH_SIZE))
                rows_processed = len(batch)
                
                if rows_processed > 0:
                    print(f"Uploading Rows {start_index} to {start_index + rows_processed - 1}...")
                    # In reality, this is where your Node app calls the Monday.com GraphQL API
                    print(f"Sample data being uploaded: {batch[0]}") 
                
        except FileNotFoundError:
            print(f"ERROR: Could not find file {file_path}")
            rows_processed = 0

        # 3. Calculate new state and completion
        new_row_index = current_row + rows_processed
        is_done = rows_processed == 0 or rows_processed < BATCH_SIZE

        print(f"Status: {'FINISHED' if is_done else 'POLLING'}")
        print("-----------------------------\n")

        # 4. Respond to Django
        response_dict = {
            "status": "success",
            "polling_state": {"last_row_index": new_row_index},
            "done": is_done
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_dict).encode('utf-8'))

print("Starting Mock Monday.com Uploader on port 3000...")
httpd = HTTPServer(('127.0.0.1', 3000), MondayUploadMockHandler)
httpd.serve_forever()