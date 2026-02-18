#!/usr/bin/env python3
"""Generate Schwab API reference docs from the downloaded PDF + local contracts."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import re
import sys

try:
    from pypdf import PdfReader
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: pypdf. Run with a Python env that has pypdf installed "
        "(e.g. system python on this machine), and set PYTHONPATH=. if needed."
    ) from exc

# Ensure project-local imports resolve when script is run directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.services.tool_contracts import (
    SCHWAB_MARKET_DATA_ENDPOINTS,
    SCHWAB_TRADER_ENDPOINTS,
    TOOL_CONTRACTS,
)


PDF_PATH = Path("/Users/advaitdarbare/Downloads/Trader API - Individual | Products | Charles Schwab Developer Portal.pdf")
OUT_PATH = Path("/Users/advaitdarbare/Documents/ai-stock-assistant/docs/SCHWAB_API_REFERENCE.md")


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_schema_names(text: str) -> list[str]:
    idx = text.find("Schemas")
    if idx < 0:
        return []
    tail = text[idx:]
    end = tail.find("Terms Of Use")
    if end > 0:
        tail = tail[:end]

    out: list[str] = []
    for line in tail.splitlines():
        value = line.strip()
        if not value:
            continue
        if "Page " in value or "http" in value:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]+", value):
            continue
        if value in {"Schemas", "Example", "Value", "Code", "Description", "Links"}:
            continue
        if value not in out:
            out.append(value)
    return out


def _present_in_pdf(text: str, endpoint_path: str) -> bool:
    normalized = " ".join(text.split())
    if endpoint_path in normalized:
        return True
    plain = endpoint_path.replace("{symbol_id}", "").replace("{market_id}", "").replace("{cusip_id}", "")
    if plain in normalized:
        return True
    # Fallback for line-break split patterns seen in PDF extraction.
    if endpoint_path == "/{symbol_id}/quotes":
        return "/{symbol_id}" in normalized and "/quotes" in normalized
    if endpoint_path == "/movers/{symbol_id}":
        return "/movers" in normalized and "symbol_id" in normalized
    if endpoint_path == "/markets/{market_id}":
        return "/markets" in normalized and "market_id" in normalized
    if endpoint_path == "/instruments/{cusip_id}":
        return "/instruments" in normalized and "cusip_id" in normalized
    return False


def _tool_contract_rows() -> list[str]:
    rows = []
    for tool_name in sorted(TOOL_CONTRACTS.keys()):
        contract = TOOL_CONTRACTS[tool_name]
        source = contract.get("source", "")
        endpoint = contract.get("endpoint", "")
        fields = contract.get("output_fields", [])
        fields_text = ", ".join(fields[:6]) + (" ..." if len(fields) > 6 else "")
        rows.append(f"| `{tool_name}` | `{source}` | `{endpoint}` | `{fields_text}` |")
    return rows


def main() -> None:
    extracted = _extract_text(PDF_PATH)
    schema_names = _extract_schema_names(extracted)
    generated_at = datetime.now(timezone.utc).isoformat()

    lines: list[str] = []
    lines.append("# Schwab API Reference")
    lines.append("")
    lines.append(f"- Source PDF: `{PDF_PATH}`")
    lines.append(f"- Generated (UTC): `{generated_at}`")
    lines.append("- Generator: `PYTHONPATH=. python3 scripts/generate_schwab_reference.py`")
    lines.append("- Notes: Market Data endpoints are parsed from the PDF. Trader endpoints are listed from implemented integration scope.")
    lines.append("")
    lines.append("## Market Data Endpoints (from PDF)")
    lines.append("")
    lines.append("| Method | Path | Summary | Found in PDF text |")
    lines.append("|---|---|---|---|")
    for endpoint in SCHWAB_MARKET_DATA_ENDPOINTS:
        found = "yes" if _present_in_pdf(extracted, endpoint["path"]) else "no"
        lines.append(f"| `{endpoint['method']}` | `{endpoint['path']}` | {endpoint['summary']} | {found} |")
    lines.append("")
    lines.append("## Trader Endpoints (implemented)")
    lines.append("")
    lines.append("| Method | Path | Summary |")
    lines.append("|---|---|---|")
    for endpoint in SCHWAB_TRADER_ENDPOINTS:
        lines.append(f"| `{endpoint['method']}` | `{endpoint['path']}` | {endpoint['summary']} |")
    lines.append("")
    lines.append("## Tool to Output Contracts")
    lines.append("")
    lines.append("| Tool | Source | Endpoint | Output fields (projected) |")
    lines.append("|---|---|---|---|")
    lines.extend(_tool_contract_rows())
    lines.append("")
    lines.append("## PDF Schema Names (extracted)")
    lines.append("")
    if schema_names:
        for name in schema_names:
            lines.append(f"- `{name}`")
    else:
        lines.append("- No schema names could be extracted from the PDF text.")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
