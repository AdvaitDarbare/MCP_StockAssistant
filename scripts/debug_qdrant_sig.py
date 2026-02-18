from qdrant_client import QdrantClient
import inspect

client = QdrantClient(host="localhost", port=6333)
print(inspect.signature(client.query_points))
print(inspect.signature(client.search)) if hasattr(client, 'search') else print("No search method")
