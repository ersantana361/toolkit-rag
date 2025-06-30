#!/bin/bash
# SuperClaude RAG Setup Script - Local Ollama Configuration
# This script sets up the RAG system with local Ollama embeddings

set -e

echo "🚀 Setting up SuperClaude RAG with Ollama embeddings..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clone RAG API if it doesn't exist
if [ ! -d "../rag_api" ]; then
    echo "📦 Cloning RAG API repository..."
    cd ..
    git clone https://github.com/danny-avila/rag_api.git
    cd docker
fi

# Copy environment file
echo "⚙️  Setting up environment configuration..."
cp .env.local .env

# Start services
echo "🐳 Starting Docker services..."
docker compose -f docker-compose.local.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check health
echo "🔍 Checking service status..."
docker compose -f docker-compose.local.yml ps

# Test embedding service
echo "🧪 Testing Ollama embedding service..."
if curl -f http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama service is running"
else
    echo "⚠️  Ollama service may still be starting up"
fi

# Test RAG API
echo "🧪 Testing RAG API..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ RAG API is running"
else
    echo "⚠️  RAG API may still be starting up"
fi

echo ""
echo "🎉 SuperClaude RAG setup complete!"
echo ""
echo "Services running:"
echo "  - MongoDB: localhost:27017"
echo "  - Ollama: localhost:11434"  
echo "  - RAG API: localhost:8000"
echo ""
echo "Next steps:"
echo "  1. Test the setup: curl http://localhost:8000/health"
echo "  2. Index your project: /rag --index --recursive"
echo "  3. Start exploring: /rag --search 'your query'"
echo ""
echo "To stop services: docker compose -f docker-compose.local.yml down"
echo "To view logs: docker compose -f docker-compose.local.yml logs"