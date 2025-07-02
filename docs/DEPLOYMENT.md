# Toolkit-RAG Deployment Guide

## Overview

This guide covers production deployment strategies for Toolkit-RAG in various environments and scales.

## Deployment Architectures

### 1. Single Server Deployment

**Use case**: Small applications, development, proof of concept

```
┌─────────────────┐
│   Application   │
│                 │
├─────────────────┤
│  Toolkit-RAG    │
│    (Docker)     │
├─────────────────┤
│   PostgreSQL    │
│   + pgvector    │
├─────────────────┤
│     Ollama      │
│  (Embeddings)   │
└─────────────────┘
```

**Setup:**
```bash
# Single server with Docker Compose
git clone --recursive https://github.com/ersantana361/toolkit-rag.git
cd toolkit-rag
docker compose up -d

# Wait for model download (may take 2-5 minutes)
docker logs -f toolkit-rag-ollama-init-1

# Verify system health
curl http://localhost:8000/health
```

### 2. Microservices Architecture

**Use case**: Medium to large applications, better scalability

```
┌─────────────────┐    ┌─────────────────┐
│   Application   │────│   Load Balancer │
└─────────────────┘    └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌─────────▼────────┐    ┌─────────▼────────┐
│ RAG API Node 1 │    │ RAG API Node 2   │    │ RAG API Node 3   │
└────────────────┘    └──────────────────┘    └──────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌─────────▼────────┐    ┌─────────▼────────┐
│   PostgreSQL   │    │    Embeddings    │    │     Redis        │
│   (Primary)    │    │    Service       │    │    (Cache)       │
└────────────────┘    └──────────────────┘    └──────────────────┘
```

### 3. Cloud-Native Deployment

**Use case**: Large scale, high availability, managed services

```
┌─────────────────┐
│   Cloud LB      │ (AWS ALB, GCP LB, Azure LB)
└─────────────────┘
         │
┌─────────────────┐
│   Kubernetes    │ (EKS, GKE, AKS)
│   ┌─────────────┤
│   │ RAG Pods    │ (Auto-scaling)
│   └─────────────┤
└─────────────────┘
         │
┌─────────────────┐    ┌─────────────────┐
│  Managed DB     │    │  Managed Vector │
│  (RDS, etc.)    │    │  (Pinecone, etc)│
└─────────────────┘    └─────────────────┘
```

## Production Configurations

### 1. High-Performance Setup

**Docker Compose for Production:**
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  superclaude-rag:
    build:
      context: ./rag_api
      dockerfile: Dockerfile
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    environment:
      - DB_HOST=superclaude-postgres
      - DB_PORT=5432
      - POSTGRES_DB=superclaude_rag
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - VECTOR_DB_TYPE=pgvector
      - EMBEDDINGS_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres-primary:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: toolkit_rag
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_MAX_CONNECTIONS: 200
      POSTGRES_SHARED_BUFFERS: 256MB
      POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - rag-api

volumes:
  postgres_data:
  redis_data:
```

**Nginx Configuration:**
```nginx
# nginx.conf
upstream rag_backend {
    least_conn;
    server rag-api:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen 443 ssl http2;
    
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # File upload size
        client_max_body_size 100M;
    }
    
    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://rag_backend/health;
        access_log off;
    }
}
```

### 2. Kubernetes Deployment

**Namespace and ConfigMap:**
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: toolkit-rag

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
  namespace: toolkit-rag
data:
  DB_HOST: "postgres-service"
  DB_PORT: "5432"
  DB_NAME: "toolkit_rag"
  EMBEDDINGS_MODEL: "openai"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis-service:6379"
```

**Secrets:**
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
  namespace: toolkit-rag
type: Opaque
stringData:
  DB_USER: "admin"
  DB_PASSWORD: "supersecure"
  OPENAI_API_KEY: "your-openai-api-key"
```

**Deployment:**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
  namespace: toolkit-rag
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: rag-api
  template:
    metadata:
      labels:
        app: rag-api
    spec:
      containers:
      - name: rag-api
        image: toolkit-rag:v1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: rag-config
        - secretRef:
            name: rag-secrets
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
      volumes:
      - name: uploads
        persistentVolumeClaim:
          claimName: rag-uploads-pvc

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-api-service
  namespace: toolkit-rag
spec:
  selector:
    app: rag-api
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-api-hpa
  namespace: toolkit-rag
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Cloud Provider Specific Deployments

### AWS Deployment

**ECS with Fargate:**
```json
{
  "family": "toolkit-rag",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "rag-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/toolkit-rag:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DB_HOST",
          "value": "your-rds-endpoint"
        },
        {
          "name": "EMBEDDINGS_MODEL",
          "value": "openai"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:db-password"
        },
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/toolkit-rag",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

**Terraform Configuration:**
```hcl
# AWS infrastructure with Terraform
resource "aws_ecs_cluster" "rag_cluster" {
  name = "toolkit-rag"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_db_instance" "rag_postgres" {
  identifier = "toolkit-rag-db"
  engine     = "postgres"
  engine_version = "16.1"
  instance_class = "db.t3.medium"
  
  allocated_storage = 100
  max_allocated_storage = 1000
  storage_type = "gp3"
  
  db_name  = "toolkit_rag"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rag.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "toolkit-rag-final-snapshot"
  
  tags = {
    Name = "toolkit-rag-postgres"
  }
}

resource "aws_elasticache_replication_group" "rag_redis" {
  replication_group_id       = "toolkit-rag-redis"
  description                = "Redis cluster for Toolkit-RAG"
  
  node_type                  = "cache.t3.micro"
  port                       = 6379
  parameter_group_name       = "default.redis7"
  
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  subnet_group_name = aws_elasticache_subnet_group.rag.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Name = "toolkit-rag-redis"
  }
}
```

### Google Cloud Platform

**Cloud Run Deployment:**
```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: toolkit-rag
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/cpu: "2"
    spec:
      containers:
      - image: gcr.io/PROJECT_ID/toolkit-rag:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: "/cloudsql/PROJECT_ID:REGION:INSTANCE_ID"
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: username
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-credentials
              key: api-key
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        volumeMounts:
        - name: cloudsql
          mountPath: /cloudsql
          readOnly: true
      volumes:
      - name: cloudsql
        csi:
          driver: gcp.sql.csi.driver
          readOnly: true
          volumeAttributes:
            instanceConnectionName: PROJECT_ID:REGION:INSTANCE_ID
```

### Azure Deployment

**Container Instances:**
```yaml
# azure-container-instances.yaml
apiVersion: 2021-07-01
location: eastus
name: toolkit-rag-group
properties:
  containers:
  - name: rag-api
    properties:
      image: yourregistry.azurecr.io/toolkit-rag:latest
      ports:
      - port: 8000
        protocol: TCP
      environmentVariables:
      - name: DB_HOST
        value: your-postgres-server.postgres.database.azure.com
      - name: DB_USER
        secureValue: admin@your-postgres-server
      - name: DB_PASSWORD
        secureValue: your-password
      - name: OPENAI_API_KEY
        secureValue: your-openai-key
      resources:
        requests:
          cpu: 2.0
          memoryInGB: 4.0
        limits:
          cpu: 2.0
          memoryInGB: 4.0
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: TCP
      port: 8000
    dnsNameLabel: toolkit-rag-api
```

## Monitoring and Observability

### Application Metrics

**Prometheus Configuration:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
- job_name: 'toolkit-rag'
  static_configs:
  - targets: ['rag-api:8000']
  metrics_path: /metrics
  scrape_interval: 15s
```

**Grafana Dashboard:**
```json
{
  "dashboard": {
    "title": "Toolkit-RAG Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "postgresql_connections_active",
            "legendFormat": "Active Connections"
          }
        ]
      }
    ]
  }
}
```

### Logging

**Structured Logging Configuration:**
```python
# logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)

# Add JSON formatter for production
for handler in logging.getLogger().handlers:
    handler.setFormatter(JSONFormatter())
```

### Health Checks

**Comprehensive Health Check:**
```python
# health.py
from fastapi import APIRouter
from sqlalchemy import text
import aiohttp
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    checks = {
        "api": True,
        "database": await check_database(),
        "embeddings": await check_embeddings(),
        "disk_space": check_disk_space(),
        "memory": check_memory()
    }
    
    healthy = all(checks.values())
    
    return {
        "status": "healthy" if healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

async def check_database():
    try:
        # Test database connection
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False

async def check_embeddings():
    embeddings_model = os.getenv("EMBEDDINGS_MODEL", "ollama")
    
    if embeddings_model == "ollama":
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://ollama:11434/api/tags") as response:
                    return response.status == 200
        except Exception:
            return False
    elif embeddings_model == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    
    return False

def check_disk_space():
    import shutil
    total, used, free = shutil.disk_usage("/")
    return (free / total) > 0.1  # At least 10% free space

def check_memory():
    import psutil
    return psutil.virtual_memory().percent < 90  # Less than 90% memory usage
```

## Security Considerations

### 1. Network Security

```yaml
# network-policy.yaml (Kubernetes)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rag-network-policy
  namespace: toolkit-rag
spec:
  podSelector:
    matchLabels:
      app: rag-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS outbound
```

### 2. Secrets Management

**Using HashiCorp Vault:**
```python
# vault_integration.py
import hvac
import os

class VaultSecretManager:
    def __init__(self):
        self.client = hvac.Client(url=os.getenv('VAULT_URL'))
        self.client.token = os.getenv('VAULT_TOKEN')
    
    def get_secret(self, path):
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
    
    def get_db_credentials(self):
        secrets = self.get_secret('toolkit-rag/database')
        return {
            'username': secrets['username'],
            'password': secrets['password']
        }

# Usage
vault = VaultSecretManager()
db_creds = vault.get_db_credentials()
```

### 3. Rate Limiting and DDoS Protection

**Redis-based Rate Limiting:**
```python
# rate_limiter.py
import redis
import time
from fastapi import HTTPException

class RateLimiter:
    def __init__(self, redis_url):
        self.redis = redis.from_url(redis_url)
    
    async def check_rate_limit(self, key: str, limit: int, window: int):
        current_time = int(time.time())
        pipe = self.redis.pipeline()
        
        # Sliding window rate limiting
        pipe.zremrangebyscore(key, 0, current_time - window)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, window)
        
        results = pipe.execute()
        request_count = results[1]
        
        if request_count >= limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(window)}
            )
        
        return True

# Middleware
from fastapi import Request

rate_limiter = RateLimiter(os.getenv('REDIS_URL'))

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    endpoint = request.url.path
    
    # Different limits for different endpoints
    limits = {
        "/search": (100, 3600),  # 100 requests per hour
        "/documents": (20, 3600),  # 20 uploads per hour
    }
    
    if endpoint in limits:
        limit, window = limits[endpoint]
        await rate_limiter.check_rate_limit(f"{client_ip}:{endpoint}", limit, window)
    
    response = await call_next(request)
    return response
```

This deployment guide provides comprehensive production-ready configurations for various environments and scales. Choose the deployment strategy that best fits your requirements and infrastructure.