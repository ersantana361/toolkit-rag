# Toolkit-RAG Integration Guide

## Overview

Toolkit-RAG is designed to be easily integrated into any application, CLI tool, or AI assistant. Built as a client/wrapper around [rag_api](https://github.com/danny-avila/rag_api), it provides a clean, framework-agnostic interface while leveraging a proven, battle-tested RAG implementation.

## Architecture

```
Your Application
      ↓
  toolkit-rag (client wrapper)
      ↓  
  rag_api (FastAPI server - submodule)
      ↓
  Database + Vector Store
```

This guide shows various integration patterns and examples.

## Integration Patterns

### 1. Python Client Library

The most straightforward way to integrate Toolkit-RAG into Python applications.

```python
from rag_client import RAGClient, RAGConfig

# Configure the client
config = RAGConfig(
    api_url="http://localhost:8000",
    project_id="my-application"
)

client = RAGClient(config)

# Index documents
stats = await client.index_project(
    project_path="./docs",
    include_docs=True,
    include_code=True
)

# Search documents
results = await client.search(
    query="authentication patterns",
    limit=10
)

# Process results
for result in results:
    print(f"Found: {result['metadata']['source']}")
    print(f"Content: {result['content'][:200]}...")
```

### 2. REST API Integration

For non-Python applications or microservices architecture.

```javascript
// JavaScript/Node.js example
const axios = require('axios');

class RAGClient {
    constructor(apiUrl, projectId) {
        this.apiUrl = apiUrl;
        this.projectId = projectId;
    }

    async search(query, limit = 10) {
        const response = await axios.post(`${this.apiUrl}/search`, {
            query: query,
            project_id: this.projectId,
            limit: limit
        });
        return response.data.results;
    }

    async uploadDocument(filePath, metadata = {}) {
        const formData = new FormData();
        formData.append('file', fs.createReadStream(filePath));
        formData.append('project_id', this.projectId);
        formData.append('metadata', JSON.stringify(metadata));

        const response = await axios.post(`${this.apiUrl}/documents`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    }
}

// Usage
const rag = new RAGClient('http://localhost:8000', 'my-app');
const results = await rag.search('error handling patterns');
```

### 3. Command Line Integration

Using the CLI interface from shell scripts or other command-line tools.

```bash
#!/bin/bash
# Shell script integration example

# Index a project
toolkit-rag index --path /path/to/project --include-all

# Search and process results
results=$(toolkit-rag search "authentication" --json --limit 5)
echo "$results" | jq '.results[].metadata.source'

# Check system health
if toolkit-rag server health --json | jq -r '.healthy'; then
    echo "RAG system is healthy"
else
    echo "RAG system needs attention"
    exit 1
fi
```

### 4. Git Submodule Integration

Adding Toolkit-RAG as a submodule to your project. This is the recommended pattern for tight integration.

```bash
# Add as submodule (includes rag_api dependency)
git submodule add https://github.com/ersantana361/toolkit-rag.git rag
git submodule update --init --recursive

# Project structure
your-project/
├── rag/                    # Toolkit-RAG submodule
│   ├── rag_api/           # danny-avila/rag_api (nested submodule)
│   ├── rag_client/        # Generic client wrapper
│   └── docker/            # Server deployment configs
├── src/
├── docs/
└── my_rag_bridge.py       # Your custom bridge

# Custom bridge example
import sys
from pathlib import Path

# Add toolkit-rag to path
sys.path.insert(0, str(Path(__file__).parent / "rag"))

from rag_client import RAGClient, RAGConfig

class MyProjectRAGBridge:
    def __init__(self):
        config = RAGConfig(
            api_url="http://localhost:8000",
            project_id="my-project"
        )
        self.client = RAGClient(config)
    
    async def search_with_context(self, query):
        # Add project-specific enhancements
        enhanced_query = self.enhance_query(query)
        results = await self.client.search(enhanced_query)
        return self.format_results(results)
    
    def enhance_query(self, query):
        # Project-specific query enhancement logic
        return f"{query} project-context"
    
    def format_results(self, results):
        # Project-specific result formatting
        return results
```

## Framework-Specific Integrations

### Django Integration

```python
# settings.py
RAG_CONFIG = {
    'API_URL': 'http://localhost:8000',
    'PROJECT_ID': 'django-app',
    'INDEX_ON_SAVE': True,
}

# models.py
from django.db import models
from django.db.models.signals import post_save
from rag_client import RAGClient

class Document(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    file = models.FileField(upload_to='documents/')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if settings.RAG_CONFIG['INDEX_ON_SAVE']:
            self.index_document()
    
    def index_document(self):
        client = RAGClient(api_url=settings.RAG_CONFIG['API_URL'])
        # Index the document...

# views.py
from django.shortcuts import render
from rag_client import RAGClient

def search_view(request):
    query = request.GET.get('q', '')
    if query:
        client = RAGClient()
        results = await client.search(query)
        return render(request, 'search_results.html', {'results': results})
    return render(request, 'search.html')
```

### Flask Integration

```python
from flask import Flask, request, jsonify
from rag_client import RAGClient
import asyncio

app = Flask(__name__)
rag_client = RAGClient()

@app.route('/search')
async def search():
    query = request.args.get('q', '')
    results = await rag_client.search(query)
    return jsonify(results)

@app.route('/upload', methods=['POST'])
async def upload():
    file = request.files['file']
    project_id = request.form.get('project_id', 'flask-app')
    
    # Save file and index
    stats = await rag_client.index_project(file.filename)
    return jsonify(stats)
```

### FastAPI Integration

```python
from fastapi import FastAPI, UploadFile, File
from rag_client import RAGClient

app = FastAPI()
rag_client = RAGClient()

@app.post("/search/")
async def search_documents(query: str, limit: int = 10):
    results = await rag_client.search(query, limit=limit)
    return {"results": results}

@app.post("/documents/")
async def upload_document(file: UploadFile = File(...)):
    stats = await rag_client.process_single_file(file.filename)
    return {"status": "indexed" if stats else "failed"}
```

## AI Assistant Integration

### Generic AI Assistant Bridge

```python
class AIAssistantRAGBridge:
    """Generic bridge for AI assistants"""
    
    def __init__(self, assistant_name: str):
        self.assistant_name = assistant_name
        self.client = RAGClient(project_id=assistant_name)
    
    async def enhance_query(self, user_query: str, context: dict = None) -> str:
        """Enhance user query with context"""
        # Add assistant-specific query enhancement
        if context and context.get('conversation_history'):
            # Include conversation context
            pass
        return user_query
    
    async def search_knowledge(self, query: str, context: dict = None) -> list:
        """Search knowledge base with assistant-specific formatting"""
        enhanced_query = await self.enhance_query(query, context)
        results = await self.client.search(enhanced_query)
        return self.format_for_assistant(results)
    
    def format_for_assistant(self, results: list) -> list:
        """Format results for assistant consumption"""
        formatted = []
        for result in results:
            formatted.append({
                'content': result['content'],
                'source': result['metadata']['source'],
                'relevance': result['score'],
                'type': result['metadata'].get('file_type', 'unknown')
            })
        return formatted

# Usage in different assistants
claude_bridge = AIAssistantRAGBridge("claude-assistant")
gpt_bridge = AIAssistantRAGBridge("gpt-assistant")
```

### Claude Code Integration

```python
# ~/.claude/bridge.py - SuperClaude specific bridge
class SuperClaudeRAGBridge(AIAssistantRAGBridge):
    def __init__(self):
        super().__init__("superclaude")
    
    async def enhance_query_for_code(self, query: str) -> str:
        """SuperClaude-specific query enhancement for code"""
        # Convert "def authenticate" to semantic code search
        if query.startswith('def '):
            func_name = query.replace('def ', '').strip()
            return f"function {func_name} definition implementation"
        
        # Class searches
        elif query.startswith('class '):
            class_name = query.replace('class ', '').strip()
            return f"class {class_name} definition structure"
        
        return query
    
    def format_results_for_claude(self, results: list) -> str:
        """Format results for Claude Code display"""
        output = []
        for i, result in enumerate(results, 1):
            source = result['metadata']['source']
            content = result['content'][:200]
            
            output.append(f"📄 Result {i}: {source}")
            output.append(f"   {content}...")
            output.append("")
        
        return "\n".join(output)
```

## Docker Integration

### As a Service

```yaml
# docker-compose.yml for your application
version: '3.8'

services:
  your-app:
    build: .
    depends_on:
      - rag-service
    environment:
      - RAG_API_URL=http://rag-service:8000
  
  rag-service:
    image: toolkit-rag:latest
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=postgres
      - EMBEDDINGS_MODEL=ollama
    depends_on:
      - postgres
      - ollama
  
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: toolkit_rag
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: supersecure
  
  ollama:
    image: ollama/ollama:latest
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: toolkit-rag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: toolkit-rag
  template:
    metadata:
      labels:
        app: toolkit-rag
    spec:
      containers:
      - name: rag-api
        image: toolkit-rag:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: "postgres-service"
        - name: EMBEDDINGS_MODEL
          value: "openai"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: openai-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: toolkit-rag-service
spec:
  selector:
    app: toolkit-rag
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

## Environment-Specific Examples

### Development Environment

```python
# dev_config.py
import os
from rag_client import RAGConfig

# Development configuration
def get_dev_config():
    return RAGConfig(
        api_url="http://localhost:8000",
        project_id=f"dev-{os.getenv('USER', 'unknown')}",
        timeout=60,  # Longer timeout for debugging
    )

# Auto-index on file changes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DevRAGHandler(FileSystemEventHandler):
    def __init__(self, rag_client):
        self.client = rag_client
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(('.py', '.md', '.txt')):
            asyncio.create_task(self.client.process_single_file(event.src_path))

# Start file watcher
client = RAGClient(get_dev_config())
handler = DevRAGHandler(client)
observer = Observer()
observer.schedule(handler, "./", recursive=True)
observer.start()
```

### Production Environment

```python
# prod_config.py
from rag_client import RAGConfig
import os

def get_prod_config():
    return RAGConfig(
        api_url=os.getenv("RAG_API_URL", "http://rag-service:8000"),
        project_id=os.getenv("RAG_PROJECT_ID", "production-app"),
        timeout=30,
        max_results=20,
    )

# Health monitoring
import asyncio
import logging

async def monitor_rag_health():
    """Monitor RAG service health"""
    client = RAGClient(get_prod_config())
    while True:
        try:
            healthy = await client.health_check()
            if not healthy:
                logging.error("RAG service is unhealthy")
                # Send alert to monitoring system
            else:
                logging.info("RAG service is healthy")
        except Exception as e:
            logging.error(f"Health check failed: {e}")
        
        await asyncio.sleep(60)  # Check every minute

# Run health monitor
asyncio.create_task(monitor_rag_health())
```

## Best Practices

### 1. Project Isolation
```python
# Use different project IDs for different contexts
user_docs = RAGClient(project_id=f"user-{user_id}")
public_docs = RAGClient(project_id="public-knowledge")
code_docs = RAGClient(project_id=f"codebase-{repo_name}")
```

### 2. Error Handling
```python
async def safe_search(client, query):
    try:
        results = await client.search(query)
        return results
    except aiohttp.ClientTimeout:
        # Handle timeout
        return []
    except aiohttp.ClientError as e:
        # Handle network errors
        logging.error(f"RAG search failed: {e}")
        return []
    except Exception as e:
        # Handle unexpected errors
        logging.error(f"Unexpected error: {e}")
        return []
```

### 3. Caching
```python
from functools import lru_cache
import hashlib

class CachedRAGClient:
    def __init__(self, client):
        self.client = client
        self._cache = {}
    
    async def search(self, query, **kwargs):
        # Create cache key
        cache_key = hashlib.md5(f"{query}{kwargs}".encode()).hexdigest()
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        results = await self.client.search(query, **kwargs)
        self._cache[cache_key] = results
        return results
```

### 4. Batch Processing
```python
async def batch_index_documents(client, file_paths):
    """Index multiple documents efficiently"""
    tasks = []
    for file_path in file_paths:
        task = client.process_single_file(file_path)
        tasks.append(task)
    
    # Process in batches of 10
    batch_size = 10
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        results = await asyncio.gather(*batch, return_exceptions=True)
        
        # Handle results and errors
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Batch indexing error: {result}")
```

This integration guide provides comprehensive examples for various use cases. Choose the pattern that best fits your application architecture and requirements.