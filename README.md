# ChatLlama

A multi-chat HTTP server powered by Llama 3 8B with persistent memory and web interface.

## Features

- Web-based chat interface with markdown rendering
- Multiple concurrent chat sessions
- Persistent SQLite database for chat history
- Memory system tracking facts, experiences, and topics
- Server-sent events for real-time streaming responses
- Docker-first deployment with embedded model

## Quick Start (Docker)

### Prerequisites

- Docker and Docker Compose
- 8GB+ available RAM
- 10GB+ free disk space

### Running with Docker

1. Clone the repository:
```bash
git clone https://github.com/ByteBaker/ChatLlama
cd ChatLlama
```

2. Start the application:
```bash
docker-compose up --build
```

The model (~5GB) will be automatically downloaded during the first build. This may take a few minutes depending on your connection.

3. Access the application:
```
http://localhost:8000
```

### Configuration

Set custom port via environment variable:
```bash
PORT=3000 docker-compose up --build
```

## Manual Installation

### Prerequisites

- Python 3.11+
- 8GB+ available RAM

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Download the model:
```bash
python src/utils/download_model.py
```

3. Run the server:
```bash
python src/main.py
```

## File Structure

```
ChatLlama/
├── src/
│   ├── main.py              # Server entry point
│   ├── config.py            # Model configuration
│   ├── chat_server.py       # Chat logic and memory system
│   ├── http_handler.py      # HTTP request handling
│   ├── index.html           # Web interface
│   ├── script.js            # Frontend JavaScript
│   ├── styles.css           # Interface styling
│   └── utils/
│       └── download_model.py # Model download utility
├── data/                    # SQLite database (created at runtime)
├── docker-compose.yml       # Docker configuration
├── Dockerfile              # Container build instructions
└── requirements.txt        # Python dependencies
```

## Memory System

The server automatically categorizes conversation content into:

- **Facts**: Concrete information and data points
- **Experiences**: Personal stories and events
- **Topics**: Subject areas and themes discussed

Memory statistics are included in all chat responses and can be queried independently.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.


