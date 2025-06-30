# Toolkit-RAG

A generic, API-first RAG (Retrieval-Augmented Generation) system designed for integration with any application, CLI tool, or AI assistant. Built as a client/wrapper around the proven [rag_api](https://github.com/danny-avila/rag_api) implementation.

## Overview

Toolkit-RAG provides document indexing, vector search, and semantic retrieval as a reusable service. It features:

- **Zero Code Duplication**: Uses original [rag_api](https://github.com/danny-avila/rag_api) as submodule dependency
- **Generic Architecture**: Framework-agnostic design for universal adoption
- **Multiple Backends**: PostgreSQL/pgvector, MongoDB, local embeddings via rag_api
- **Flexible Deployment**: Docker, local, and cloud deployment options
- **Upstream Benefits**: Automatically benefits from rag_api updates
- **REST API**: Standard HTTP API for any client integration

## Quick Start

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/ersantana361/toolkit-rag.git
cd toolkit-rag

# Initialize submodules if not using --recursive
git submodule update --init --recursive

# Start with Docker (recommended)
docker compose up -d

# Or install locally (requires rag_api submodule)
pip install -r requirements.txt
pip install -r rag_api/requirements.txt
python rag_api/main.py

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
├── rag_api/             # danny-avila/rag_api submodule (FastAPI server)
├── rag_client/          # Python client library wrapper
├── cli.py               # Command-line interface
├── docker/              # Deployment configurations for rag_api
├── docs/                # Generic documentation
└── examples/            # Integration examples
```

### Key Benefits

- **No Code Duplication**: Server implementation uses proven rag_api via submodule
- **Upstream Sync**: Automatically benefits from rag_api improvements and fixes
- **Clean Separation**: Toolkit-rag focuses on client/wrapper functionality
- **Framework Agnostic**: Generic interface works with any application
- **Battle Tested**: Built on the mature and well-tested rag_api foundation

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