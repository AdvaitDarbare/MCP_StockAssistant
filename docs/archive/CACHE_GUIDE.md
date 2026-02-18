# Redis Caching Guide

## Overview

The AI Stock Assistant uses Redis to cache market data, significantly improving response times and reducing API calls to external services (Schwab API, etc.).

## Architecture

```
User Query → Main API → Stock Agent → Check Redis → [Cache Hit/Miss]
                                                           ↓
                                        Cache Hit: Return cached data (fast)
                                        Cache Miss: Call Schwab API → Cache result → Return
```

## Cache Keys

Cache keys follow a hierarchical pattern:

```
stock:quote:{SYMBOL}                    # Single stock quote
stock:quotes:{AAPL,GOOGL,MSFT}         # Multiple quotes (sorted)
stock:history:{SYMBOL}:{params_hash}    # Price history
stock:movers:{index}:{sort}:{freq}      # Market movers
stock:hours:{markets}:{date}            # Market hours
```

## TTL Strategy (Time-To-Live)

Cache expiration varies based on:
1. **Data Type** - Different data changes at different rates
2. **Market Hours** - Real-time data gets shorter TTL during trading hours

### TTL Table

| Data Type          | Market Hours | After Hours | Rationale                          |
|--------------------|--------------|-------------|-------------------------------------|
| Stock Quote        | 15s          | 5min        | Price changes rapidly during trading|
| Price History      | 1 hour       | 1 hour      | Historical data doesn't change      |
| Company Overview   | 1 day        | 1 day       | Fundamental data changes slowly     |
| Analyst Ratings    | 1 day        | 1 day       | Updated periodically                |
| Insider Trades     | 1 day        | 1 day       | Filed daily at most                 |
| Company News       | 30 min       | 30 min      | News updates frequently             |
| Reddit Sentiment   | 5 min        | 5 min       | Social sentiment changes quickly    |
| Portfolio Holdings | 30s          | 30s         | User data needs to stay current     |
| Market Movers      | 1 min        | 5 min       | Rankings change during trading      |
| Market Hours       | 1 hour       | 1 hour      | Schedule doesn't change often       |

**Market Hours**: 9:30 AM - 4:00 PM ET

## API Endpoints

### Get Cache Statistics
```bash
GET /cache/stats
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "hits": 150,
    "misses": 50,
    "total_requests": 200,
    "hit_rate_percent": 75.0,
    "memory_used_mb": 12.5,
    "memory_peak_mb": 15.2
  }
}
```

### Invalidate Cache by Pattern
```bash
POST /cache/invalidate
Content-Type: application/json

{
  "pattern": "stock:quote:AAPL"
}
```

**Patterns:**
- `stock:quote:*` - Clear all quote caches
- `stock:history:AAPL:*` - Clear AAPL price history
- `stock:*` - Clear all stock data

**Response:**
```json
{
  "success": true,
  "message": "Invalidated cache keys matching: stock:quote:AAPL"
}
```

### Clear Entire Cache
```bash
DELETE /cache/clear
```

⚠️ **Warning**: This clears ALL cached data. Use with caution!

**Response:**
```json
{
  "success": true,
  "message": "Entire cache cleared successfully",
  "warning": "All services will need to rebuild cache from API calls"
}
```

### Check Cache Health
```bash
GET /cache/health
```

**Response:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "message": "Cache is operational"
}
```

## Testing Cache Performance

Run the test suite to verify caching works:

```bash
cd backend
python test_cache.py
```

**Expected Output:**
```
🧪 Redis Cache Test Suite

1️⃣  Testing Redis Health...
   ✅ Redis Status: connected

2️⃣  Clearing cache for clean test...
   ✅ Entire cache cleared successfully

3️⃣  Testing FIRST request (should be cache MISS)...
   ⏱️  Time: 1.85s
   📊 Expected: Slow (API call to Schwab)

4️⃣  Testing SECOND request (should be cache HIT)...
   ⏱️  Time: 0.12s
   📊 Expected: Fast (retrieved from Redis)

   🚀 Performance Improvement: 93.5% faster
   ✅ Cache is working! Second request was significantly faster.

5️⃣  Checking cache statistics...
   📈 Cache Hits: 1
   📉 Cache Misses: 1
   🎯 Hit Rate: 50.0%
   💾 Memory Used: 0.05 MB
```

## Manual Testing

### Test 1: Cache Miss (First Request)
```bash
curl -X POST http://localhost:8000/graph \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AAPL stock price?"}'
```

Check stock agent logs for:
```
🔄 Cache MISS - Fetched quote for AAPL from API
```

### Test 2: Cache Hit (Second Request)
```bash
# Same query again
curl -X POST http://localhost:8000/graph \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AAPL stock price?"}'
```

Check stock agent logs for:
```
💾 Cache HIT - Retrieved quote for AAPL from cache
```

### Test 3: Check Statistics
```bash
curl http://localhost:8000/cache/stats
```

### Test 4: Invalidate Cache
```bash
curl -X POST http://localhost:8000/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{"pattern": "stock:quote:*"}'
```

## Performance Metrics

### Expected Performance Improvement

| Request Type         | Uncached | Cached | Improvement |
|---------------------|----------|--------|-------------|
| Single Quote        | 1-2s     | 50ms   | 95%+        |
| Multiple Quotes     | 2-3s     | 80ms   | 95%+        |
| Price History       | 2-4s     | 100ms  | 95%+        |
| Market Movers       | 1-2s     | 60ms   | 95%+        |
| Complex Multi-Agent | 5-10s    | 1-2s   | 70-80%      |

### Cache Hit Rate Goals

- **After 1 hour of use**: 40-50%
- **After 1 day**: 60-70%
- **Steady state**: 70-80%

## Monitoring

### Check Health in Main API
```bash
curl http://localhost:8000/health
```

Look for cache section:
```json
{
  "services": {
    "cache": {
      "status": "connected",
      "type": "Redis",
      "stats": {
        "hits": 500,
        "misses": 200,
        "hit_rate_percent": 71.4
      }
    }
  }
}
```

### Check Individual Agent Health
```bash
curl http://localhost:8020/health  # Stock agent
```

Response includes cache stats:
```json
{
  "status": "healthy",
  "service": "stock_agent",
  "cache": {
    "status": "connected",
    "stats": { ... }
  }
}
```

## Troubleshooting

### Cache Not Working

**Symptom**: All requests are slow, no cache hits

**Check:**
1. Is Redis running?
   ```bash
   docker-compose ps redis
   ```

2. Can you connect to Redis?
   ```bash
   redis-cli -h localhost -p 6380 ping
   # Expected: PONG
   ```

3. Check cache health:
   ```bash
   curl http://localhost:8000/cache/health
   ```

4. Check logs for connection errors:
   ```bash
   grep -i redis logs/$(date +%Y-%m-%d)/app.log
   ```

### Cache Stale Data

**Symptom**: Seeing old prices or data

**Solution**: Invalidate specific cache keys
```bash
# Clear quotes for specific symbol
curl -X POST http://localhost:8000/cache/invalidate \
  -d '{"pattern": "stock:quote:AAPL"}'

# Clear all quotes
curl -X POST http://localhost:8000/cache/invalidate \
  -d '{"pattern": "stock:quote:*"}'
```

### Memory Usage Too High

**Symptom**: Redis using too much memory

**Check stats:**
```bash
curl http://localhost:8000/cache/stats
```

**Solution**: Clear old data
```bash
# Clear all cache
curl -X DELETE http://localhost:8000/cache/clear

# Or use Redis directly
redis-cli -h localhost -p 6380 FLUSHDB
```

### Cache Hit Rate Too Low

**Symptom**: Hit rate below 40% after warmup

**Possible causes:**
1. Users querying different stocks each time
2. TTL too short for query patterns
3. Cache getting cleared too often

**Solution**: Check query patterns in logs
```bash
grep "Cache HIT\|Cache MISS" logs/$(date +%Y-%m-%d)/app.log | \
  tail -100
```

## Configuration

Cache configuration is in `backend/app/cache/redis_cache.py`:

```python
# Adjust TTL values in get_ttl() method
def get_ttl(self, data_type: str) -> int:
    # Modify these values based on your needs
    ttl_map = {
        "quote": 15 if is_market_hours else 300,
        # ... other settings
    }
```

## Best Practices

1. **Monitor hit rate**: Aim for 60%+ in production
2. **Don't cache user-specific data for too long**: Portfolio data = 30s
3. **Invalidate strategically**: Clear only what changed, not everything
4. **Use patterns for bulk invalidation**: `stock:quote:*` not one-by-one
5. **Check health regularly**: Include in monitoring dashboard
6. **Log cache events**: Keep cache hit/miss logs for analysis

## Redis Configuration

Located in `docker-compose.yml`:

```yaml
redis:
  image: redis:7.4-alpine
  ports:
    - "6380:6379"  # External:Internal
  volumes:
    - redis-data:/data
  command: redis-server --appendonly yes
```

**Connection:**
- Host: `localhost` (or `REDIS_HOST` env var)
- Port: `6380` (or `REDIS_PORT` env var)
- No password (development only)

## Production Considerations

For production deployment:

1. **Add authentication**:
   ```yaml
   command: redis-server --requirepass your_password
   ```

2. **Enable persistence**:
   ```yaml
   command: redis-server --appendonly yes --save 60 1000
   ```

3. **Set memory limits**:
   ```yaml
   command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
   ```

4. **Use Redis Cluster** for high availability

5. **Monitor with Redis Insights** or similar tools

6. **Set up alerts** for:
   - Memory usage > 80%
   - Hit rate < 40%
   - Connection errors

## Summary

The Redis caching layer provides:
- ✅ **95%+ faster response times** for cached data
- ✅ **Reduced API costs** by minimizing external calls
- ✅ **Better user experience** with instant responses
- ✅ **Smart TTL strategy** based on data freshness needs
- ✅ **Easy monitoring** via health checks and statistics
- ✅ **Flexible invalidation** for cache management

Cache is now fully integrated into the Stock Agent and ready for production use!
