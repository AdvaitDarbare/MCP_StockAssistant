# Operations

## Start Services

### Backend

```bash
cd /Users/advaitdarbare/Documents/ai-stock-assistant
./.venv/bin/python -m uvicorn apps.api.gateway.main:app --host 127.0.0.1 --port 8001
```

### Frontend

```bash
cd /Users/advaitdarbare/Documents/ai-stock-assistant/apps/web
npm run dev
```

### MLflow UI

```bash
cd /Users/advaitdarbare/Documents/ai-stock-assistant
./.venv/bin/mlflow ui --backend-store-uri file:./mlruns --host 127.0.0.1 --port 5001
```

## Smoke Checks

```bash
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/api/tools/contracts | jq '.tools | keys'
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3001/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3001/reports
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3001/integrations/schwab
```

## Quality Checks

### Frontend lint (targeted)

```bash
cd /Users/advaitdarbare/Documents/ai-stock-assistant/apps/web
npm run lint -- src/app/page.tsx src/hooks/use-supervisor-chat.ts
```

### Backend compile smoke

```bash
cd /Users/advaitdarbare/Documents/ai-stock-assistant
python3 -m compileall apps/api
```

## Tracing

- Chat traces: MLflow experiment `ai-stock-assistant-chat`
- Report traces: MLflow experiment `ai-stock-assistant-reports`
- In-app trace: chat decision panel and reports orchestration trace

## Schwab Reference Refresh

```bash
cd /Users/advaitdarbare/Documents/ai-stock-assistant
PYTHONPATH=. python3 scripts/generate_schwab_reference.py
```

## Safety Flags

- `ENABLE_LIVE_TRADING=false` (recommended default)
- `REQUIRE_HITL_FOR_TRADES=true` (required)
