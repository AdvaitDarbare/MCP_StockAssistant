from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apps.api.services.report_engine import list_report_types
from apps.api.services.report_orchestrator import (
    ReportRunOptions,
    orchestrate_report,
    orchestrate_report_followup,
)
from apps.api.services.report_prompts import PROMPT_TEMPLATES
from apps.api.services.report_templates import (
    list_templates,
    reset_template_override,
    save_template_override,
)

router = APIRouter()


class ReportRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    owner_key: str | None = None
    prompt_override: str | None = None
    thread_id: str | None = None
    follow_up_question: str | None = None
    refresh_data: bool = False


class TemplateUpdateRequest(BaseModel):
    owner_key: str
    prompt_text: str


class FollowupRequest(BaseModel):
    owner_key: str
    thread_id: str
    question: str
    refresh_data: bool = False


@router.get("/reports/types")
async def get_report_types():
    return {"types": list_report_types()}


@router.get("/reports/templates")
async def get_report_templates(owner_key: str = Query(..., description="Per-user owner key")):
    try:
        return {"templates": await list_templates(owner_key)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/reports/templates/{report_type}")
async def update_report_template(report_type: str, request: TemplateUpdateRequest):
    try:
        return await save_template_override(
            owner_key=request.owner_key,
            report_type=report_type,
            prompt_text=request.prompt_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/reports/templates/{report_type}")
async def delete_report_template(report_type: str, owner_key: str = Query(..., description="Per-user owner key")):
    try:
        return await reset_template_override(owner_key=owner_key, report_type=report_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/{report_type}/prompt")
async def get_report_prompt(report_type: str):
    rt = report_type.strip().lower()
    if rt not in PROMPT_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Unknown report type '{report_type}'.")
    meta = PROMPT_TEMPLATES[rt]
    return {"id": rt, "title": meta["title"], "prompt_template": meta["prompt"]}


@router.post("/reports/{report_type}")
async def run_report(report_type: str, request: ReportRequest):
    try:
        return await orchestrate_report(
            report_type,
            request.payload,
            options=ReportRunOptions(
                owner_key=request.owner_key,
                prompt_override=request.prompt_override,
                thread_id=request.thread_id,
                follow_up_question=request.follow_up_question,
                refresh_data=request.refresh_data,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.post("/reports/{report_type}/followup")
async def followup_report(report_type: str, request: FollowupRequest):
    try:
        return await orchestrate_report_followup(
            report_type=report_type,
            owner_key=request.owner_key,
            thread_id=request.thread_id,
            question=request.question,
            refresh_data=request.refresh_data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run follow-up: {str(e)}")
