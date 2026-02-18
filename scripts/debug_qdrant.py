from qdrant_client import QdrantClient
import inspect

client = QdrantClient(host="localhost", port=6333)
print(f"QdrantClient methods: {[m for m in dir(client) if not m.startswith('_')]}")
