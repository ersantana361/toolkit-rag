#!/bin/bash
# SuperClaude RAG Setup Script - OpenAI Configuration
# This script sets up the RAG system with OpenAI embeddings

set -e

echo "🚀 Setting up SuperClaude RAG with OpenAI embeddings..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check for OpenAI API key
if [ -z "$RAG_OPENAI_API_KEY" ]; then
    echo "⚠️  OpenAI API key not found in environment."
    echo "Please set your OpenAI API key:"
    echo "  export RAG_OPENAI_API_KEY=your_api_key_here"
    echo ""
    echo "Or add it to the .env.openai file and run:"
    echo "  source .env.openai"
    exit 1
fi

# Clone RAG API if it doesn't exist
if [ ! -d "../rag_api" ]; then
    echo "📦 Cloning RAG API repository..."
    cd ..
    git clone https://github.com/danny-avila/rag_api.git
    cd docker
fi

# Copy and configure environment file
echo "⚙️  Setting up environment configuration..."
cp .env.openai .env
sed -i "s/your_openai_api_key_here/$RAG_OPENAI_API_KEY/g" .env

# Start services
echo "🐳 Starting Docker services..."
docker compose -f docker-compose.openai.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check health
echo "🔍 Checking service status..."
docker compose -f docker-compose.openai.yml ps

# Test RAG API
echo "🧪 Testing RAG API..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ RAG API is running"
else
    echo "⚠️  RAG API may still be starting up"
fi

# Test OpenAI connectivity
echo "🧪 Testing OpenAI connectivity..."
if curl -f -H "Authorization: Bearer $RAG_OPENAI_API_KEY" https://api.openai.com/v1/models >/dev/null 2>&1; then
    echo "✅ OpenAI API connection successful"
else
    echo "⚠️  OpenAI API connection failed - check your API key"
fi

echo ""
echo "🎉 SuperClaude RAG setup complete!"
echo ""
echo "Services running:"
echo "  - MongoDB: localhost:27017"
echo "  - RAG API: localhost:8000"
echo "  - OpenAI Embeddings: via API"
echo ""
echo "Next steps:"
echo "  1. Test the setup: curl http://localhost:8000/health"
echo "  2. Index your project: /rag --index --recursive"
echo "  3. Start exploring: /rag --search 'your query'"
echo ""
echo "To stop services: docker compose -f docker-compose.openai.yml down"
echo "To view logs: docker compose -f docker-compose.openai.yml logs"