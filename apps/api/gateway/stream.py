import json
import re
import time
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from apps.api.agents.supervisor.graph import graph, GRAPH_RECURSION_LIMIT
from apps.api.agents.content_utils import normalize_content_to_text
from apps.api.services.mlflow_tracker import log_chat_trace_to_mlflow
from apps.api.services.report_orchestrator import orchestrate_report, orchestrate_report_followup, ReportRunOptions
from apps.api.services.report_engine import list_report_types

router = APIRouter()


def sanitize_uuid(uuid_str: str | None) -> str | None:
    """Sanitize UUID string by removing any prefixes and validating format."""
    if not uuid_str:
        return None
    
    # Remove any prefixes like 'conv-', 'user-', etc.
    if '-' in uuid_str and len(uuid_str) > 36:
        parts = uuid_str.split('-')
        if len(parts) >= 6:
            # Reconstruct UUID from parts (skip the first prefix part)
            uuid_parts = parts[1:]
            if len(uuid_parts) == 5:
                clean_uuid = '-'.join(uuid_parts)
                # Validate it's a proper UUID format (36 characters)
                if len(clean_uuid) == 36:
                    try:
                        # Validate it's a valid UUID
                        uuid.UUID(clean_uuid)
                        return clean_uuid
                    except ValueError:
                        pass
    
    # If it's already a proper UUID, validate and return it
    if len(uuid_str) == 36:
        try:
            uuid.UUID(uuid_str)
            return uuid_str
        except ValueError:
            pass
    
    # If we can't sanitize it, return None to generate a new one
    return None

class ChatRequest(BaseModel):
    messages: list
    model: str = "claude-3-5-sonnet-20240620"
    user_id: str | None = None
    tenant_id: str | None = None
    conversation_id: str | None = None
    report_followup: dict | None = None  # For report follow-up requests


def _extract_final_response(output) -> str:
    """Extract final response from LangGraph end event payloads."""
    if not output:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        # Common path: {"final_response": "..."}
        direct = output.get("final_response")
        if direct:
            return normalize_content_to_text(direct)
        # Nested path seen in compiled graph: {"aggregator": {"final_response": "..."}}
        aggr = output.get("aggregator")
        if isinstance(aggr, dict) and aggr.get("final_response"):
            return normalize_content_to_text(aggr.get("final_response"))
        # Fallback: scan nested dicts for first final_response-like key.
        for v in output.values():
            text = _extract_final_response(v)
            if text:
                return text
    return ""


def _extract_latest_user_query(messages: list) -> str:
    for msg in reversed(messages or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", "") or "")
        role = getattr(msg, "role", None)
        if role == "user":
            return str(getattr(msg, "content", "") or "")
        msg_type = getattr(msg, "type", None)
        if msg_type == "human":
            return str(getattr(msg, "content", "") or "")
    return ""


def _detect_report_request(user_query: str) -> tuple[str | None, dict]:
    """
    Detect if user query is requesting a specific report type.
    Returns (report_type, payload) or (None, {}) if not a report request.
    """
    query_lower = user_query.lower()
    
    # Report type patterns - ordered from most specific to least specific
    report_patterns = {
        "harvard_dividend": [
            r"harvard.*endowment",
            r"harvard.*dividend",
            r"managing.*harvard.*endowment",
            r"endowment.*dividend.*strategy",
            r"dividend.*focused.*strategy.*harvard",
        ],
        "citadel_technical": [
            r"citadel.*technical",
            r"citadel.*style",
            r"technical analysis.*citadel",
            r"senior.*quantitative.*trader.*citadel",
        ],
        "morgan_dcf": [
            r"morgan.*stanley.*dcf",
            r"morgan.*dcf",
            r"morgan.*stanley.*equity.*research",
            r"morgan.*stanley.*valuation",
        ],
        "bridgewater_risk": [
            r"bridgewater.*risk",
            r"bridgewater.*portfolio",
            r"bridgewater.*associates.*portfolio",
            r"bridgewater.*associates.*risk",
        ],
        "goldman_screener": [
            r"goldman.*sachs.*screen",
            r"goldman.*screen",
            r"goldman.*sachs.*equity.*research",
        ],
        "jpm_earnings": [
            r"jpmorgan.*earnings?",
            r"jpm.*earnings?",
            r"jpmorgan.*chase.*earnings",
        ],
        "blackrock_builder": [
            r"blackrock.*portfolio",
            r"blackrock.*builder",
            r"blackrock.*asset.*allocation",
        ],
        "bain_competitive": [
            r"bain.*competitive",
            r"bain.*company.*competitive",
        ],
        "renaissance_pattern": [
            r"renaissance.*pattern",
            r"renaissance.*technologies.*pattern",
        ],
        "mckinsey_macro": [
            r"mckinsey.*macro",
            r"mckinsey.*company.*macro",
        ],
        # Generic patterns (only if no institution mentioned)
        "citadel_technical_generic": [
            r"technical analysis",
            r"rsi.*macd",
            r"moving averages?",
            r"support.*resistance",
            r"fibonacci.*retracement",
            r"bollinger bands?",
            r"chart patterns?",
        ],
        "goldman_screener_generic": [
            r"stock screen",
            r"screen.*stocks?",
            r"find.*stocks?",
            r"growth.*stocks?.*screen",
        ],
        "morgan_dcf_generic": [
            r"dcf.*valuation",
            r"discounted.*cash.*flow",
            r"intrinsic.*value",
        ],
        "jpm_earnings_generic": [
            r"earnings?.*analysis",
            r"earnings?.*report",
        ],
        "blackrock_builder_generic": [
            r"portfolio.*builder?",
            r"build.*portfolio",
            r"asset.*allocation",
            r"moderate.*risk.*portfolio",
        ],
        "harvard_dividend_generic": [
            r"dividend.*strategy",
            r"dividend.*income",
            r"income.*portfolio",
            r"endowment.*dividend",
        ],
        "bain_competitive_generic": [
            r"competitive.*analysis",
            r"industry.*analysis",
            r"sector.*analysis",
            r"semiconductors?.*analysis",
        ],
        "renaissance_pattern_generic": [
            r"pattern.*finder?",
            r"find.*patterns?",
            r"quantitative.*patterns?",
        ],
        "mckinsey_macro_generic": [
            r"macro.*economic",
            r"economic.*impact",
            r"macro.*analysis",
        ],
        "bridgewater_risk_generic": [
            r"risk.*assessment",
            r"portfolio.*risk",
            r"risk.*analysis",
        ],
    }
    
    # Check for report type matches
    for report_type, patterns in report_patterns.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                # Extract ticker symbol if present - look for patterns like [TICKER] or "analyze: TICKER"
                ticker_match = None
                
                # First, look for ticker in brackets like [PLTR]
                bracket_match = re.search(r'\[([A-Z]{1,5})\]', user_query)
                if bracket_match:
                    ticker_match = bracket_match
                else:
                    # Look for ticker after "analyze:" or similar patterns
                    analyze_match = re.search(r'(?:analyze|stock|ticker|symbol):\s*\[?([A-Z]{1,5})\]?', user_query, re.IGNORECASE)
                    if analyze_match:
                        ticker_match = analyze_match
                    else:
                        # Look for standalone ticker symbols (but avoid single letters at start of sentences)
                        ticker_matches = re.findall(r'\b([A-Z]{2,5})\b', user_query)
                        if ticker_matches:
                            # Take the last match to avoid picking up words like "I" or "A"
                            ticker_match = type('Match', (), {'group': lambda self, n: ticker_matches[-1]})()
                
                payload = {}
                if ticker_match:
                    payload["ticker"] = ticker_match.group(1)
                
                # Extract sector for competitive analysis
                if report_type == "bain_competitive":
                    sector_words = ["tech", "technology", "semiconductor", "finance", "healthcare", "energy", "retail"]
                    for word in sector_words:
                        if word in query_lower:
                            payload["sector"] = word
                            break
                
                # Map generic patterns back to their base report types
                if report_type.endswith("_generic"):
                    report_type = report_type.replace("_generic", "")
                
                return report_type, payload
    
    return None, {}


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_query = _extract_latest_user_query(request.messages)
    
    # Handle report follow-up requests
    if request.report_followup:
        return await _handle_report_followup(request, user_query)
    
    # Detect new report requests
    report_type, report_payload = _detect_report_request(user_query)
    
    # If this is a report request, route to report orchestrator
    if report_type:
        return await _handle_report_request(request, report_type, report_payload, user_query)
    
    # Otherwise, handle as regular chat
    return await _handle_chat_request(request)


async def _handle_report_request(request: ChatRequest, report_type: str, report_payload: dict, user_query: str):
    """Handle report generation requests in chat format."""
    async def report_generator():
        conversation_id = sanitize_uuid(request.conversation_id) or str(uuid.uuid4())
        user_id = sanitize_uuid(request.user_id) or str(uuid.uuid4())
        
        started = time.perf_counter()
        
        try:
            # Indicate report generation is starting
            yield f"data: {json.dumps({'type': 'agent_start', 'agent': 'report_generator'})}\n\n"
            report_name = report_type.replace("_", " ").title()
            message = f'Generating {report_name} report...'
            yield f"data: {json.dumps({'type': 'token', 'content': message})}\n\n"
            
            # Generate the report
            options = ReportRunOptions(
                owner_key=user_id,
                thread_id=conversation_id,
                prompt_override=None,
                follow_up_question=None,
                refresh_data=False,
            )
            
            result = await orchestrate_report(report_type, report_payload, options)
            
            # Stream the report content
            markdown_content = result.get("markdown", "")
            if markdown_content:
                yield f"data: {json.dumps({'type': 'final', 'content': markdown_content})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to generate report'})}\n\n"
                
            yield f"data: {json.dumps({'type': 'agent_end', 'agent': 'report_generator'})}\n\n"
            
            # Add metadata about the report
            if result.get("thread_id"):
                yield f"data: {json.dumps({'type': 'report_metadata', 'thread_id': result['thread_id'], 'report_type': report_type})}\n\n"
                
        except Exception as exc:
            error_msg = f"Error generating report: {str(exc)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'final', 'content': error_msg})}\n\n"
        
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            yield f"data: {json.dumps({'type': 'trace_run', 'provider': 'report', 'duration_ms': duration_ms})}\n\n"
    
    return StreamingResponse(report_generator(), media_type="text/event-stream")


async def _handle_report_followup(request: ChatRequest, user_query: str):
    """Handle report follow-up requests in chat format."""
    async def followup_generator():
        followup_data = request.report_followup or {}
        report_type = followup_data.get("report_type")
        thread_id = followup_data.get("thread_id")
        owner_key = sanitize_uuid(request.user_id) or str(uuid.uuid4())
        
        if not report_type or not thread_id:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Missing report type or thread ID for follow-up'})}\n\n"
            return
        
        started = time.perf_counter()
        
        try:
            yield f"data: {json.dumps({'type': 'agent_start', 'agent': 'report_followup'})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': 'Processing follow-up question...'})}\n\n"
            
            result = await orchestrate_report_followup(
                report_type=report_type,
                owner_key=owner_key,
                thread_id=thread_id,
                question=user_query,
                refresh_data=followup_data.get("refresh_data", False)
            )
            
            # Stream the follow-up response
            markdown_content = result.get("markdown", "")
            if markdown_content:
                yield f"data: {json.dumps({'type': 'final', 'content': markdown_content})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to generate follow-up response'})}\n\n"
                
            yield f"data: {json.dumps({'type': 'agent_end', 'agent': 'report_followup'})}\n\n"
            
        except Exception as exc:
            error_msg = f"Error processing follow-up: {str(exc)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'final', 'content': error_msg})}\n\n"
        
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            yield f"data: {json.dumps({'type': 'trace_run', 'provider': 'report_followup', 'duration_ms': duration_ms})}\n\n"
    
    return StreamingResponse(followup_generator(), media_type="text/event-stream")


async def _handle_chat_request(request: ChatRequest):
    """Handle regular chat requests."""
    async def event_generator():
        conversation_id = sanitize_uuid(request.conversation_id) or str(uuid.uuid4())
        user_id = sanitize_uuid(request.user_id) or str(uuid.uuid4())
        tenant_id = request.tenant_id or f"tenant_{user_id}"

        # Initialize state
        initial_state = {
            "messages": request.messages,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "agent_results": {},
            "pending_agents": [],
            "task_status": {},
            "memory_context": []
        }
        started = time.perf_counter()
        trace_events: list[dict] = []
        route_agents: list[str] = []
        final_text = ""
        trace_error = None
        user_query = _extract_latest_user_query(request.messages)
        seen_task_status: dict[str, str] = {}

        def record(event_type: str, **details):
            entry = {
                "type": event_type,
                "t_ms": int((time.perf_counter() - started) * 1000),
            }
            entry.update(details)
            trace_events.append(entry)

        try:
            async for event in graph.astream_events(
                initial_state,
                version="v1",
                config={"recursion_limit": GRAPH_RECURSION_LIMIT},
            ):
                kind = event["event"]
                name = event["name"]

                # Agent Status Events
                agent_nodes = [
                    "market_data",
                    "technical_analysis",
                    "fundamentals",
                    "sentiment",
                    "advisor",
                    "macro",
                    "planner",
                    "router",
                ]

                if kind == "on_chain_start" and name in agent_nodes:
                    record("agent_start", agent=name)
                    yield f"data: {json.dumps({'type': 'agent_start', 'agent': name})}\n\n"

                elif kind == "on_chain_end" and name in agent_nodes:
                    record("agent_end", agent=name)
                    yield f"data: {json.dumps({'type': 'agent_end', 'agent': name})}\n\n"
                    output = (event.get("data") or {}).get("output") or {}
                    if isinstance(output, dict):
                        status_update = output.get("task_status")
                        if isinstance(status_update, dict):
                            for task_id, task_state in status_update.items():
                                if not task_id:
                                    continue
                                task_state_str = str(task_state)
                                if seen_task_status.get(task_id) == task_state_str:
                                    continue
                                seen_task_status[task_id] = task_state_str
                                record("task_update", task_id=str(task_id), status=task_state_str)
                                yield f"data: {json.dumps({'type': 'task_update', 'task_id': str(task_id), 'status': task_state_str})}\n\n"
                    if name == "planner":
                        plan = output.get("plan")
                        reasoning = ""
                        steps = []
                        if plan is not None:
                            reasoning = getattr(plan, "reasoning", "") or ""
                            plan_steps = getattr(plan, "steps", []) or []
                            for step in plan_steps:
                                agent = getattr(step, "agent", "")
                                query = getattr(step, "query", "")
                                task_id = getattr(step, "task_id", "")
                                depends_on = getattr(step, "depends_on", []) or []
                                if agent:
                                    steps.append(
                                        {
                                            "task_id": str(task_id),
                                            "agent": str(agent),
                                            "query": str(query),
                                            "depends_on": [str(dep) for dep in depends_on],
                                        }
                                    )
                        if reasoning or steps:
                            route_agents[:] = [s.get("agent", "") for s in steps if s.get("agent")]
                            record("decision", reasoning=reasoning, steps=steps)
                            payload = {
                                "type": "decision",
                                "reasoning": reasoning,
                                "steps": steps,
                            }
                            yield f"data: {json.dumps(payload)}\n\n"
                    elif isinstance(output, dict) and name in {"fundamentals", "sentiment"}:
                        # Surface tool usage from agent payloads (for agents not instrumented via LangChain tools).
                        agent_results = output.get("agent_results") or {}
                        agent_result = agent_results.get(name) if isinstance(agent_results, dict) else None
                        data = agent_result.get("data") if isinstance(agent_result, dict) else None
                        tool_results = data.get("tool_results") if isinstance(data, dict) else None
                        if isinstance(tool_results, list):
                            for tool_result in tool_results:
                                if not isinstance(tool_result, dict):
                                    continue
                                tool_name = str(tool_result.get("tool") or "").strip()
                                if not tool_name or tool_name == "text":
                                    continue
                                symbol = str(tool_result.get("symbol") or "").strip()
                                label = f"{tool_name}({symbol})" if symbol else tool_name
                                record("tool_end", tool=label)
                                yield f"data: {json.dumps({'type': 'tool_end', 'tool': label})}\n\n"

                elif kind == "on_chat_model_stream":
                    content = normalize_content_to_text(event["data"]["chunk"].content)
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                elif kind == "on_tool_start":
                    record("tool_start", tool=name)
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': name})}\n\n"
                elif kind == "on_tool_end":
                    record("tool_end", tool=name)
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': name})}\n\n"

                elif kind == "on_chain_end" and name == "LangGraph":
                    # Final output
                    output = event["data"].get("output")
                    final_text = _extract_final_response(output)
                    if final_text:
                        record("final", chars=len(final_text))
                        yield f"data: {json.dumps({'type': 'final', 'content': final_text})}\n\n"
        except Exception as exc:
            trace_error = str(exc)
            record("error", message=trace_error)
            yield f"data: {json.dumps({'type': 'error', 'message': trace_error})}\n\n"
            if not final_text:
                final_text = "I hit an internal error while running this analysis."
                yield f"data: {json.dumps({'type': 'final', 'content': final_text})}\n\n"
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            status = "error" if trace_error else ("ok" if final_text else "partial")
            mlflow_run = log_chat_trace_to_mlflow(
                user_query=user_query,
                final_text=final_text,
                events=trace_events,
                duration_ms=duration_ms,
                route_agents=route_agents,
                status=status,
                error=trace_error,
            )
            if mlflow_run.run_id:
                yield f"data: {json.dumps({'type': 'trace_run', 'provider': 'mlflow', 'run_id': mlflow_run.run_id})}\n\n"
                yield f"data: {json.dumps({'type': 'trace_link', 'url': 'http://127.0.0.1:5001'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")