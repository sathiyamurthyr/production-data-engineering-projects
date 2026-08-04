"""Pinecone Vector Database Client."""

import logging
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class VectorRecord(BaseModel):
    """Vector record."""
    id: str
    vector: list[float]
    metadata: dict[str, Any]
    content: str | None = None


class PineconeClient:
    """Pinecone vector database client."""
    
    def __init__(self, api_key: str, environment: str, index_name: str):
        """Initialize Pinecone client.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Index name
        """
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.client = None
        self.index = None
    
    def connect(self) -> None:
        """Connect to Pinecone."""
        try:
            import pinecone
            pinecone.init(api_key=self.api_key, environment=self.environment)
            self.index = pinecone.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"Pinecone connection failed: {e}")
            raise
    
    def add_vectors(self, vectors: list[VectorRecord]) -> bool:
        """Add vectors to index.
        
        Args:
            vectors: List of vector records
            
        Returns:
            True if successful
        """
        try:
            # Prepare vectors for Pinecone
            items = []
            for v in vectors:
                item = {
                    "id": v.id,
                    "values": v.vector,
                    "metadata": v.metadata,
                }
                if v.content:
                    item["metadata"]["content"] = v.content
                items.append(item)
            
            # Upsert in batches
            self.index.upsert(vectors=items)
            logger.info(f"Added {len(vectors)} vectors to Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False
    
    def search(self, vector: list[float], top_k: int = 10, filters: dict[str, Any] = None) -> list[dict[str, Any]]:
        """Search vectors.
        
        Args:
            vector: Query vector
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            Search results
        """
        try:
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                filter=filters,
                include_metadata=True,
            )
            
            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata,
                    "content": match.metadata.get("content", ""),
                }
                for match in results.matches
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete(self, ids: list[str]) -> bool:
        """Delete vectors.
        
        Args:
            ids: List of vector IDs
            
        Returns:
            True if successful
        """
        try:
            self.index.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def get_stats(self) -> dict[str, Any]:
        """Get index statistics.
        
        Returns:
            Index stats
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


class WeaviateClient:
    """Weaviate vector database client."""
    
    def __init__(self, url: str, api_key: str = None):
        """Initialize Weaviate client.
        
        Args:
            url: Weaviate URL
            api_key: API key (optional)
        """
        self.url = url
        self.api_key = api_key
        self.client = None
    
    def connect(self) -> None:
        """Connect to Weaviate."""
        try:
            import weaviate
            auth_config = weaviate.auth.AuthApiKey(api_key=self.api_key) if self.api_key else None
            self.client = weaviate.Client(url=self.url, auth_client_secret=auth_config)
            logger.info(f"Connected to Weaviate at {self.url}")
        except Exception as e:
            logger.error(f"Weaviate connection failed: {e}")
            raise
    
    def add_vectors(self, vectors: list[VectorRecord], class_name: str = "Document") -> bool:
        """Add vectors to Weaviate.
        
        Args:
            vectors: List of vector records
            class_name: Weaviate class name
            
        Returns:
            True if successful
        """
        try:
            with self.client.batch as batch:
                for v in vectors:
                    batch.add_data_object(
                        data_object={
                            "content": v.content,
                            **v.metadata,
                        },
                        class_name=class_name,
                        vector=v.vector,
                    )
            logger.info(f"Added {len(vectors)} vectors to Weaviate")
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False
    
    def search(self, vector: list[float], top_k: int = 10, filters: dict[str, Any] = None) -> list[dict[str, Any]]:
        """Search vectors.
        
        Args:
            vector: Query vector
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            Search results
        """
        try:
            query = self.client.query.get("Document", ["content", "metadata"]).with_near_vector({
                "vector": vector,
            }).with_limit(top_k)
            
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    filter_conditions.append({
                        "path": [key],
                        "operator": "Equal",
                        "valueString": str(value),
                    })
                query = query.with_where({
                    "operator": "And",
                    "operands": filter_conditions,
                })
            
            results = query.do()
            
            return [
                {
                    "id": item["id"],
                    "score": item["_additional"]["distance"],
                    "content": item.get("content", ""),
                    "metadata": item.get("metadata", {}),
                }
                for item in results["data"]["Get"]["Document"]
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete(self, ids: list[str], class_name: str = "Document") -> bool:
        """Delete vectors.
        
        Args:
            ids: List of vector IDs
            class_name: Weaviate class name
            
        Returns:
            True if successful
        """
        try:
            for id in ids:
                self.client.data_object.delete(id, class_name)
            logger.info(f"Deleted {len(ids)} vectors")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False


class ChromaClient:
    """Chroma vector database client."""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize Chroma client.
        
        Args:
            persist_directory: Directory to persist data
        """
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
    
    def connect(self, collection_name: str = "documents") -> None:
        """Connect to Chroma.
        
        Args:
            collection_name: Collection name
        """
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(collection_name)
            logger.info(f"Connected to Chroma collection: {collection_name}")
        except Exception as e:
            logger.error(f"Chroma connection failed: {e}")
            raise
    
    def add_vectors(self, vectors: list[VectorRecord]) -> bool:
        """Add vectors to Chroma.
        
        Args:
            vectors: List of vector records
            
        Returns:
            True if successful
        """
        try:
            ids = [v.id for v in vectors]
            embeddings = [v.vector for v in vectors]
            documents = [v.content or "" for v in vectors]
            metadatas = [v.metadata for v in vectors]
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(vectors)} vectors to Chroma")
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False
    
    def search(self, vector: list[float], top_k: int = 10, filters: dict[str, Any] = None) -> list[dict[str, Any]]:
        """Search vectors.
        
        Args:
            vector: Query vector
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            Search results
        """
        try:
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=top_k,
                where=filters,
            )
            
            return [
                {
                    "id": id,
                    "score": distance,
                    "content": document,
                    "metadata": metadata,
                }
                for id, document, distance, metadata in zip(
                    results["ids"][0],
                    results["documents"][0],
                    results["distances"][0],
                    results["metadatas"][0],
                )
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete(self, ids: list[str]) -> bool:
        """Delete vectors.
        
        Args:
            ids: List of vector IDs
            
        Returns:
            True if successful
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def get_stats(self) -> dict[str, Any]:
        """Get collection statistics.
        
        Returns:
            Collection stats
        """
        try:
            count = self.collection.count()
            return {"total_vectors": count}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


class PgVectorClient:
    """PostgreSQL pgvector client."""
    
    def __init__(self, connection_string: str, table_name: str = "vectors"):
        """Initialize pgvector client.
        
        Args:
            connection_string: Database connection string
            table_name: Table name
        """
        self.connection_string = connection_string
        self.table_name = table_name
        self.connection = None
    
    def connect(self) -> None:
        """Connect to PostgreSQL."""
        try:
            import psycopg2
            self.connection = psycopg2.connect(self.connection_string)
            logger.info("Connected to PostgreSQL pgvector")
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            raise
    
    def add_vectors(self, vectors: list[VectorRecord]) -> bool:
        """Add vectors to pgvector.
        
        Args:
            vectors: List of vector records
            
        Returns:
            True if successful
        """
        try:
            with self.connection.cursor() as cursor:
                for v in vectors:
                    cursor.execute(
                        f"INSERT INTO {self.table_name} (id, vector, metadata, content) VALUES (%s, %s, %s, %s)",
                        (v.id, str(v.vector), str(v.metadata), v.content),
                    )
            self.connection.commit()
            logger.info(f"Added {len(vectors)} vectors to pgvector")
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            self.connection.rollback()
            return False
    
    def search(self, vector: list[float], top_k: int = 10) -> list[dict[str, Any]]:
        """Search vectors.
        
        Args:
            vector: Query vector
            top_k: Number of results
            
        Returns:
            Search results
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT id, 1 - (vector <=> %s) AS score, metadata, content FROM {self.table_name} ORDER BY vector <=> %s LIMIT %s",
                    (str(vector), str(vector), top_k),
                )
                results = cursor.fetchall()
                
                return [
                    {
                        "id": row[0],
                        "score": row[1],
                        "metadata": row[2],
                        "content": row[3],
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete(self, ids: list[str]) -> bool:
        """Delete vectors.
        
        Args:
            ids: List of vector IDs
            
        Returns:
            True if successful
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM {self.table_name} WHERE id IN %s", (tuple(ids),))
            self.connection.commit()
            logger.info(f"Deleted {len(ids)} vectors")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            self.connection.rollback()
            return False