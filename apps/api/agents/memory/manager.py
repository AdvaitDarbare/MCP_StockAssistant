from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from apps.api.agents.memory.vector_store import VectorStore

class MemoryManager:
    def __init__(self):
        self.vector_store = VectorStore()
        
    async def get_relevant_context(
        self,
        query: str,
        k: int = 3,
        user_id: str | None = None,
        tenant_id: str | None = None,
        conversation_id: str | None = None,
    ) -> List[Dict]:
        """Retrieve relevant context for a given query."""
        scoped_filter: dict[str, str] = {}
        if tenant_id:
            scoped_filter["tenant_id"] = tenant_id
        if user_id:
            scoped_filter["user_id"] = user_id
        if conversation_id:
            scoped_filter["conversation_id"] = conversation_id

        docs = []
        if scoped_filter:
            docs = self.vector_store.similarity_search(query, k=k, filter=scoped_filter)
            # Back off from conversation to tenant/user scope if thread-specific context is empty.
            if not docs and "conversation_id" in scoped_filter:
                broader = dict(scoped_filter)
                broader.pop("conversation_id", None)
                if broader:
                    docs = self.vector_store.similarity_search(query, k=k, filter=broader)
        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]

    async def save_interaction(self, user_input: str, agent_output: str, metadata: Dict[str, Any] = None):
        """Save a user-agent interaction to memory."""
        # Keep memory compact to reduce retrieval token overhead.
        u = (user_input or "").strip()
        a = (agent_output or "").strip()
        if len(u) > 500:
            u = u[:500] + "..."
        if len(a) > 1800:
            a = a[:1800] + "..."

        content = f"User: {u}\nAssistant: {a}"
        
        doc = Document(
            page_content=content,
            metadata=metadata or {}
        )
        
        self.vector_store.add_documents([doc])
