#!/usr/bin/env python3
"""
Basic Toolkit-RAG Usage Example

This example demonstrates the fundamental operations:
- Indexing documents
- Searching content
- Managing projects
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_client import RAGClient, RAGConfig

async def main():
    """Demonstrate basic RAG operations"""
    
    print("🚀 Toolkit-RAG Basic Usage Example")
    print("=" * 50)
    
    # Configure the RAG client
    config = RAGConfig(
        api_url="http://localhost:8000",
        project_id="basic-example"
    )
    
    client = RAGClient(config)
    
    # 1. Check if the server is healthy
    print("1. Checking server health...")
    healthy = await client.health_check()
    if not healthy:
        print("❌ RAG server is not accessible. Please start the server:")
        print("   docker compose up -d")
        print("   Or: python -m rag_server")
        return
    
    print("✅ RAG server is healthy")
    
    # 2. Index some documents
    print("\n2. Indexing documents...")
    
    # Index the current directory (examples and docs)
    stats = await client.index_project(
        project_path=".",
        include_docs=True,
        include_code=True,
        recursive=True
    )
    
    if "error" in stats:
        print(f"❌ Indexing failed: {stats['error']}")
        return
    
    total = stats.get('total_files', 0)
    successful = stats.get('successful', 0)
    
    print(f"✅ Indexed {successful}/{total} files")
    
    # Show breakdown by type
    by_type = stats.get('by_type', {})
    if by_type:
        print("   Files by type:")
        for file_type, count in by_type.items():
            print(f"   • {file_type}: {count}")
    
    # 3. Search for content
    print("\n3. Searching for content...")
    
    search_queries = [
        "installation guide",
        "API endpoints",
        "Docker configuration",
        "search functionality"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Searching for: '{query}'")
        
        results = await client.search(
            query=query,
            limit=3
        )
        
        if results:
            print(f"   Found {len(results)} results:")
            
            for i, result in enumerate(results, 1):
                # Handle different result formats
                if isinstance(result, list) and len(result) > 0:
                    doc_data = result[0]
                    score = result[1] if len(result) > 1 else None
                else:
                    doc_data = result
                    score = None
                
                # Extract information
                if isinstance(doc_data, dict):
                    metadata = doc_data.get('metadata', {})
                    source = metadata.get('source', 'Unknown')
                    content = doc_data.get('page_content', '')[:150]
                    file_type = metadata.get('file_type', 'unknown')
                else:
                    source = 'Unknown'
                    content = str(doc_data)[:150]
                    file_type = 'unknown'
                
                print(f"   {i}. {source} ({file_type})")
                if score:
                    print(f"      Relevance: {score:.3f}")
                print(f"      {content}...")
        else:
            print("   No results found")
    
    # 4. Get project statistics
    print("\n4. Project statistics...")
    
    stats = await client.get_stats()
    if "error" not in stats:
        print("✅ Project statistics:")
        print(f"   • Documents: {stats.get('documents', {}).get('total', 0)}")
        print(f"   • Chunks: {stats.get('chunks', {}).get('total', 0)}")
        
        # Show file types
        by_type = stats.get('documents', {}).get('by_type', {})
        if by_type:
            print("   • By type:")
            for file_type, count in by_type.items():
                print(f"     - {file_type}: {count}")
    else:
        print(f"❌ Failed to get stats: {stats['error']}")
    
    # 5. Interactive exploration (optional)
    print("\n5. Interactive exploration available")
    print("   Run: await client.interactive_explore()")
    print("   This provides a command-line interface for real-time search")
    
    print("\n🎉 Basic usage example completed!")
    print("\nNext steps:")
    print("• Try different search queries")
    print("• Index more documents from different directories")
    print("• Experiment with different search modes (hybrid, semantic)")
    print("• Check out other examples in the examples/ directory")

if __name__ == "__main__":
    # Run the example
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        print("\nTroubleshooting:")
        print("• Make sure the RAG server is running: docker compose up -d")
        print("• Check if the API URL is correct (default: http://localhost:8000)")
        print("• Verify network connectivity to the RAG server")