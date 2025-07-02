#!/usr/bin/env python3
"""
SuperClaude RAG Client
High-level interface for RAG operations in SuperClaude
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Set, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

from document_processor import SuperClaudeDocumentProcessor, DocumentType

class SearchMode(Enum):
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    KEYWORD = "keyword"

@dataclass
class RAGConfig:
    """Configuration for RAG operations"""
    api_url: str = "http://localhost:8000"
    project_id: str = "superclaude"
    timeout: int = 30
    max_results: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 200

class SuperClaudeRAGClient:
    """
    High-level RAG client for SuperClaude integration
    Provides easy-to-use interface for all RAG operations
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.processor = SuperClaudeDocumentProcessor(
            rag_api_url=self.config.api_url,
            project_id=self.config.project_id
        )
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the RAG client"""
        logger = logging.getLogger('superclaude.rag.client')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    async def index_project(self, 
                          project_path: str = ".",
                          include_code: bool = True,
                          include_docs: bool = True,
                          include_configs: bool = False,
                          include_tests: bool = False,
                          recursive: bool = True) -> Dict:
        """
        Index a project with simplified interface
        
        Args:
            project_path: Path to project directory
            include_code: Include source code files
            include_docs: Include documentation files
            include_configs: Include configuration files
            include_tests: Include test files
            recursive: Process subdirectories
            
        Returns:
            Indexing statistics
        """
        include_patterns = set()
        
        if include_code:
            include_patterns.add('code')
        if include_docs:
            include_patterns.add('docs')
        if include_configs:
            include_patterns.add('configs')
        if include_tests:
            include_patterns.add('tests')
        
        if not include_patterns:
            include_patterns.add('all')
        
        self.logger.info(f"Indexing project: {project_path}")
        self.logger.info(f"Including: {', '.join(include_patterns)}")
        
        return await self.processor.index_project(
            project_path=project_path,
            include_patterns=include_patterns,
            recursive=recursive
        )

    async def search(self, 
                   query: str,
                   mode: SearchMode = SearchMode.SEMANTIC,
                   limit: int = 5,
                   file_types: Optional[List[str]] = None,
                   languages: Optional[List[str]] = None) -> List[Dict]:
        """
        Search indexed documents with advanced options
        
        Args:
            query: Search query string
            mode: Search mode (semantic, hybrid, keyword)
            limit: Maximum number of results
            file_types: Filter by file types
            languages: Filter by programming languages
            
        Returns:
            Search results with metadata
        """
        filters = {}
        
        if file_types:
            filters['file_types'] = file_types
        if languages:
            filters['languages'] = languages
        
        self.logger.info(f"Searching: '{query}' (mode: {mode.value}, limit: {limit})")
        
        # Use the appropriate search endpoint based on mode
        if mode == SearchMode.HYBRID:
            return await self._hybrid_search(query, limit, filters)
        else:
            return await self.processor.search_documents(query, limit, filters)

    async def _hybrid_search(self, query: str, limit: int, filters: Dict) -> List[Dict]:
        """Perform hybrid search combining semantic and keyword search"""
        # For now, use the same semantic search since /search/hybrid doesn't exist
        # This could be enhanced in the future by combining multiple search strategies
        self.logger.info("Using semantic search for hybrid mode (hybrid endpoint not available)")
        return await self.processor.search_documents(query, limit, filters)

    async def find_similar(self, file_path: str, limit: int = 5) -> List[Dict]:
        """
        Find documents similar to a specific file
        
        Args:
            file_path: Path to the reference file
            limit: Maximum number of results
            
        Returns:
            Similar documents
        """
        self.logger.info(f"Finding similar documents to: {file_path}")
        
        async with aiohttp.ClientSession() as session:
            search_data = {
                'file_path': file_path,
                'limit': limit,
                'project_id': self.config.project_id
            }
            
            async with session.post(f"{self.config.api_url}/search/similar", 
                                  json=search_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Similar search failed: {await response.text()}")
                    return []

    async def extract_patterns(self, 
                             pattern_type: str = "architectural",
                             limit: int = 10) -> List[Dict]:
        """
        Extract code patterns from indexed documents
        
        Args:
            pattern_type: Type of patterns to extract
            limit: Maximum number of patterns
            
        Returns:
            Extracted patterns
        """
        self.logger.info(f"Extracting {pattern_type} patterns")
        
        async with aiohttp.ClientSession() as session:
            search_data = {
                'pattern_type': pattern_type,
                'limit': limit,
                'project_id': self.config.project_id
            }
            
            async with session.post(f"{self.config.api_url}/patterns/extract", 
                                  json=search_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Pattern extraction failed: {await response.text()}")
                    return []

    async def analyze_context(self, 
                            context: str,
                            focus: str = "implementation") -> Dict:
        """
        Analyze context and provide relevant suggestions
        
        Args:
            context: Context description or code snippet
            focus: Analysis focus (implementation, security, performance, etc.)
            
        Returns:
            Context analysis results
        """
        self.logger.info(f"Analyzing context with focus: {focus}")
        
        async with aiohttp.ClientSession() as session:
            analysis_data = {
                'context': context,
                'focus': focus,
                'project_id': self.config.project_id
            }
            
            async with session.post(f"{self.config.api_url}/analyze/context", 
                                  json=analysis_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Context analysis failed: {await response.text()}")
                    return {}

    async def get_stats(self) -> Dict:
        """Get project statistics"""
        return await self.processor.get_project_stats()

    async def health_check(self) -> bool:
        """Check RAG API health"""
        return await self.processor.health_check()

    async def interactive_explore(self) -> None:
        """
        Interactive exploration mode for the RAG system
        """
        print("🔍 SuperClaude RAG Interactive Explorer")
        print("Type 'help' for commands, 'quit' to exit")
        
        while True:
            try:
                command = input("\nrag> ").strip()
                
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                elif command.lower() == 'help':
                    self._print_help()
                elif command.startswith('search '):
                    query = command[7:]
                    results = await self.search(query)
                    self._print_search_results(results)
                elif command.startswith('similar '):
                    file_path = command[8:]
                    results = await self.find_similar(file_path)
                    self._print_search_results(results)
                elif command == 'stats':
                    stats = await self.get_stats()
                    print(json.dumps(stats, indent=2))
                elif command == 'health':
                    healthy = await self.health_check()
                    print(f"RAG API: {'✅ Healthy' if healthy else '❌ Unhealthy'}")
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

    def _print_help(self):
        """Print help for interactive mode"""
        print("""
Available commands:
  search <query>     - Search indexed documents
  similar <file>     - Find documents similar to file
  stats             - Show project statistics
  health            - Check RAG API health
  help              - Show this help message
  quit              - Exit interactive mode
""")

    def _print_search_results(self, results: List[Dict]):
        """Print formatted search results"""
        if not results:
            print("No results found.")
            return
        
        print(f"\nFound {len(results)} result(s):")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.get('file_path', 'Unknown file')}")
            if 'score' in result:
                print(f"   Score: {result['score']:.3f}")
            if 'snippet' in result:
                print(f"   Snippet: {result['snippet'][:100]}...")


# CLI interface for the RAG client
async def main():
    """CLI interface for the SuperClaude RAG client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SuperClaude RAG Client")
    parser.add_argument("command", nargs="?", default="interactive",
                       choices=["index", "search", "similar", "patterns", "analyze", "stats", "health", "interactive"])
    parser.add_argument("--project-path", default=".", help="Path to project directory")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--file", help="File path for similarity search")
    parser.add_argument("--pattern-type", default="architectural", help="Pattern type to extract")
    parser.add_argument("--context", help="Context for analysis")
    parser.add_argument("--focus", default="implementation", help="Analysis focus")
    parser.add_argument("--limit", type=int, default=5, help="Result limit")
    parser.add_argument("--include-code", action="store_true", default=True)
    parser.add_argument("--include-docs", action="store_true", default=True)
    parser.add_argument("--include-configs", action="store_true", default=False)
    parser.add_argument("--include-tests", action="store_true", default=False)
    parser.add_argument("--rag-url", default="http://localhost:8000", help="RAG API URL")
    parser.add_argument("--project-id", default="superclaude", help="Project ID")
    
    args = parser.parse_args()
    
    config = RAGConfig(
        api_url=args.rag_url,
        project_id=args.project_id
    )
    
    client = SuperClaudeRAGClient(config)
    
    if args.command == "index":
        stats = await client.index_project(
            project_path=args.project_path,
            include_code=args.include_code,
            include_docs=args.include_docs,
            include_configs=args.include_configs,
            include_tests=args.include_tests
        )
        print(json.dumps(stats, indent=2))
    
    elif args.command == "search":
        if not args.query:
            print("Error: --query is required for search command")
            return
        
        results = await client.search(args.query, limit=args.limit)
        client._print_search_results(results)
    
    elif args.command == "similar":
        if not args.file:
            print("Error: --file is required for similar command")
            return
        
        results = await client.find_similar(args.file, limit=args.limit)
        client._print_search_results(results)
    
    elif args.command == "patterns":
        results = await client.extract_patterns(args.pattern_type, limit=args.limit)
        print(json.dumps(results, indent=2))
    
    elif args.command == "analyze":
        if not args.context:
            print("Error: --context is required for analyze command")
            return
        
        results = await client.analyze_context(args.context, args.focus)
        print(json.dumps(results, indent=2))
    
    elif args.command == "stats":
        stats = await client.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.command == "health":
        healthy = await client.health_check()
        print(f"RAG API: {'✅ Healthy' if healthy else '❌ Unhealthy'}")
    
    elif args.command == "interactive":
        await client.interactive_explore()

if __name__ == "__main__":
    asyncio.run(main())