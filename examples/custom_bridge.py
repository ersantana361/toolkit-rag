#!/usr/bin/env python3
"""
Custom Bridge Example for Toolkit-RAG

This example shows how to create a custom bridge for integrating
Toolkit-RAG into your specific application or tool.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_client import RAGClient, RAGConfig, SearchMode

class CustomApplicationBridge:
    """
    Example bridge for integrating Toolkit-RAG into a custom application
    
    This bridge demonstrates:
    - Application-specific query enhancement
    - Custom result formatting
    - Context-aware search
    - Error handling and fallbacks
    """
    
    def __init__(self, application_name: str, api_url: str = "http://localhost:8000"):
        self.application_name = application_name
        self.project_id = f"{application_name.lower().replace(' ', '-')}"
        
        # Configure RAG client
        config = RAGConfig(
            api_url=api_url,
            project_id=self.project_id
        )
        
        self.client = RAGClient(config)
        self.logger = self._setup_logging()
        
        # Application-specific configurations
        self.query_enhancers = {
            'code': self._enhance_code_query,
            'docs': self._enhance_docs_query,
            'config': self._enhance_config_query,
            'error': self._enhance_error_query
        }
        
        # Context tracking
        self.search_history = []
        self.user_context = {}

    def _setup_logging(self) -> logging.Logger:
        """Setup application-specific logging"""
        logger = logging.getLogger(f'{self.application_name}.rag.bridge')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'[{self.application_name}] %(levelname)s: %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    async def setup_project(self, project_paths: List[str], **index_options) -> Dict[str, Any]:
        """
        Setup the project by indexing relevant documents
        
        Args:
            project_paths: List of paths to index
            **index_options: Additional indexing options
            
        Returns:
            Indexing statistics
        """
        self.logger.info(f"Setting up {self.application_name} project...")
        
        total_stats = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'by_type': {},
            'paths_indexed': []
        }
        
        for path in project_paths:
            self.logger.info(f"Indexing path: {path}")
            
            try:
                stats = await self.client.index_project(
                    project_path=path,
                    **index_options
                )
                
                if "error" not in stats:
                    # Aggregate statistics
                    total_stats['total_files'] += stats.get('total_files', 0)
                    total_stats['successful'] += stats.get('successful', 0)
                    total_stats['failed'] += stats.get('failed', 0)
                    total_stats['paths_indexed'].append(path)
                    
                    # Merge file type counts
                    by_type = stats.get('by_type', {})
                    for file_type, count in by_type.items():
                        total_stats['by_type'][file_type] = total_stats['by_type'].get(file_type, 0) + count
                
                else:
                    self.logger.error(f"Failed to index {path}: {stats['error']}")
                    total_stats['failed'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error indexing {path}: {e}")
                total_stats['failed'] += 1
        
        self.logger.info(f"Setup complete: {total_stats['successful']}/{total_stats['total_files']} files indexed")
        return total_stats

    async def smart_search(self, 
                          query: str, 
                          context_type: Optional[str] = None,
                          user_context: Optional[Dict] = None,
                          limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform context-aware search with application-specific enhancements
        
        Args:
            query: Search query
            context_type: Type of search context (code, docs, config, error)
            user_context: Additional user context
            limit: Maximum results to return
            
        Returns:
            Enhanced search results
        """
        # Update user context
        if user_context:
            self.user_context.update(user_context)
        
        # Enhance query based on context
        enhanced_query = await self._enhance_query(query, context_type)
        
        # Track search history
        self.search_history.append({
            'original_query': query,
            'enhanced_query': enhanced_query,
            'context_type': context_type,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        # Keep only recent history
        if len(self.search_history) > 10:
            self.search_history = self.search_history[-10:]
        
        try:
            # Perform search
            results = await self.client.search(
                query=enhanced_query,
                mode=SearchMode.SEMANTIC,
                limit=limit
            )
            
            # Format results for application
            formatted_results = await self._format_results(results, query, context_type)
            
            self.logger.info(f"Search completed: '{query}' -> {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def _enhance_query(self, query: str, context_type: Optional[str] = None) -> str:
        """Enhance query based on application context"""
        
        # Apply context-specific enhancers
        if context_type and context_type in self.query_enhancers:
            enhanced = self.query_enhancers[context_type](query)
            if enhanced != query:
                self.logger.debug(f"Enhanced query: '{query}' -> '{enhanced}'")
                return enhanced
        
        # Apply general enhancements
        enhanced_query = query
        
        # Add context from search history
        if self.search_history:
            recent_queries = [h['original_query'] for h in self.search_history[-3:]]
            if any(word in query.lower() for word in ['this', 'that', 'it', 'similar']):
                # User is referring to previous searches
                context_words = ' '.join(recent_queries)
                enhanced_query = f"{query} {context_words}"
        
        # Add user context
        if self.user_context.get('current_task'):
            task = self.user_context['current_task']
            enhanced_query = f"{query} {task}"
        
        return enhanced_query

    def _enhance_code_query(self, query: str) -> str:
        """Enhance queries for code search"""
        # Function definitions
        if query.startswith('def ') or query.startswith('function '):
            func_name = query.replace('def ', '').replace('function ', '').strip()
            return f"function {func_name} definition implementation method"
        
        # Class definitions
        elif query.startswith('class '):
            class_name = query.replace('class ', '').strip()
            return f"class {class_name} definition structure methods attributes"
        
        # Import statements
        elif query.startswith(('import ', 'from ', 'require(')):
            return f"{query} dependency module usage examples"
        
        # Error patterns
        elif query.lower().endswith(('error', 'exception')):
            return f"{query} handling patterns try catch recovery debugging"
        
        return query

    def _enhance_docs_query(self, query: str) -> str:
        """Enhance queries for documentation search"""
        # How-to queries
        if query.lower().startswith('how to'):
            return f"{query} tutorial guide instructions steps"
        
        # What is queries
        elif query.lower().startswith('what is'):
            return f"{query} explanation definition overview concept"
        
        # Installation/setup queries
        elif any(word in query.lower() for word in ['install', 'setup', 'configure']):
            return f"{query} installation setup configuration guide tutorial"
        
        return f"{query} documentation guide explanation"

    def _enhance_config_query(self, query: str) -> str:
        """Enhance queries for configuration search"""
        return f"{query} configuration settings environment variables options"

    def _enhance_error_query(self, query: str) -> str:
        """Enhance queries for error/troubleshooting search"""
        return f"{query} error troubleshooting debugging solution fix resolve"

    async def _format_results(self, 
                             results: List[Any], 
                             original_query: str,
                             context_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Format search results for application consumption"""
        formatted = []
        
        for i, result in enumerate(results):
            # Handle different result formats
            if isinstance(result, list) and len(result) > 0:
                doc_data = result[0]
                score = result[1] if len(result) > 1 else None
            else:
                doc_data = result
                score = None
            
            # Extract metadata and content
            if isinstance(doc_data, dict):
                metadata = doc_data.get('metadata', {})
                content = doc_data.get('page_content', '')
                
                formatted_result = {
                    'rank': i + 1,
                    'source': metadata.get('source', 'Unknown'),
                    'content': content,
                    'relevance_score': score,
                    'file_type': metadata.get('file_type', 'unknown'),
                    'language': metadata.get('language'),
                    'size': metadata.get('size'),
                    'context_type': context_type,
                    'query_match': self._calculate_query_match(content, original_query)
                }
                
                # Add application-specific enhancements
                formatted_result.update(
                    self._add_application_metadata(formatted_result, metadata)
                )
                
                formatted.append(formatted_result)
        
        return formatted

    def _calculate_query_match(self, content: str, query: str) -> Dict[str, Any]:
        """Calculate how well content matches the query"""
        query_words = query.lower().split()
        content_lower = content.lower()
        
        # Simple word matching
        matches = sum(1 for word in query_words if word in content_lower)
        match_ratio = matches / len(query_words) if query_words else 0
        
        return {
            'word_matches': matches,
            'total_words': len(query_words),
            'match_ratio': match_ratio
        }

    def _add_application_metadata(self, result: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add application-specific metadata to results"""
        enhancements = {}
        
        # Add file category
        file_type = result['file_type']
        if file_type == 'code':
            enhancements['category'] = 'Implementation'
            enhancements['icon'] = '🔧'
        elif file_type == 'documentation':
            enhancements['category'] = 'Documentation'
            enhancements['icon'] = '📚'
        elif file_type == 'configuration':
            enhancements['category'] = 'Configuration'
            enhancements['icon'] = '⚙️'
        else:
            enhancements['category'] = 'Other'
            enhancements['icon'] = '📄'
        
        # Add priority based on relevance
        score = result.get('relevance_score', 0)
        if score and score > 0.8:
            enhancements['priority'] = 'high'
        elif score and score > 0.5:
            enhancements['priority'] = 'medium'
        else:
            enhancements['priority'] = 'low'
        
        return enhancements

    async def get_project_insights(self) -> Dict[str, Any]:
        """Get insights about the project and search patterns"""
        # Get basic stats
        stats = await self.client.get_stats()
        
        insights = {
            'project_stats': stats,
            'search_insights': self._analyze_search_history(),
            'user_context': self.user_context,
            'recommendations': self._generate_recommendations()
        }
        
        return insights

    def _analyze_search_history(self) -> Dict[str, Any]:
        """Analyze search history for patterns"""
        if not self.search_history:
            return {}
        
        # Common query patterns
        query_types = {}
        for search in self.search_history:
            context_type = search.get('context_type', 'general')
            query_types[context_type] = query_types.get(context_type, 0) + 1
        
        # Recent search trends
        recent_queries = [s['original_query'] for s in self.search_history[-5:]]
        
        return {
            'total_searches': len(self.search_history),
            'query_types': query_types,
            'recent_queries': recent_queries
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on usage patterns"""
        recommendations = []
        
        # Based on search history
        if self.search_history:
            query_types = self._analyze_search_history()['query_types']
            most_common = max(query_types, key=query_types.get)
            
            recommendations.append(
                f"You frequently search for {most_common} content. Consider indexing more {most_common} files."
            )
        
        # Based on project stats
        # Add more recommendation logic here
        
        return recommendations

    def set_user_context(self, **context):
        """Set user context for better search results"""
        self.user_context.update(context)
        self.logger.debug(f"Updated user context: {context}")

    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info(f"Cleaning up {self.application_name} RAG bridge")
        # Perform any necessary cleanup


# Example usage
async def main():
    """Demonstrate custom bridge usage"""
    
    print("🔧 Custom Application Bridge Example")
    print("=" * 50)
    
    # Create a custom bridge for a hypothetical "DevTool"
    bridge = CustomApplicationBridge(
        application_name="DevTool Pro",
        api_url="http://localhost:8000"
    )
    
    # Check server health
    healthy = await bridge.client.health_check()
    if not healthy:
        print("❌ RAG server not available")
        return
    
    print("✅ RAG server is healthy")
    
    # Setup project
    print("\n📁 Setting up project...")
    stats = await bridge.setup_project(
        project_paths=["."],
        include_code=True,
        include_docs=True,
        recursive=True
    )
    
    print(f"✅ Indexed {stats['successful']}/{stats['total_files']} files")
    
    # Set user context
    bridge.set_user_context(
        current_task="implementing authentication",
        programming_language="python",
        experience_level="intermediate"
    )
    
    # Demonstrate different types of searches
    searches = [
        ("def authenticate", "code"),
        ("how to install", "docs"),
        ("database settings", "config"),
        ("connection timeout error", "error")
    ]
    
    print("\n🔍 Performing smart searches...")
    
    for query, context_type in searches:
        print(f"\n🎯 {context_type.upper()} search: '{query}'")
        
        results = await bridge.smart_search(
            query=query,
            context_type=context_type,
            limit=3
        )
        
        for result in results:
            print(f"   {result['icon']} {result['source']} ({result['category']})")
            print(f"      Priority: {result['priority']} | Match: {result['query_match']['match_ratio']:.2f}")
            print(f"      {result['content'][:100]}...")
    
    # Get project insights
    print("\n📊 Project insights...")
    insights = await bridge.get_project_insights()
    
    search_insights = insights['search_insights']
    print(f"✅ Total searches: {search_insights.get('total_searches', 0)}")
    print(f"✅ Query types: {search_insights.get('query_types', {})}")
    
    recommendations = insights['recommendations']
    if recommendations:
        print("\n💡 Recommendations:")
        for rec in recommendations:
            print(f"   • {rec}")
    
    # Cleanup
    await bridge.cleanup()
    
    print("\n🎉 Custom bridge example completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")