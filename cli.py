#!/usr/bin/env python3
"""
Toolkit-RAG Command Line Interface
Generic CLI for RAG operations
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from rag_client import RAGClient, RAGConfig, SearchMode
from rag_client.manager import RAGServerManager, RAGServerConfig, DeploymentType

def print_status(message: str, status: str = "info"):
    """Print formatted status messages"""
    icons = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️", "working": "🔄"}
    icon = icons.get(status, "ℹ️")
    print(f"{icon} {message}")

async def cmd_index(args):
    """Index project files"""
    config = RAGConfig(
        api_url=args.api_url,
        project_id=args.project_id
    )
    
    client = RAGClient(config)
    
    # Check if server is healthy
    if not await client.health_check():
        print_status("RAG server is not accessible. Please start the server first.", "error")
        print_status(f"Run: toolkit-rag server start", "info")
        return False
    
    print_status(f"Indexing project: {args.path}", "working")
    
    stats = await client.index_project(
        project_path=args.path,
        include_code=args.include_code,
        include_docs=args.include_docs,
        include_configs=args.include_configs,
        include_tests=args.include_tests,
        recursive=args.recursive
    )
    
    if "error" in stats:
        print_status(f"Indexing failed: {stats['error']}", "error")
        return False
    
    total = stats.get('total_files', 0)
    successful = stats.get('successful', 0)
    failed = stats.get('failed', 0)
    
    if successful > 0:
        print_status(f"Successfully indexed {successful}/{total} files", "success")
        
        # Show breakdown by type
        by_type = stats.get('by_type', {})
        if by_type:
            print_status("Files by type:", "info")
            for file_type, count in by_type.items():
                print(f"  • {file_type}: {count}")
                
        print_status("Ready for search!", "success")
        
    elif total == 0:
        print_status("No files found to index", "warning")
        print_status("Try adjusting --include-* flags or check project path", "info")
        
    else:
        print_status(f"Failed to index {failed}/{total} files", "error")
        
    return successful > 0

async def cmd_search(args):
    """Search indexed documents"""
    config = RAGConfig(
        api_url=args.api_url,
        project_id=args.project_id
    )
    
    client = RAGClient(config)
    
    # Check if server is healthy
    if not await client.health_check():
        print_status("RAG server is not accessible", "error")
        return False
    
    print_status(f"Searching for: '{args.query}'", "working")
    
    search_mode = SearchMode.HYBRID if args.hybrid else SearchMode.SEMANTIC
    
    results = await client.search(
        query=args.query,
        mode=search_mode,
        limit=args.limit,
        file_types=args.file_types,
        languages=args.languages
    )
    
    if not results:
        print_status("No results found", "warning")
        return False
    
    print_status(f"Found {len(results)} results:", "success")
    print()
    
    for i, result in enumerate(results, 1):
        # Handle nested array format
        if isinstance(result, list) and len(result) > 0:
            doc_data = result[0]
            score = result[1] if len(result) > 1 else None
        else:
            doc_data = result
            score = None
        
        # Extract metadata and content
        if isinstance(doc_data, dict):
            metadata = doc_data.get('metadata', {})
            file_path = metadata.get('source', 'Unknown file')
            content = doc_data.get('page_content', '')
            file_type = metadata.get('file_type', 'unknown')
            language = metadata.get('language', '')
        else:
            metadata = {}
            file_path = 'Unknown file'
            content = str(doc_data)
            file_type = 'unknown'
            language = ''
        
        # Display result
        print(f"📄 Result {i}: {file_path}")
        
        if score is not None:
            confidence_bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            print(f"   Relevance: {score:.3f} [{confidence_bar}]")
        
        if file_type != 'unknown':
            type_display = f"{file_type}"
            if language:
                type_display += f" ({language})"
            print(f"   Type: {type_display}")
        
        print(f"   Content: {content[:200]}{'...' if len(content) > 200 else ''}")
        print()
    
    return True

async def cmd_stats(args):
    """Get project statistics"""
    config = RAGConfig(
        api_url=args.api_url,
        project_id=args.project_id
    )
    
    client = RAGClient(config)
    
    stats = await client.get_stats()
    
    if "error" in stats:
        print_status(f"Failed to get stats: {stats['error']}", "error")
        return False
    
    print_status("Project Statistics", "info")
    print("=" * 20)
    print(json.dumps(stats, indent=2))
    
    return True

async def cmd_explore(args):
    """Interactive exploration mode"""
    config = RAGConfig(
        api_url=args.api_url,
        project_id=args.project_id
    )
    
    client = RAGClient(config)
    
    # Check if server is healthy
    if not await client.health_check():
        print_status("RAG server is not accessible", "error")
        return False
    
    try:
        await client.interactive_explore()
        return True
    except KeyboardInterrupt:
        print_status("Interactive exploration ended", "info")
        return True

async def cmd_server(args):
    """Server management commands"""
    # Determine project root and docker directory
    current_dir = Path.cwd()
    project_root = str(current_dir)
    
    # Look for docker directory in current location or parent
    docker_dir = None
    for check_dir in [current_dir, current_dir.parent]:
        potential_docker = check_dir / "docker"
        if potential_docker.exists():
            docker_dir = str(potential_docker)
            project_root = str(check_dir)
            break
    
    if not docker_dir:
        docker_dir = str(current_dir / "docker")  # Default to current/docker
    
    config = RAGServerConfig(
        deployment_type=DeploymentType(args.deployment),
        project_root=project_root,
        docker_dir=docker_dir,
        rag_api_url=args.api_url,
        log_level=args.log_level.upper()
    )
    
    manager = RAGServerManager(config)
    
    if args.server_command == "start":
        success = await manager.start_server()
        if success:
            print_status("Server started successfully!", "success")
            print(f"API URL: {args.api_url}")
        return success
        
    elif args.server_command == "stop":
        return await manager.stop_server()
        
    elif args.server_command == "restart":
        return await manager.restart_server()
        
    elif args.server_command == "status":
        status = await manager.get_status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            manager.print_status(status)
        return True
        
    elif args.server_command == "logs":
        logs = await manager.get_logs(args.service, args.tail)
        print(logs)
        return True
        
    elif args.server_command == "health":
        healthy = await manager.health_check()
        if args.json:
            print(json.dumps({"healthy": healthy}))
        else:
            print("🟢 Healthy" if healthy else "🔴 Unhealthy")
        return healthy
        
    elif args.server_command == "validate":
        return await manager.validate_setup()
    
    return False

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Toolkit-RAG - Generic RAG system for universal integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Server management
  %(prog)s server start --deployment local
  %(prog)s server status
  %(prog)s server stop
  
  # Document indexing
  %(prog)s index --path . --include-docs --include-code
  %(prog)s index --path /path/to/project --recursive
  
  # Document search
  %(prog)s search "authentication patterns"
  %(prog)s search "error handling" --limit 10 --hybrid
  
  # Statistics and exploration
  %(prog)s stats --project-id my-project
  %(prog)s explore --project-id my-project

For more information, see: https://github.com/ersantana361/toolkit-rag
        """
    )
    
    # Global options
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="RAG API URL")
    parser.add_argument("--project-id", default="default", 
                       help="Project identifier")
    parser.add_argument("--json", action="store_true", 
                       help="Output in JSON format")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARN", "ERROR"], 
                       default="INFO", help="Logging level")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Server management commands
    server_parser = subparsers.add_parser('server', help='Server management')
    server_parser.add_argument('server_command', 
                              choices=['start', 'stop', 'restart', 'status', 'logs', 'health', 'validate'])
    server_parser.add_argument("--deployment", "-d", 
                              choices=["local", "tei", "openai", "production"], 
                              default="local", help="Deployment type")
    server_parser.add_argument("--service", help="Specific service for logs")
    server_parser.add_argument("--tail", type=int, default=100, 
                              help="Number of log lines to show")
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Index project files')
    index_parser.add_argument('--path', default='.', help='Project directory path')
    index_parser.add_argument('--recursive', action='store_true', default=True, 
                             help='Process subdirectories')
    index_parser.add_argument('--include-code', action='store_true', default=True, 
                             help='Include source code files')
    index_parser.add_argument('--include-docs', action='store_true', default=True, 
                             help='Include documentation files')
    index_parser.add_argument('--include-configs', action='store_true', default=False, 
                             help='Include configuration files')
    index_parser.add_argument('--include-tests', action='store_true', default=False, 
                             help='Include test files')
    index_parser.add_argument('--include-all', action='store_true', 
                             help='Include all supported file types')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search indexed documents')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=5, 
                              help='Number of results to return')
    search_parser.add_argument('--hybrid', action='store_true', 
                              help='Use hybrid search (vector + keyword)')
    search_parser.add_argument('--file-types', nargs='+', 
                              help='Filter by file types')
    search_parser.add_argument('--languages', nargs='+', 
                              help='Filter by programming languages')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Get project statistics')
    
    # Explore command
    explore_parser = subparsers.add_parser('explore', help='Interactive exploration')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle --include-all flag
    if hasattr(args, 'include_all') and args.include_all:
        args.include_code = True
        args.include_docs = True
        args.include_configs = True
        args.include_tests = True
    
    try:
        if args.command == 'server':
            success = asyncio.run(cmd_server(args))
        elif args.command == 'index':
            success = asyncio.run(cmd_index(args))
        elif args.command == 'search':
            success = asyncio.run(cmd_search(args))
        elif args.command == 'stats':
            success = asyncio.run(cmd_stats(args))
        elif args.command == 'explore':
            success = asyncio.run(cmd_explore(args))
        else:
            print(f"Unknown command: {args.command}")
            return 1
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())