from fastapi import APIRouter, HTTPException

from apps.api.services.tool_contracts import get_tool_contract, list_tool_contracts

router = APIRouter()


@router.get("/tools/contracts")
async def tool_contracts():
    """List available tool contracts and Schwab endpoint references."""
    return list_tool_contracts()


@router.get("/tools/contracts/{tool_name}")
async def tool_contract(tool_name: str):
    """Get a single tool contract by name."""
    contract = get_tool_contract(tool_name)
    if not contract:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    return contract
