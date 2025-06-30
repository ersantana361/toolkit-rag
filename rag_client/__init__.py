"""
Toolkit-RAG Client Library

Generic Python client for interacting with Toolkit-RAG server.
Provides high-level interfaces for document indexing, search, and management.
"""

from .client import RAGClient, RAGConfig, SearchMode
from .manager import RAGServerManager, RAGServerConfig, DeploymentType, ServiceStatus
from .processor import DocumentProcessor, DocumentType

__version__ = "1.0.0"
__all__ = [
    "RAGClient",
    "RAGConfig", 
    "SearchMode",
    "RAGServerManager",
    "RAGServerConfig",
    "DeploymentType",
    "ServiceStatus",
    "DocumentProcessor",
    "DocumentType"
]