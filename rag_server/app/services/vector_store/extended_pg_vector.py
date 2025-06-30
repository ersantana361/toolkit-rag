from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import delete, func, cast, Text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
from langchain_core.documents import Document
from langchain_community.vectorstores.pgvector import PGVector

class ExtendedPgVector(PGVector):
    def get_all_ids(self) -> list[str]:
        with Session(self._bind) as session:
            results = session.query(self.EmbeddingStore.custom_id).all()
            return [result[0] for result in results if result[0] is not None]
        
    def get_filtered_ids(self, ids: list[str]) -> list[str]:
        with Session(self._bind) as session:
            query = session.query(self.EmbeddingStore.custom_id).filter(self.EmbeddingStore.custom_id.in_(ids))
            results = query.all()
            return [result[0] for result in results if result[0] is not None]

    def get_documents_by_ids(self, ids: list[str]) -> list[Document]:
        with Session(self._bind) as session:
            results = (
                session.query(self.EmbeddingStore)
                .filter(self.EmbeddingStore.custom_id.in_(ids))
                .all()
            )
            return [
                Document(page_content=result.document, metadata=result.cmetadata or {})
                for result in results
                if result.custom_id in ids
            ]

    def _delete_multiple(
        self, ids: Optional[list[str]] = None, collection_only: bool = False
    ) -> None:
        with Session(self._bind) as session:
            if ids is not None:
                self.logger.debug(
                    "Trying to delete vectors by ids (represented by the model "
                    "using the custom ids field)"
                )
                stmt = delete(self.EmbeddingStore)
                if collection_only:
                    collection = self.get_collection(session)
                    if not collection:
                        self.logger.warning("Collection not found")
                        return
                    stmt = stmt.where(self.EmbeddingStore.collection_id == collection.uuid)
                stmt = stmt.where(self.EmbeddingStore.custom_id.in_(ids))
                session.execute(stmt)
            session.commit()

    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a project"""
        with Session(self._bind) as session:
            # Get documents filtered by project_id in metadata using proper JSONB operators
            query = session.query(self.EmbeddingStore).filter(
                self.EmbeddingStore.cmetadata.op('->>')('project_id') == project_id
            )
            
            documents = query.all()
            
            if not documents:
                return {
                    "project_id": project_id,
                    "total_documents": 0,
                    "total_chunks": 0,
                    "file_types": {},
                    "storage_size": 0,
                    "last_indexed": None
                }
            
            # Count unique files and total chunks
            unique_files = set()
            file_types = {}
            total_size = 0
            last_indexed = None
            
            for doc in documents:
                metadata = doc.cmetadata or {}
                
                # Track unique files
                file_id = metadata.get('file_id')
                if file_id:
                    unique_files.add(file_id)
                
                # Count file types
                file_type = metadata.get('file_type', 'unknown')
                if isinstance(file_type, str):
                    file_types[file_type] = file_types.get(file_type, 0) + 1
                
                # Calculate storage size (rough estimate)
                if doc.document:
                    total_size += len(doc.document.encode('utf-8'))
                
                # Track latest indexed time
                if hasattr(doc, 'created_at') and doc.created_at:
                    doc_created_at = doc.created_at
                    if isinstance(doc_created_at, str):
                        doc_created_at = datetime.fromisoformat(doc_created_at)
                    elif hasattr(doc_created_at, 'isoformat'):
                        # Already a datetime object
                        pass
                    else:
                        # Skip invalid datetime
                        continue
                        
                    if last_indexed is None:
                        last_indexed = doc_created_at.isoformat()
                    else:
                        last_indexed_dt = datetime.fromisoformat(last_indexed)
                        if doc_created_at > last_indexed_dt:
                            last_indexed = doc_created_at.isoformat()
            
            return {
                "project_id": project_id,
                "total_documents": len(unique_files),
                "total_chunks": len(documents),
                "file_types": file_types,
                "storage_size": total_size,
                "last_indexed": last_indexed
            }