#!/bin/bash
# SuperClaude RAG Setup Script - HuggingFace TEI Configuration
# This script sets up the RAG system with HuggingFace Text-Embeddings-Inference

set -e

echo "🚀 Setting up SuperClaude RAG with HuggingFace TEI embeddings..."

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
cp .env.tei .env

# Start services
echo "🐳 Starting Docker services..."
docker compose -f docker-compose.tei.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
echo "Note: TEI service may take a few minutes to download the model on first run..."
sleep 60

# Check health
echo "🔍 Checking service status..."
docker compose -f docker-compose.tei.yml ps

# Test embedding service
echo "🧪 Testing TEI embedding service..."
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo "✅ TEI service is running"
else
    echo "⚠️  TEI service may still be downloading the model"
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
echo "  - TEI Embeddings: localhost:8080"  
echo "  - RAG API: localhost:8000"
echo ""
echo "Next steps:"
echo "  1. Test the setup: curl http://localhost:8000/health"
echo "  2. Index your project: /rag --index --recursive"
echo "  3. Start exploring: /rag --search 'your query'"
echo ""
echo "To stop services: docker compose -f docker-compose.tei.yml down"
echo "To view logs: docker compose -f docker-compose.tei.yml logs"