# Toolkit-RAG

A comprehensive RAG (Retrieval-Augmented Generation) system designed for integration with any application, CLI tool, or AI assistant. Built around a forked and enhanced version of [rag_api](https://github.com/ersantana361/rag_api) with SuperClaude-specific improvements.

## Overview

Toolkit-RAG provides document indexing, vector search, and semantic retrieval as a production-ready service. It features:

- **Enhanced RAG API**: Forked rag_api with SuperClaude optimizations and bug fixes
- **Docker-First Architecture**: Containerized deployment with multiple configuration options
- **Multiple Backends**: PostgreSQL/pgvector, MongoDB Atlas, local Ollama embeddings
- **Flexible Deployment**: Docker Compose, local, and cloud deployment options
- **Production Ready**: Health checks, restart policies, and robust error handling
- **REST API**: Standard HTTP API for universal client integration

## Quick Start

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/ersantana361/toolkit-rag.git
cd toolkit-rag

# Start with Docker (recommended)
docker compose up -d

# Check system health
curl http://localhost:8000/health

# Index documents
curl -X POST "http://localhost:8000/embed" \
  -F "file=@document.pdf" \
  -F "file_id=my-document"

# Search documents (using query_multiple endpoint)
curl -X POST "http://localhost:8000/query_multiple" \
  -H "Content-Type: application/json" \
  -d '{"query": "search terms", "file_ids": ["my-document"], "k": 5}'
```

## Network Troubleshooting

If you encounter Ollama model download issues:

```bash
# Check connectivity to Ollama registry
curl -I https://registry.ollama.ai

# If connection fails, try:
# 1. Different network (mobile hotspot)
# 2. VPN connection
# 3. Different DNS servers in docker-compose.yml
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