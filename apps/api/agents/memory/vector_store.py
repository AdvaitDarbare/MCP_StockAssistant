import uuid
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_core.documents import Document
from fastembed import TextEmbedding
from apps.api.config import settings

class VectorStore:
    def __init__(self, collection_name: str = "conversation_memory"):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = collection_name
        
        # Initialize FastEmbed (lightweight, local, CPU-friendly)
        # BAAI/bge-small-en-v1.5 is a good default, ~384 dimensions
        self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        # vector_size for this model is 384
        self.embedding_dimension = 384 
        
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists in Qdrant."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_dimension,
                    distance=models.Distance.COSINE
                )
            )

    def add_documents(self, documents: List[Document]):
        """Add documents to the vector store."""
        if not documents:
            return

        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # Generate embeddings
        embeddings = list(self.embedding_model.embed(texts))
        
        points = []
        for i, (text, meta, vector) in enumerate(zip(texts, metadatas, embeddings)):
            point_id = str(uuid.uuid4())
            points.append(models.PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload={
                    "page_content": text,
                    **meta
                }
            ))
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def similarity_search(self, query: str, k: int = 3, filter: Optional[Dict] = None) -> List[Document]:
        """Search for similar documents."""
        query_vector = list(self.embedding_model.embed([query]))[0]

        query_filter = None
        if filter:
            conditions = []
            for key, value in filter.items():
                if value is None:
                    continue
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )
            if conditions:
                query_filter = models.Filter(must=conditions)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            limit=k,
            query_filter=query_filter,
        ).points
        
        docs = []
        for res in results:
            payload = res.payload
            text = payload.pop("page_content", "")
            docs.append(Document(page_content=text, metadata=payload))
            
        return docs
