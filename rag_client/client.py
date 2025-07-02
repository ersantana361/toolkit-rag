#!/usr/bin/env python3
"""
Toolkit-RAG Client
Generic high-level interface for RAG operations
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Set, Union, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

from .processor import DocumentProcessor, DocumentType

class SearchMode(Enum):
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    KEYWORD = "keyword"

@dataclass
class RAGConfig:
    """Configuration for RAG operations"""
    api_url: str = "http://localhost:8000"
    project_id: str = "default"
    timeout: int = 30
    max_results: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 200

class RAGClient:
    """
    Generic high-level RAG client
    Provides easy-to-use interface for all RAG operations
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.processor = DocumentProcessor(
            rag_api_url=self.config.api_url,
            project_id=self.config.project_id
        )
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the RAG client"""
        logger = logging.getLogger('toolkit.rag.client')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    async def index_project(self, 
                          project_path: str = ".",
                          include_code: bool = True,
                          include_docs: bool = True,
                          include_configs: bool = False,
                          include_tests: bool = False,
                          recursive: bool = True) -> Dict[str, Any]:
        """
        Index project files for semantic search
        
        Args:
            project_path: Path to project directory
            include_code: Include source code files
            include_docs: Include documentation files  
            include_configs: Include configuration files
            include_tests: Include test files
            recursive: Process subdirectories
            
        Returns:
            Dictionary with indexing statistics
        """
        try:
            stats = await self.processor.process_project(
                project_path=project_path,
                include_code=include_code,
                include_docs=include_docs,
                include_configs=include_configs,
                include_tests=include_tests,
                recursive=recursive
            )
            return stats
        except Exception as e:
            self.logger.error(f"Failed to index project: {e}")
            return {"error": str(e), "total_files": 0, "successful": 0, "failed": 1}

    async def search(self,
                    query: str,
                    mode: SearchMode = SearchMode.SEMANTIC,
                    limit: int = 5,
                    file_types: Optional[List[str]] = None,
                    languages: Optional[List[str]] = None,
                    project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search indexed documents
        
        Args:
            query: Search query
            mode: Search mode (semantic, hybrid, keyword)
            limit: Maximum results to return
            file_types: Filter by file types
            languages: Filter by programming languages  
            project_id: Override default project ID
            
        Returns:
            List of search results
        """
        try:
            search_project_id = project_id or self.config.project_id
            
            search_data = {
                "query": query,
                "project_id": search_project_id,
                "limit": limit,
                "mode": mode.value
            }
            
            if file_types:
                search_data["file_types"] = file_types
            if languages:
                search_data["languages"] = languages
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.api_url}/search",
                    json=search_data,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Search failed: {response.status} - {error_text}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return []

    async def get_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get project indexing statistics
        
        Args:
            project_id: Override default project ID
            
        Returns:
            Statistics dictionary
        """
        try:
            stats_project_id = project_id or self.config.project_id
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.api_url}/projects/{stats_project_id}/stats",
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
                        
        except Exception as e:
            return {"error": str(e)}

    async def delete_project(self, project_id: Optional[str] = None) -> bool:
        """
        Delete all documents for a project
        
        Args:
            project_id: Project ID to delete (defaults to config project_id)
            
        Returns:
            True if successful
        """
        try:
            delete_project_id = project_id or self.config.project_id
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.config.api_url}/projects/{delete_project_id}",
                    timeout=self.config.timeout
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.error(f"Delete project error: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if RAG server is healthy
        
        Returns:
            True if server is healthy
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.api_url}/health",
                    timeout=5
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False

    async def interactive_explore(self) -> None:
        """
        Start interactive exploration mode
        
        Note: This is a basic implementation. 
        Applications should override this for custom UI.
        """
        print("🔍 Interactive RAG Exploration")
        print("Type 'quit' to exit, 'help' for commands")
        
        while True:
            try:
                query = input("\n> ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                elif query.lower() == 'help':
                    print("Commands:")
                    print("  <query>  - Search documents")
                    print("  stats    - Show project statistics")
                    print("  health   - Check server health")
                    print("  quit     - Exit")
                    continue
                elif query.lower() == 'stats':
                    stats = await self.get_stats()
                    print(json.dumps(stats, indent=2))
                    continue
                elif query.lower() == 'health':
                    healthy = await self.health_check()
                    print("🟢 Healthy" if healthy else "🔴 Unhealthy")
                    continue
                elif not query:
                    continue
                
                results = await self.search(query)
                
                if results:
                    print(f"\n📄 Found {len(results)} results:")
                    for i, result in enumerate(results, 1):
                        if isinstance(result, list) and len(result) > 0:
                            doc_data = result[0]
                            score = result[1] if len(result) > 1 else None
                        else:
                            doc_data = result
                            score = None
                        
                        if isinstance(doc_data, dict):
                            metadata = doc_data.get('metadata', {})
                            file_path = metadata.get('source', 'Unknown')
                            content = doc_data.get('page_content', '')
                        else:
                            file_path = 'Unknown'
                            content = str(doc_data)
                        
                        print(f"\n{i}. {file_path}")
                        if score:
                            print(f"   Score: {score:.3f}")
                        print(f"   {content[:200]}{'...' if len(content) > 200 else ''}")
                else:
                    print("❌ No results found")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def extract_patterns(self,
                             pattern_type: str = "architectural", 
                             limit: int = 10,
                             project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract patterns from indexed documents
        
        Args:
            pattern_type: Type of patterns to extract
            limit: Maximum patterns to return
            project_id: Override default project ID
            
        Returns:
            List of extracted patterns
        """
        # This is a placeholder - implement based on your pattern extraction needs
        search_query = f"{pattern_type} patterns"
        results = await self.search(search_query, limit=limit, project_id=project_id)
        
        # Transform results into pattern format
        patterns = []
        for result in results:
            if isinstance(result, list) and len(result) > 0:
                doc_data = result[0]
            else:
                doc_data = result
            
            if isinstance(doc_data, dict):
                metadata = doc_data.get('metadata', {})
                patterns.append({
                    "type": pattern_type,
                    "source": metadata.get('source', 'Unknown'),
                    "content": doc_data.get('page_content', ''),
                    "metadata": metadata
                })
        
        return patterns[:limit]