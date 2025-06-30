# Toolkit-RAG

A generic, API-first RAG (Retrieval-Augmented Generation) system designed for integration with any application, CLI tool, or AI assistant.

## Overview

Toolkit-RAG provides document indexing, vector search, and semantic retrieval as a reusable service. It features:

- **Generic Architecture**: Framework-agnostic design for universal adoption
- **Multiple Backends**: PostgreSQL/pgvector, MongoDB, local embeddings
- **Flexible Deployment**: Docker, local, and cloud deployment options
- **Plugin System**: Extensible architecture for custom processors
- **REST API**: Standard HTTP API for any client integration

## Quick Start

```bash
# Clone the repository
git clone https://github.com/ersantana361/toolkit-rag.git
cd toolkit-rag

# Start with Docker (recommended)
docker compose up -d

# Or install locally
pip install -r requirements.txt
python -m rag_server

# Index documents
curl -X POST "http://localhost:8000/documents" \
  -F "file=@document.pdf" \
  -F "project_id=my-project"

# Search documents
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "search terms", "project_id": "my-project"}'
```

## Architecture

```
toolkit-rag/
├── rag_server/          # FastAPI server
├── rag_client/          # Python client library
├── cli.py               # Command-line interface
├── docker/              # Deployment configurations
└── docs/                # Documentation
```

## Integration

Toolkit-RAG is designed to be integrated as a git submodule or standalone service:

```bash
# As a submodule
git submodule add https://github.com/ersantana361/toolkit-rag.git rag

# Custom bridge example
from rag_client import RAGClient
client = RAGClient(api_url="http://localhost:8000")
results = await client.search(query="search terms", project_id="my-project")
```

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [API Reference](docs/API_REFERENCE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Integration Examples](docs/INTEGRATIONS.md)

## License

MIT License - see [LICENSE](LICENSE) file for details.