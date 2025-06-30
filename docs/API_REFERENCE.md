# Toolkit-RAG API Reference

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, Toolkit-RAG uses project-based isolation rather than authentication. Each request should include a `project_id` to isolate data between different projects or applications.

## Core Endpoints

### Health Check
Check if the RAG service is healthy and operational.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Database Health
Check database connectivity and pgvector extension.

```http
GET /health/database
```

**Response:**
```json
{
  "status": "healthy",
  "database": "postgresql",
  "pgvector": "0.5.1"
}
```

## Document Management

### Upload Document
Index a single document for semantic search.

```http
POST /documents
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (file): Document file to upload
- `project_id` (string): Project identifier for isolation
- `metadata` (string, optional): JSON string with additional metadata

**Example:**
```bash
curl -X POST "http://localhost:8000/documents" \
  -F "file=@document.pdf" \
  -F "project_id=my-project" \
  -F "metadata={\"source\": \"/path/to/document.pdf\", \"type\": \"documentation\"}"
```

**Response:**
```json
{
  "id": "doc_12345",
  "project_id": "my-project", 
  "filename": "document.pdf",
  "size": 1024,
  "chunks": 5,
  "status": "indexed"
}
```

### List Documents
Get all documents for a project.

```http
GET /documents/{project_id}
```

**Response:**
```json
{
  "project_id": "my-project",
  "total_documents": 10,
  "total_chunks": 150,
  "documents": [
    {
      "id": "doc_12345",
      "filename": "document.pdf",
      "size": 1024,
      "chunks": 5,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### Delete Document
Remove a document and its embeddings.

```http
DELETE /documents/{document_id}
```

**Response:**
```json
{
  "id": "doc_12345",
  "status": "deleted"
}
```

### Delete Project
Remove all documents and embeddings for a project.

```http
DELETE /projects/{project_id}
```

**Response:**
```json
{
  "project_id": "my-project",
  "documents_deleted": 10,
  "chunks_deleted": 150,
  "status": "deleted"
}
```

## Search Operations

### Semantic Search
Search documents using vector similarity.

```http
POST /search
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "authentication patterns",
  "project_id": "my-project",
  "mode": "semantic",
  "limit": 5,
  "min_score": 0.1,
  "file_types": ["code", "documentation"],
  "languages": ["python", "javascript"]
}
```

**Parameters:**
- `query` (string, required): Search query
- `project_id` (string, required): Project identifier
- `mode` (string): Search mode - "semantic", "hybrid", or "keyword" (default: "semantic")
- `limit` (integer): Maximum results to return (default: 10, max: 100)
- `min_score` (float): Minimum similarity score (default: 0.1)
- `file_types` (array): Filter by file types
- `languages` (array): Filter by programming languages

**Response:**
```json
{
  "query": "authentication patterns",
  "mode": "semantic",
  "total_results": 3,
  "results": [
    {
      "document_id": "doc_12345",
      "chunk_id": "chunk_67890",
      "score": 0.89,
      "content": "Authentication patterns in modern applications...",
      "metadata": {
        "source": "/path/to/auth.py",
        "file_type": "code",
        "language": "python",
        "line_start": 45,
        "line_end": 60
      }
    }
  ]
}
```

### Batch Search
Search multiple queries in a single request.

```http
POST /search/batch
Content-Type: application/json
```

**Request Body:**
```json
{
  "queries": [
    "authentication patterns",
    "error handling",
    "database connections"
  ],
  "project_id": "my-project",
  "mode": "semantic",
  "limit": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "query": "authentication patterns",
      "results": [...]
    },
    {
      "query": "error handling", 
      "results": [...]
    }
  ]
}
```

## Statistics and Analytics

### Project Statistics
Get detailed statistics for a project.

```http
GET /stats/{project_id}
```

**Response:**
```json
{
  "project_id": "my-project",
  "documents": {
    "total": 25,
    "by_type": {
      "code": 15,
      "documentation": 8,
      "configuration": 2
    },
    "by_language": {
      "python": 10,
      "javascript": 5,
      "markdown": 8,
      "yaml": 2
    }
  },
  "chunks": {
    "total": 450,
    "avg_per_document": 18
  },
  "storage": {
    "total_size_bytes": 2048576,
    "avg_document_size": 81943
  },
  "last_indexed": "2024-01-01T12:00:00Z"
}
```

### System Statistics
Get overall system statistics.

```http
GET /stats/system
```

**Response:**
```json
{
  "total_projects": 5,
  "total_documents": 125,
  "total_chunks": 2250,
  "total_storage_bytes": 10485760,
  "embedding_model": "nomic-embed-text",
  "vector_dimensions": 768,
  "database": {
    "type": "postgresql",
    "version": "16.1",
    "pgvector_version": "0.5.1"
  }
}
```

## Advanced Features

### Similar Documents
Find documents similar to a given document.

```http
POST /similar/{document_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "project_id": "my-project",
  "limit": 5,
  "min_score": 0.5
}
```

### Keyword Extraction
Extract keywords from documents or text.

```http
POST /keywords
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "Long text content to extract keywords from...",
  "limit": 10,
  "min_frequency": 2
}
```

**Response:**
```json
{
  "keywords": [
    {"term": "authentication", "score": 0.95, "frequency": 5},
    {"term": "security", "score": 0.87, "frequency": 3}
  ]
}
```

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

### 400 Bad Request
```json
{
  "error": "validation_error",
  "message": "project_id is required",
  "details": {
    "field": "project_id",
    "code": "required"
  }
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "message": "Document not found",
  "resource_id": "doc_12345"
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "message": "Database connection failed",
  "request_id": "req_abc123"
}
```

## Rate Limits

Current rate limits (may be adjusted):
- Search requests: 100 per minute per IP
- Upload requests: 20 per minute per IP
- Bulk operations: 5 per minute per IP

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Webhook Support

### Document Processing Events
Register webhooks to receive notifications about document processing events.

```http
POST /webhooks
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhooks/rag",
  "events": ["document.indexed", "document.failed"],
  "project_id": "my-project"
}
```

**Webhook Payload:**
```json
{
  "event": "document.indexed",
  "project_id": "my-project",
  "document_id": "doc_12345",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "filename": "document.pdf",
    "chunks": 5,
    "processing_time_ms": 1500
  }
}
```