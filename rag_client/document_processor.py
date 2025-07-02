#!/usr/bin/env python3
"""
SuperClaude Document Processing Pipeline
Integrates with RAG API for intelligent document indexing and retrieval
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging
from dataclasses import dataclass
from enum import Enum

class DocumentType(Enum):
    CODE = "code"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    TEST = "test"
    OTHER = "other"

@dataclass
class DocumentMetadata:
    file_path: str
    file_type: DocumentType
    language: Optional[str]
    size: int
    last_modified: float
    project_id: str

class SuperClaudeDocumentProcessor:
    """
    Document processing pipeline for SuperClaude RAG integration
    """
    
    def __init__(self, rag_api_url: str = "http://localhost:8000", project_id: str = "superclaude"):
        self.rag_api_url = rag_api_url.rstrip('/')
        self.project_id = project_id
        self.logger = self._setup_logging()
        
        # File type mappings
        self.code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', 
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.r', '.m', '.mm', '.sql', '.sh', '.bash', '.ps1', '.lua', '.pl'
        }
        
        self.doc_extensions = {
            '.md', '.txt', '.rst', '.adoc', '.tex', '.doc', '.docx', '.pdf'
        }
        
        self.config_extensions = {
            '.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.cfg', 
            '.env', '.properties', '.xml', '.plist'
        }
        
        self.test_patterns = {
            'test_', '_test', '.test.', '.spec.', 'tests/', 'test/', 
            '__tests__/', 'spec/', 'cypress/', 'e2e/'
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the document processor"""
        logger = logging.getLogger('superclaude.rag.processor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def _get_file_type(self, file_path: str) -> DocumentType:
        """Determine the document type based on file path and extension"""
        path = Path(file_path)
        extension = path.suffix.lower()
        filename = path.name.lower()
        path_str = str(path).lower()
        
        # Check for test files first
        if any(pattern in path_str for pattern in self.test_patterns):
            return DocumentType.TEST
        
        # Check by extension
        if extension in self.code_extensions:
            return DocumentType.CODE
        elif extension in self.doc_extensions:
            return DocumentType.DOCUMENTATION
        elif extension in self.config_extensions:
            return DocumentType.CONFIGURATION
        else:
            return DocumentType.OTHER

    def _get_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension"""
        extension_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.tsx': 'typescript', '.jsx': 'javascript', '.java': 'java',
            '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.cs': 'csharp',
            '.php': 'php', '.rb': 'ruby', '.go': 'go', '.rs': 'rust',
            '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
            '.r': 'r', '.m': 'objective-c', '.sql': 'sql',
            '.sh': 'bash', '.bash': 'bash', '.ps1': 'powershell'
        }
        
        extension = Path(file_path).suffix.lower()
        return extension_map.get(extension)

    def _should_process_file(self, file_path: str, include_patterns: Set[str]) -> bool:
        """Determine if a file should be processed based on patterns"""
        path = Path(file_path)
        
        # Skip hidden files and directories
        if any(part.startswith('.') for part in path.parts):
            # Allow specific dotfiles that are important
            allowed_dotfiles = {'.gitignore', '.env.example', '.dockerignore'}
            if path.name not in allowed_dotfiles:
                return False
        
        # Skip common build/cache directories
        skip_dirs = {
            'node_modules', 'dist', 'build', '__pycache__', '.git',
            'venv', 'env', '.venv', 'target', 'bin', 'obj', 'out'
        }
        
        if any(skip_dir in str(path) for skip_dir in skip_dirs):
            return False
        
        # Check include patterns
        if 'all' in include_patterns:
            return True
        
        file_type = self._get_file_type(str(path))
        
        return (
            ('code' in include_patterns and file_type == DocumentType.CODE) or
            ('docs' in include_patterns and file_type == DocumentType.DOCUMENTATION) or
            ('configs' in include_patterns and file_type == DocumentType.CONFIGURATION) or
            ('tests' in include_patterns and file_type == DocumentType.TEST)
        )

    async def _upload_document(self, session: aiohttp.ClientSession, 
                             file_path: str, metadata: DocumentMetadata) -> bool:
        """Upload a single document to the RAG API"""
        try:
            with open(file_path, 'rb') as file:
                # Generate a unique file_id based on file path
                import hashlib
                file_id = hashlib.md5(file_path.encode()).hexdigest()[:10] + "_" + Path(file_path).name.replace('.', '_')
                
                form_data = aiohttp.FormData()
                form_data.add_field('file_id', file_id)
                form_data.add_field('entity_id', self.project_id)
                form_data.add_field('file', file, filename=Path(file_path).name)
                
                async with session.post(f"{self.rag_api_url}/embed", 
                                      data=form_data) as response:
                    if response.status == 200:
                        self.logger.info(f"Successfully uploaded: {file_path}")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to upload {file_path}: {error_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error uploading {file_path}: {str(e)}")
            return False

    async def index_project(self, 
                          project_path: str, 
                          include_patterns: Set[str] = {'code', 'docs'},
                          recursive: bool = True,
                          batch_size: int = 10) -> Dict[str, int]:
        """
        Index an entire project directory
        
        Args:
            project_path: Path to the project directory
            include_patterns: Set of patterns to include ('code', 'docs', 'configs', 'tests', 'all')
            recursive: Whether to process subdirectories
            batch_size: Number of files to process concurrently
            
        Returns:
            Dict with statistics about the indexing operation
        """
        self.logger.info(f"Starting project indexing: {project_path}")
        
        project_path = Path(project_path)
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
        
        # Collect all files to process
        files_to_process = []
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in project_path.glob(pattern):
            if file_path.is_file() and self._should_process_file(str(file_path), include_patterns):
                try:
                    stat = file_path.stat()
                    metadata = DocumentMetadata(
                        file_path=str(file_path),
                        file_type=self._get_file_type(str(file_path)),
                        language=self._get_language(str(file_path)),
                        size=stat.st_size,
                        last_modified=stat.st_mtime,
                        project_id=self.project_id
                    )
                    files_to_process.append((str(file_path), metadata))
                except Exception as e:
                    self.logger.warning(f"Could not process {file_path}: {str(e)}")
        
        self.logger.info(f"Found {len(files_to_process)} files to process")
        
        # Process files in batches
        stats = {
            'total_files': len(files_to_process),
            'successful': 0,
            'failed': 0,
            'by_type': {}
        }
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(files_to_process), batch_size):
                batch = files_to_process[i:i + batch_size]
                
                tasks = [
                    self._upload_document(session, file_path, metadata)
                    for file_path, metadata in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (file_path, metadata), result in zip(batch, results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Exception processing {file_path}: {result}")
                        stats['failed'] += 1
                    elif result:
                        stats['successful'] += 1
                        file_type = metadata.file_type.value
                        stats['by_type'][file_type] = stats['by_type'].get(file_type, 0) + 1
                    else:
                        stats['failed'] += 1
                
                self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(files_to_process) - 1)//batch_size + 1}")
        
        self.logger.info(f"Indexing complete. Success: {stats['successful']}, Failed: {stats['failed']}")
        return stats

    async def search_documents(self, 
                             query: str, 
                             limit: int = 5,
                             filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search indexed documents using the RAG API
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            filters: Optional filters for the search
            
        Returns:
            List of search results
        """
        search_data = {
            'query': query,
            'limit': limit,
            'project_id': self.project_id
        }
        
        if filters:
            search_data['filters'] = filters
        
        async with aiohttp.ClientSession() as session:
            # First get all available file IDs
            async with session.get(f"{self.rag_api_url}/ids") as ids_response:
                if ids_response.status != 200:
                    self.logger.error("Failed to get file IDs")
                    return []
                
                file_ids = await ids_response.json()
                if not file_ids:
                    self.logger.warning("No indexed files found")
                    return []
            
            # Use query_multiple endpoint to search across all files
            query_data = {
                'query': query,
                'file_ids': file_ids,
                'k': limit
            }
            
            async with session.post(f"{self.rag_api_url}/query_multiple", 
                                  json=query_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    self.logger.error(f"Search failed: {error_text}")
                    return []

    async def get_project_stats(self) -> Dict:
        """Get statistics about the indexed project"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.rag_api_url}/projects/{self.project_id}/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {'error': 'Failed to get project stats'}

    async def health_check(self) -> bool:
        """Check if the RAG API is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.rag_api_url}/health") as response:
                    return response.status == 200
        except Exception:
            return False


# CLI interface for the document processor
async def main():
    """CLI interface for the SuperClaude document processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SuperClaude Document Processor")
    parser.add_argument("command", choices=["index", "search", "stats", "health"])
    parser.add_argument("--project-path", default=".", help="Path to project directory")
    parser.add_argument("--include", nargs="+", default=["code", "docs"], 
                       choices=["code", "docs", "configs", "tests", "all"],
                       help="File types to include")
    parser.add_argument("--recursive", action="store_true", default=True,
                       help="Process subdirectories recursively")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Search result limit")
    parser.add_argument("--rag-url", default="http://localhost:8000", help="RAG API URL")
    parser.add_argument("--project-id", default="superclaude", help="Project ID")
    
    args = parser.parse_args()
    
    processor = SuperClaudeDocumentProcessor(
        rag_api_url=args.rag_url,
        project_id=args.project_id
    )
    
    if args.command == "index":
        stats = await processor.index_project(
            project_path=args.project_path,
            include_patterns=set(args.include),
            recursive=args.recursive
        )
        print(f"Indexing results: {json.dumps(stats, indent=2)}")
    
    elif args.command == "search":
        if not args.query:
            print("Error: --query is required for search command")
            return
        
        results = await processor.search_documents(
            query=args.query,
            limit=args.limit
        )
        print(f"Search results: {json.dumps(results, indent=2)}")
    
    elif args.command == "stats":
        stats = await processor.get_project_stats()
        print(f"Project stats: {json.dumps(stats, indent=2)}")
    
    elif args.command == "health":
        healthy = await processor.health_check()
        print(f"RAG API health: {'OK' if healthy else 'FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())