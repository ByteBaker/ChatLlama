"""HTTP request handler for ChatLlama server."""

import json
from http.server import SimpleHTTPRequestHandler


class MultiChatHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, chat_server=None, **kwargs):
        self.chat_server = chat_server
        super().__init__(*args, **kwargs)

    def end_headers(self):
        """Add cache-busting headers for CSS and JS files"""
        if self.path.endswith(('.css', '.js')):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/chats':
            self.handle_get_chats()
            return
        elif self.path.startswith('/chat/'):
            chat_id = self.path.split('/')[-1]
            self.handle_get_chat_messages(chat_id)
            return
        elif self.path.startswith('/memory-stats/'):
            chat_id = self.path.split('/')[-1]
            self.handle_memory_stats(chat_id)
            return

        return super().do_GET()

    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/chat':
            self.handle_chat()
        elif self.path == '/chat-stream':
            self.handle_chat_stream()
        elif self.path == '/new-chat':
            self.handle_new_chat()
        else:
            self.send_error(404)

    def do_DELETE(self):
        """Handle DELETE requests"""
        if self.path.startswith('/chat/'):
            chat_id = self.path.split('/')[-1]
            self.handle_delete_chat(chat_id)
        else:
            self.send_error(404)

    def handle_new_chat(self):
        """Handle new chat creation"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            message = data.get('message', '').strip()
            if not message:
                self.send_json_response({'error': 'Empty message'}, 400)
                return

            response, memories_added, chat_id, title = self.chat_server.generate_response(
                None, message, is_first_message=True
            )

            if not chat_id:
                self.send_json_response({'error': 'Failed to create chat'}, 500)
                return

            facts_count, experiences_count, topics_count = self.chat_server.get_memory_counts(chat_id)

            self.send_json_response({
                'chat_id': chat_id,
                'title': title,
                'response': response,
                'memories_added': memories_added,
                'memory_stats': {
                    'facts': facts_count,
                    'experiences': experiences_count,
                    'topics': topics_count
                }
            })

        except json.JSONDecodeError:
            self.send_json_response({'error': 'Invalid JSON'}, 400)
        except Exception as e:
            print(f"New chat error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def handle_chat(self):
        """Handle chat messages"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            message = data.get('message', '').strip()
            chat_id = data.get('chat_id')

            if not message:
                self.send_json_response({'error': 'Empty message'}, 400)
                return

            if not chat_id:
                self.send_json_response({'error': 'No chat_id provided'}, 400)
                return

            response, memories_added, _, _ = self.chat_server.generate_response(chat_id, message)

            facts_count, experiences_count, topics_count = self.chat_server.get_memory_counts(chat_id)

            self.send_json_response({
                'response': response,
                'memories_added': memories_added,
                'memory_stats': {
                    'facts': facts_count,
                    'experiences': experiences_count,
                    'topics': topics_count
                }
            })

        except json.JSONDecodeError:
            self.send_json_response({'error': 'Invalid JSON'}, 400)
        except Exception as e:
            print(f"Chat error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def handle_chat_stream(self):
        """Handle streaming chat messages"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            message = data.get('message', '').strip()
            chat_id = data.get('chat_id')

            if not message:
                self.send_json_response({'error': 'Empty message'}, 400)
                return

            if not chat_id:
                self.send_json_response({'error': 'No chat_id provided'}, 400)
                return

            self.send_streaming_response(chat_id, message)

        except json.JSONDecodeError:
            self.send_json_response({'error': 'Invalid JSON'}, 400)
        except Exception as e:
            print(f"Streaming chat error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def send_streaming_response(self, chat_id, message):
        """Send streaming SSE response"""
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response, memories_added = self.chat_server.generate_streaming_response(chat_id, message, self.wfile)

            facts_count, experiences_count, topics_count = self.chat_server.get_memory_counts(chat_id)
            final_data = {
                'memories_added': memories_added,
                'memory_stats': {
                    'facts': facts_count,
                    'experiences': experiences_count,
                    'topics': topics_count
                }
            }

            try:
                self.wfile.write(f"data: {json.dumps(final_data)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                print("Client disconnected before final response")

        except Exception as e:
            print(f"Streaming error: {e}")
            error_data = {'error': str(e)}
            try:
                self.wfile.write(f"data: {json.dumps(error_data)}\n\n".encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def handle_get_chats(self):
        """Handle getting chat list"""
        try:
            chats = self.chat_server.get_chats()
            self.send_json_response({'chats': chats})
        except Exception as e:
            print(f"Get chats error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def handle_get_chat_messages(self, chat_id):
        """Handle getting messages for a chat"""
        try:
            messages = self.chat_server.get_chat_messages(chat_id)
            self.send_json_response({'messages': messages})
        except Exception as e:
            print(f"Get messages error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def handle_memory_stats(self, chat_id):
        """Handle memory stats requests for a specific chat"""
        try:
            facts_count, experiences_count, topics_count = self.chat_server.get_memory_counts(chat_id)

            self.send_json_response({
                'memory_stats': {
                    'facts': facts_count,
                    'experiences': experiences_count,
                    'topics': topics_count
                }
            })
        except Exception as e:
            print(f"Memory stats error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def handle_delete_chat(self, chat_id):
        """Handle chat deletion"""
        try:
            success = self.chat_server.delete_chat(chat_id)
            if success:
                self.send_json_response({'success': True})
            else:
                self.send_json_response({'error': 'Failed to delete chat'}, 500)
        except Exception as e:
            print(f"Delete chat error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        response_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.wfile.write(response_data)

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        """Override to reduce verbose logging"""
        if not any(path in self.path for path in ['/chat', '/new-chat', '/chats']):
            return
        super().log_message(format, *args)