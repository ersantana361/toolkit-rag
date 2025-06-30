#!/usr/bin/env python3
"""
Toolkit-RAG Document Processing Pipeline
Generic document indexing and retrieval for any project
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
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

class DocumentProcessor:
    """
    Generic document processing pipeline for RAG integration
    """
    
    def __init__(self, rag_api_url: str = "http://localhost:8000", project_id: str = "default"):
        self.rag_api_url = rag_api_url.rstrip('/')
        self.project_id = project_id
        self.logger = self._setup_logging()
        
        # File type mappings
        self.code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', 
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.r', '.m', '.mm', '.sql', '.sh', '.bash', '.ps1', '.lua', '.pl',
            '.dart', '.vue', '.svelte', '.elm', '.clj', '.cljs', '.hs', '.ml',
            '.fs', '.vb', '.pas', '.asm', '.s', '.scss', '.sass', '.less', '.css'
        }
        
        self.doc_extensions = {
            '.md', '.txt', '.rst', '.adoc', '.org', '.tex', '.rtf',
            '.pdf', '.doc', '.docx', '.odt', '.html', '.htm', '.xml'
        }
        
        self.config_extensions = {
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            '.env', '.properties', '.plist', '.config'
        }
        
        self.test_patterns = {
            'test_', '_test', '.test.', '.spec.', '_spec', 'tests/',
            'test/', '__test__', '__tests__'
        }
        
        # Language detection mapping
        self.language_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.h': 'c',
            '.cs': 'csharp', '.php': 'php', '.rb': 'ruby', '.go': 'go',
            '.rs': 'rust', '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
            '.sql': 'sql', '.sh': 'bash', '.bash': 'bash', '.ps1': 'powershell',
            '.html': 'html', '.css': 'css', '.scss': 'scss', '.sass': 'sass',
            '.vue': 'vue', '.svelte': 'svelte', '.dart': 'dart'
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for document processor"""
        logger = logging.getLogger('toolkit.rag.processor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def _classify_document(self, file_path: Path) -> DocumentType:
        """Classify document based on file path and extension"""
        file_str = str(file_path).lower()
        extension = file_path.suffix.lower()
        
        # Check if it's a test file
        if any(pattern in file_str for pattern in self.test_patterns):
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

    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension"""
        extension = file_path.suffix.lower()
        return self.language_map.get(extension)

    def _should_include_file(self, 
                           file_path: Path,
                           include_code: bool,
                           include_docs: bool,
                           include_configs: bool,
                           include_tests: bool) -> bool:
        """Determine if file should be included based on type and flags"""
        doc_type = self._classify_document(file_path)
        
        # Standard exclusions
        exclusions = {
            '.git', '__pycache__', 'node_modules', '.pytest_cache',
            '.mypy_cache', '.coverage', 'dist', 'build', '.venv', 
            'venv', '.env', 'env', '.DS_Store', 'Thumbs.db'
        }
        
        if any(excl in str(file_path) for excl in exclusions):
            return False
        
        # Check file size (skip very large files)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
                return False
        except OSError:
            return False
        
        # Check inclusion flags
        if doc_type == DocumentType.CODE and not include_code:
            return False
        elif doc_type == DocumentType.DOCUMENTATION and not include_docs:
            return False
        elif doc_type == DocumentType.CONFIGURATION and not include_configs:
            return False
        elif doc_type == DocumentType.TEST and not include_tests:
            return False
        
        return True

    async def _upload_document(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Upload a single document to RAG API"""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create form data
            form_data = aiohttp.FormData()
            form_data.add_field('file', file_content, filename=file_path.name)
            form_data.add_field('project_id', metadata.project_id)
            form_data.add_field('metadata', json.dumps({
                'source': str(file_path),
                'file_type': metadata.file_type.value,
                'language': metadata.language,
                'size': metadata.size,
                'last_modified': metadata.last_modified
            }))
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.rag_api_url}/documents",
                    data=form_data,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.warning(f"Failed to upload {file_path}: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            self.logger.warning(f"Error uploading {file_path}: {e}")
            return False

    async def process_project(self,
                            project_path: str = ".",
                            include_code: bool = True,
                            include_docs: bool = True,
                            include_configs: bool = False,
                            include_tests: bool = False,
                            recursive: bool = True) -> Dict[str, Any]:
        """
        Process all files in a project directory
        
        Args:
            project_path: Path to project directory
            include_code: Include source code files
            include_docs: Include documentation files
            include_configs: Include configuration files
            include_tests: Include test files
            recursive: Process subdirectories
            
        Returns:
            Processing statistics
        """
        project_dir = Path(project_path).resolve()
        
        if not project_dir.exists():
            return {"error": f"Project path does not exist: {project_path}"}
        
        # Collect files to process
        files_to_process = []
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in project_dir.glob(pattern):
            if file_path.is_file() and self._should_include_file(
                file_path, include_code, include_docs, include_configs, include_tests
            ):
                files_to_process.append(file_path)
        
        if not files_to_process:
            return {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "by_type": {},
                "message": "No files found to process"
            }
        
        # Process files
        stats = {
            "total_files": len(files_to_process),
            "successful": 0,
            "failed": 0,
            "by_type": {}
        }
        
        for file_path in files_to_process:
            doc_type = self._classify_document(file_path)
            language = self._detect_language(file_path)
            
            try:
                file_stat = file_path.stat()
                metadata = DocumentMetadata(
                    file_path=str(file_path),
                    file_type=doc_type,
                    language=language,
                    size=file_stat.st_size,
                    last_modified=file_stat.st_mtime,
                    project_id=self.project_id
                )
                
                success = await self._upload_document(file_path, metadata)
                
                if success:
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1
                
                # Track by type
                type_name = doc_type.value
                if type_name not in stats["by_type"]:
                    stats["by_type"][type_name] = 0
                stats["by_type"][type_name] += 1
                
            except Exception as e:
                self.logger.warning(f"Error processing {file_path}: {e}")
                stats["failed"] += 1
        
        return stats

    async def process_single_file(self, file_path: str) -> bool:
        """
        Process a single file
        
        Args:
            file_path: Path to file to process
            
        Returns:
            True if successful
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            self.logger.error(f"File does not exist: {file_path}")
            return False
        
        doc_type = self._classify_document(file_path_obj)
        language = self._detect_language(file_path_obj)
        
        try:
            file_stat = file_path_obj.stat()
            metadata = DocumentMetadata(
                file_path=str(file_path_obj),
                file_type=doc_type,
                language=language,
                size=file_stat.st_size,
                last_modified=file_stat.st_mtime,
                project_id=self.project_id
            )
            
            return await self._upload_document(file_path_obj, metadata)
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return False