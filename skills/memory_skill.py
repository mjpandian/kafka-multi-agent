
import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
import ollama

class MemorySkill:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.active = False
        
        # Connect to Qdrant service defined in docker-compose or local
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        try:
            self.client = QdrantClient(host=qdrant_host, port=6333, timeout=5)
            self.collection_name = "agent_memories"
            
            # Ensure collection exists
            try:
                self.client.get_collection(self.collection_name)
            except Exception:
                print(f"Creating collection {self.collection_name}...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
                )
            self.active = True
        except Exception as e:
            print(f"⚠️ MemorySkill: Could not connect to Qdrant at {qdrant_host}: {e}")

    def _get_embedding(self, text):
        # Use ollama to get embeddings. Host is configured via environment variable usually,
        # but here we might need to assume a default or pass it.
        # Assuming OLLAMA_URL env var is set or localhost default works within network if configured.
        # However, in 'ollama' python lib, client needs host.
        
        # Strip /v1 if present because ollama library expects base URL
        ollama_host = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        if ollama_host.endswith("/v1"):
            ollama_host = ollama_host[:-3]
            
        client = ollama.Client(host=ollama_host)
        
        response = client.embeddings(model="nomic-embed-text", prompt=text)
        return response["embedding"]

    def add_memory(self, content, metadata=None):
        """Stores a fact or experience."""
        if not self.active:
            return False
        try:
            vector = self._get_embedding(content)
            
            payload = {"content": content, "agent_id": self.agent_id}
            if metadata:
                payload.update(metadata)

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            print(f"📝 Memory added for {self.agent_id}: {content[:30]}...")
            return True
        except Exception as e:
            print(f"❌ Memory Add Error: {e}")
            return False

    def get_memories(self, query, limit=3):
        """Retrieves relevant memories."""
        if not self.active:
            return []
        try:
            vector = self._get_embedding(query)
            
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="agent_id",
                            match=models.MatchValue(value=self.agent_id)
                        )
                    ]
                ),
                limit=limit
            ).points
            
            memories = []
            for hit in search_result:
                memories.append({"text": hit.payload["content"], "score": hit.score})
            
            return memories
        except Exception as e:
            print(f"❌ Memory Retrieval Error: {e}")
            return []
