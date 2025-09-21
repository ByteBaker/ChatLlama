"""Main entry point for ChatLlama server."""

import os
import sys
import signal
import threading
from http.server import ThreadingHTTPServer

from config import LLAMA3_MODEL
from chat_server import Llama3MultiChatServer
from http_handler import MultiChatHTTPRequestHandler


def main():
    """Main server function"""
    print("🚀 Llama 3 8B Multi-Chat HTTP Server")
    print("=" * 40)

    # Check if model exists
    model_path = LLAMA3_MODEL["path"]
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        print("💡 For non-Docker usage, run: python src/utils/download_model.py")
        sys.exit(1)

    # Initialize chat server
    try:
        chat_server = Llama3MultiChatServer()
        print("✅ Multi-chat server initialized")
    except Exception as e:
        print(f"❌ Failed to initialize chat server: {e}")
        sys.exit(1)

    # Create HTTP server
    port = int(os.environ.get('PORT', 8000))
    server_address = ('', port)

    def handler(*args, **kwargs):
        MultiChatHTTPRequestHandler(*args, chat_server=chat_server, **kwargs)

    httpd = ThreadingHTTPServer(server_address, handler)

    # Set up graceful shutdown
    shutdown_event = threading.Event()

    def signal_handler(signum, frame):
        signal_name = signal.Signals(signum).name
        print(f"\n📡 Received {signal_name}, initiating graceful shutdown...")

        # Signal shutdown to all components
        shutdown_event.set()

        # Shutdown HTTP server
        print("🛑 Stopping HTTP server...")
        httpd.shutdown()
        httpd.server_close()

        # Gracefully shutdown chat server
        chat_server.shutdown()

        print("✅ Server stopped gracefully")
        sys.exit(0)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C

    print(f"🌐 Server running at http://localhost:{port}")
    print("=" * 40)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        # This shouldn't be reached due to signal handler, but just in case
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()