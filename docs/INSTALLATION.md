# Toolkit-RAG Installation Guide

## Prerequisites

Toolkit-RAG uses [rag_api](https://github.com/danny-avila/rag_api) as a submodule dependency. Make sure to clone with submodules or initialize them after cloning.

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/ersantana361/toolkit-rag.git
cd toolkit-rag

# If you forgot --recursive, initialize submodules
git submodule update --init --recursive

# Start with default configuration (PostgreSQL + Ollama)
docker compose up -d

# Wait for services to start (30-60 seconds)
# Check status
python cli.py server health

# Index some documents
python cli.py index --path . --include-docs

# Search documents
python cli.py search "installation guide"
```

### Option 2: Local Installation

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/ersantana361/toolkit-rag.git
cd toolkit-rag

# Install toolkit-rag client dependencies
pip install -r requirements.txt

# Install rag_api server dependencies
pip install -r rag_api/requirements.txt

# Start the rag_api server locally
python rag_api/main.py

# Set up external services (PostgreSQL with pgvector)
# See deployment guides for different configurations
```

**Note**: Local installation requires setting up PostgreSQL with pgvector and an embeddings service (Ollama/OpenAI) separately.

## Deployment Options

### Local Development
- **Database**: PostgreSQL with pgvector extension
- **Embeddings**: Ollama (local models)
- **Use case**: Development, testing, offline usage

```bash
docker compose -f docker/docker-compose.local.yml up -d
```

### TEI Embeddings
- **Database**: PostgreSQL with pgvector extension  
- **Embeddings**: Text Embeddings Inference (TEI) server
- **Use case**: High-performance embeddings, GPU acceleration

```bash
docker compose -f docker/docker-compose.tei.yml up -d
```

### OpenAI Integration
- **Database**: PostgreSQL with pgvector extension
- **Embeddings**: OpenAI API
- **Use case**: Production usage with managed embeddings

```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key"
docker compose -f docker/docker-compose.openai.yml up -d
```

### Production Deployment
- **Database**: Managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- **Embeddings**: OpenAI API or managed service
- **Use case**: Production applications

```bash
# Configure production environment variables
docker compose -f docker/docker-compose.production.yml up -d
```

## Environment Variables

### Core Configuration
```bash
# API Configuration
RAG_API_URL=http://localhost:8000
RAG_HOST=0.0.0.0
RAG_PORT=8000

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=toolkit_rag
DB_USER=admin
DB_PASSWORD=supersecure
VECTOR_DB_TYPE=pgvector

# Embeddings Configuration
EMBEDDINGS_MODEL=ollama  # ollama, openai, tei
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
OPENAI_API_KEY=your-api-key-here
TEI_ENDPOINT=http://localhost:8080
```

### Optional Configuration
```bash
# Chunk Settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Processing Settings
PDF_EXTRACT_IMAGES=false
MAX_FILE_SIZE=10485760  # 10MB

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=false
```

## Health Checks

```bash
# Check overall system health
python cli.py server health

# Check individual components
curl http://localhost:8000/health
curl http://localhost:8000/health/database
curl http://localhost:11434/api/tags  # Ollama
```

## Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check Docker logs
docker compose logs rag-api
docker compose logs postgres
docker compose logs ollama

# Restart services
docker compose restart
```

**Database connection issues:**
```bash
# Test database connectivity
docker exec -it toolkit-rag-postgres psql -U admin -d toolkit_rag -c "SELECT 1;"
```

**Ollama model not found:**
```bash
# Pull embedding model
docker exec -it toolkit-rag-ollama ollama pull nomic-embed-text
```

**Port conflicts:**
```bash
# Check what's using ports
netstat -tulpn | grep -E "(5432|8000|11434)"

# Use different ports in docker-compose.yml
```

### Performance Tuning

**PostgreSQL optimization:**
```sql
-- Increase shared_buffers for better performance
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
SELECT pg_reload_conf();
```

**Ollama performance:**
```bash
# For GPU acceleration (if available)
docker run -d --gpus all -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
```

## Next Steps

- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Integration Guide](INTEGRATIONS.md) - How to integrate with your application
- [Deployment Guide](DEPLOYMENT.md) - Production deployment strategies