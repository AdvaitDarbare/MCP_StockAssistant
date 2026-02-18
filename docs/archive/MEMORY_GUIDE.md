# Qdrant Vector Memory Guide

## Overview

The AI Stock Assistant now has **conversation memory** using Qdrant vector database. The system remembers past stock analysis, retrieves relevant context automatically, and provides smarter recommendations that build on previous research.

---

## Architecture

```
User Query → Router → Advisor Agent
                          ↓
                    [Memory Retrieval]
                    Search Qdrant for relevant
                    past conversations
                          ↓
                    Include context in
                    investment advice
                          ↓
               Response → Synthesizer
                          ↓
                    [Memory Storage]
                    Store conversation +
                    embeddings in Qdrant
```

---

## What Was Built

### 1. ConversationMemory Class (`backend/app/memory/qdrant_memory.py`)

**Features:**
- Semantic search using FastEmbed (BAAI/bge-small-en-v1.5, 384-dim vectors)
- User-scoped storage (only retrieve your own conversations)
- Symbol tracking for better context retrieval
- Chronological access to recent conversations
- Automatic embedding generation

**Key Methods:**
```python
await memory.store_conversation(
    user_id="testuser",
    thread_id="thread-123",
    query="What's AAPL price?",
    response="AAPL: $230.85...",
    metadata={
        "symbols": ["AAPL"],
        "agents_used": ["stock", "advisor"],
        "timestamp": "2024-01-15T10:30:00"
    }
)

results = await memory.search_similar(
    user_id="testuser",
    query="Should I invest more in Apple?",
    limit=3,
    score_threshold=0.7  # Only 70%+ similar
)

recent = await memory.get_recent_conversations(
    user_id="testuser",
    limit=10
)
```

### 2. Symbol Extraction Utility (`backend/app/utils/symbol_extraction.py`)

**Extracts stock symbols from text:**
- Pattern matching: `$AAPL`, `AAPL:`, `"AAPL"`
- Known symbol detection: AAPL, TSLA, GOOGL, etc.
- Company name mapping: Apple → AAPL

```python
from app.utils.symbol_extraction import extract_symbols_from_text

symbols = extract_symbols_from_text("Compare $AAPL with TSLA")
# Returns: ['AAPL', 'TSLA']

symbols = extract_symbols_from_results({
    "stock": "AAPL: $230.85",
    "advisor": "AAPL shows strong growth..."
})
# Returns: ['AAPL']
```

### 3. Memory API Endpoints (`backend/app/api/memory.py`)

**Endpoints:**

1. **POST /memory/search** - Semantic search
   ```bash
   curl -X POST http://localhost:8000/memory/search \
     -d '{"user_id": "testuser", "query": "Apple analysis", "limit": 3}'
   ```

2. **GET /memory/recent/{user_id}** - Recent conversations
   ```bash
   curl http://localhost:8000/memory/recent/testuser?limit=5
   ```

3. **POST /memory/store** - Manually store conversation
   ```bash
   curl -X POST http://localhost:8000/memory/store \
     -d '{
       "user_id": "testuser",
       "thread_id": "thread-1",
       "query": "AAPL price?",
       "response": "AAPL: $230.85",
       "metadata": {"symbols": ["AAPL"]}
     }'
   ```

4. **DELETE /memory/clear/{user_id}** - Clear all user memory
   ```bash
   curl -X DELETE http://localhost:8000/memory/clear/testuser
   ```

5. **GET /memory/health** - Check Qdrant connectivity
   ```bash
   curl http://localhost:8000/memory/health
   ```

6. **GET /memory/stats** - Collection statistics
   ```bash
   curl http://localhost:8000/memory/stats
   ```

### 4. Synthesizer Integration

**After synthesizing responses, stores conversation automatically:**

```python
# In synthesizer_node.py
memory = get_memory()

await memory.store_conversation(
    user_id=state.get("user_id", "testuser"),
    thread_id=state.get("thread_id", str(uuid4())),
    query=user_input,
    response=final_output,
    metadata={
        "symbols": extract_symbols_from_results(accumulated_results),
        "agents_used": list(accumulated_results.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }
)
```

### 5. Advisor Integration

**Before generating advice, retrieves relevant past research:**

```python
# In advisor_agent.py
memory = get_memory()

past_analysis = await memory.search_similar(
    user_id="testuser",
    query=user_query,
    limit=3,
    score_threshold=0.7
)

if past_analysis:
    memory_context = "\n\n📚 **RELEVANT PAST ANALYSIS:**\n"
    for item in past_analysis:
        memory_context += f"[{item['timestamp']}] {item['symbols']}\n"
        memory_context += f"Q: {item['query']}\nA: {item['response'][:200]}...\n"

# Include in LLM prompt
advice_prompt = f"""...
{memory_context}
..."""
```

### 6. GraphState Updates

**Added memory fields:**
```python
class GraphState(TypedDict):
    input: str
    route: str
    output: str
    pending_tasks: List[str]
    accumulated_results: Dict[str, str]
    user_id: Optional[str]  # NEW
    thread_id: Optional[str]  # NEW
    memory_context: Optional[List[dict]]  # NEW
```

### 7. Main.py Enhancements

**Startup event:**
```python
@app.on_event("startup")
async def startup_event():
    mem = get_memory()
    await mem.setup_collection()
    logger.info("✅ Qdrant conversation memory initialized")
```

**Health check includes Qdrant:**
```json
{
  "services": {
    "qdrant": {
      "status": "connected",
      "type": "Qdrant Vector DB",
      "stats": {
        "total_conversations": 42,
        "vector_size": 384,
        "distance_metric": "cosine"
      }
    }
  }
}
```

---

## How Memory Works

### Storage Flow

1. **User asks a question** → "Analyze AAPL stock"
2. **System processes** → Router → Stock Agent → Advisor → Synthesizer
3. **Synthesizer stores conversation**:
   - Combines query + response
   - Generates 384-dim embedding using FastEmbed
   - Stores in Qdrant with metadata (symbols, agents, timestamp)
   - Saves to collection: `stock_conversations`

### Retrieval Flow

1. **User asks related question** → "Should I buy more Apple?"
2. **Advisor agent retrieves memory**:
   - Generates embedding for new query
   - Searches Qdrant with cosine similarity
   - Filters by user_id (user-scoped)
   - Returns top 3 matches above 70% similarity
3. **Advisor includes context in prompt**:
   - Shows past analysis to LLM
   - LLM builds on previous research
   - Provides continuity and avoids repetition

---

## Example Usage

### Scenario: Repeated Analysis

**First Query:**
```bash
curl -X POST http://localhost:8000/graph \
  -d '{"query": "Analyze AAPL stock for investment"}'
```

**Response:**
```
🎯 Investment Recommendation
💚 BUY - Confidence: High (8/10)
...detailed analysis...
```

**Stored in Memory:**
- Query: "Analyze AAPL stock for investment"
- Response: Full analysis
- Symbols: ["AAPL"]
- Agents: ["stock", "advisor"]
- Vector: [0.123, -0.456, ...] (384 dimensions)

**Second Query (days later):**
```bash
curl -X POST http://localhost:8000/graph \
  -d '{"query": "Should I buy more AAPL?"}'
```

**Advisor Retrieves Memory:**
```
📚 RELEVANT PAST ANALYSIS:
[1] 2024-01-15T10:30:00 | Symbols: ['AAPL'] | Relevance: 0.89
Previous Q: Analyze AAPL stock for investment
Previous A: 🎯 Investment Recommendation - BUY - Confidence: High (8/10)...
```

**Response:**
```
🎯 Investment Recommendation

Based on your previous analysis 3 days ago where we recommended BUY at $230...

Current price: $234.50 (+1.9% since analysis)
Your timing was good! The stock has appreciated...

💡 Adding to Position:
Given your existing analysis and current momentum...
```

---

## Testing

### 1. Verify Qdrant Running
```bash
docker-compose ps qdrant
curl http://localhost:6333/collections
# Should return: {"result": {"collections": []}}
```

### 2. Check Health
```bash
curl http://localhost:8000/health

# Expected:
{
  "services": {
    "qdrant": {
      "status": "connected",
      "type": "Qdrant Vector DB"
    }
  }
}
```

### 3. Store First Conversation
```bash
curl -X POST http://localhost:8000/graph \
  -d '{"query": "What is AAPL stock price and should I buy it?"}'
```

Check collection created:
```bash
curl http://localhost:6333/collections/stock_conversations
```

### 4. Search Memory
```bash
curl -X POST http://localhost:8000/memory/search \
  -d '{"user_id": "testuser", "query": "Apple stock", "limit": 3}'
```

Expected:
```json
{
  "success": true,
  "results": [
    {
      "query": "What is AAPL stock price...",
      "response": "📈 Stock Information: AAPL: $230.85...",
      "symbols": ["AAPL"],
      "timestamp": "2024-01-15T10:30:00",
      "similarity_score": 0.92
    }
  ],
  "count": 1
}
```

### 5. Test Context Retrieval
```bash
# First query
curl -X POST http://localhost:8000/graph \
  -d '{"query": "Analyze Tesla stock"}'

# Related query - should recall previous analysis
curl -X POST http://localhost:8000/graph \
  -d '{"query": "Should I invest in Tesla?"}'
```

Check advisor logs for:
```
Retrieved 1 relevant past conversations for advisor
```

### 6. Get Recent Conversations
```bash
curl http://localhost:8000/memory/recent/testuser?limit=5
```

### 7. Clear Memory (Testing)
```bash
curl -X DELETE http://localhost:8000/memory/clear/testuser
```

---

## Configuration

### Environment Variables

Add to `.env`:
```bash
# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=stock_conversations

# Default user (until auth added)
DEFAULT_USER_ID=testuser
```

### Qdrant Collection Settings

- **Collection Name**: `stock_conversations`
- **Vector Size**: 384 (FastEmbed BAAI/bge-small-en-v1.5)
- **Distance Metric**: Cosine similarity
- **Payload Schema**:
  ```python
  {
      "user_id": str,
      "thread_id": str,
      "query": str,
      "response": str,
      "symbols": List[str],
      "agents_used": List[str],
      "timestamp": str (ISO 8601)
  }
  ```

---

## Monitoring

### Memory Stats
```bash
curl http://localhost:8000/memory/stats
```

Response:
```json
{
  "collection_name": "stock_conversations",
  "total_conversations": 156,
  "vector_size": 384,
  "distance_metric": "cosine",
  "status": "healthy"
}
```

### System Health
```bash
curl http://localhost:8000/health
```

Check `services.qdrant` section for memory status.

### Logs

Memory operations are logged with loguru:
```
[INFO] Stored conversation in memory: Analyze AAPL stock... → symbols: ['AAPL']
[INFO] Retrieved 2 relevant past conversations for advisor
[WARNING] Failed to retrieve memory context: Connection refused
```

---

## Troubleshooting

### Memory Not Working

**Symptom**: Advisor doesn't mention past analysis

**Check:**
1. Is Qdrant running?
   ```bash
   docker-compose ps qdrant
   ```

2. Is collection created?
   ```bash
   curl http://localhost:6333/collections/stock_conversations
   ```

3. Are conversations being stored?
   ```bash
   curl http://localhost:8000/memory/stats
   # Check total_conversations > 0
   ```

4. Check logs:
   ```bash
   grep -i "memory" logs/$(date +%Y-%m-%d)/app.log
   ```

### Low Similarity Scores

**Symptom**: Memory search returns no results even with related queries

**Solution**: Lower score_threshold
```python
# In advisor_agent.py
past_analysis = await memory.search_similar(
    user_id=user_id,
    query=user_query,
    limit=3,
    score_threshold=0.6  # Lower from 0.7 to 0.6
)
```

### Collection Not Found

**Error**: `Collection 'stock_conversations' not found`

**Solution**: Restart main API to trigger startup event
```bash
# Kill and restart
uvicorn app.main:app --reload --port 8000
```

Or manually initialize:
```bash
curl -X POST http://localhost:8000/memory/store \
  -d '{"user_id": "testuser", "thread_id": "1", "query": "test", "response": "test"}'
```

---

## Best Practices

1. **User Scoping**: Always filter by user_id for privacy
2. **Score Threshold**: Use 0.7 for high-quality matches, 0.6 for broader recall
3. **Limit Results**: Typically 3-5 past conversations is enough context
4. **Truncate Responses**: Only include first 200 chars of past responses in prompts
5. **Graceful Degradation**: Continue even if memory retrieval fails
6. **Symbol Tracking**: Always extract and store symbols for better retrieval
7. **Timestamps**: Include timestamps for temporal context

---

## Future Enhancements

Potential improvements for Phase 3:

1. **Time-based Weighting**: Boost recent conversations in search results
2. **Symbol-specific Collections**: Separate collection per stock symbol
3. **Conversation Threading**: Link related conversations with thread_id
4. **Memory Pruning**: Auto-delete conversations older than N days
5. **Hybrid Search**: Combine vector similarity with keyword matching
6. **Multi-user Support**: Full JWT authentication with user isolation
7. **Memory Dashboard**: UI to view/search/manage stored conversations
8. **Export/Import**: Backup and restore conversation history

---

## Performance

### Memory Footprint

- **Per Conversation**: ~1KB (384-float vector + metadata)
- **1000 Conversations**: ~1MB
- **100K Conversations**: ~100MB

### Search Speed

- **Cosine similarity search**: <50ms for 100K vectors
- **With user_id filter**: <10ms (indexed)
- **Embedding generation**: ~20ms per query

### Scalability

- Qdrant handles **millions of vectors** efficiently
- User-scoped search maintains fast performance
- Consider sharding by user_id for >1M users

---

## Summary

Phase 2.4 adds intelligent conversation memory:

✅ **Store**: Every conversation → Qdrant with embeddings
✅ **Search**: Semantic similarity search with user scoping
✅ **Retrieve**: Advisor recalls relevant past analysis
✅ **Context**: Smarter recommendations building on history
✅ **API**: Full management endpoints for memory ops
✅ **Health**: Integrated health checks and monitoring

The AI Stock Assistant now remembers what you've asked before and provides context-aware advice!

🎉 **Phase 2.4 Complete!** 🎉
