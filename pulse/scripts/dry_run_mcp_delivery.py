"""Dry-run Task 8: append pulse to Google Doc + create Gmail draft via MCP-Server-1 HTTP."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

PULSE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PULSE_ROOT / ".env")

MCP_URL = os.environ.get("MCP_URL", "").rstrip("/")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
DOC_ID = os.environ.get("PULSE_DOC_ID", "")
DRAFT_TO = os.environ.get("PULSE_DRAFT_TO", "")


def _rpc(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    if not MCP_URL or not MCP_API_KEY:
        raise SystemExit("Set MCP_URL and MCP_API_KEY in pulse/.env")
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        MCP_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {MCP_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} from MCP: {err_body[:500]}") from e
    # Streamable HTTP may return SSE lines or plain JSON
    if raw.startswith("event:") or "data:" in raw.splitlines()[0:1]:
        payloads = []
        for line in raw.splitlines():
            if line.startswith("data:"):
                payloads.append(line[5:].strip())
        raw = payloads[-1] if payloads else raw
    return json.loads(raw)


def main() -> int:
    out_dir = PULSE_ROOT / "out"
    pulses = sorted(out_dir.glob("pulse-*.md"))
    if not pulses:
        raise SystemExit(f"No pulse-*.md under {out_dir}")
    pulse_path = pulses[-1]
    pulse_body = pulse_path.read_text(encoding="utf-8")
    date = pulse_path.stem.replace("pulse-", "")
    print(f"Pulse: {pulse_path.name}")
    print(f"Doc ID set: {bool(DOC_ID)}  Draft to set: {bool(DRAFT_TO)}")

    # Health via parent /health
    health_url = MCP_URL.rsplit("/mcp", 1)[0] + "/health"
    try:
        with urllib.request.urlopen(health_url, timeout=20) as resp:
            print("Health:", resp.read().decode("utf-8")[:200])
    except Exception as e:  # noqa: BLE001
        print("Health check failed:", e)
        return 2

    init = _rpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pulse-dry-run", "version": "0.1"},
        },
        req_id=1,
    )
    print("initialize:", json.dumps(init)[:300])

    content = f"Groww Weekly Review Pulse — {date}\n\n{pulse_body}"
    docs = _rpc(
        "tools/call",
        {
            "name": "google_docs_append_content",
            "arguments": {
                "document_id": DOC_ID,
                "content": content,
                "add_newline_before": True,
            },
        },
        req_id=2,
    )
    print("docs append:", json.dumps(docs)[:500])

    draft = _rpc(
        "tools/call",
        {
            "name": "gmail_create_draft",
            "arguments": {
                "to": [DRAFT_TO],
                "subject": f"Groww Weekly Review Pulse — {date}",
                "body": (
                    f"Weekly pulse ready.\n\n"
                    f"Doc: https://docs.google.com/document/d/{DOC_ID}/edit\n\n"
                    f"---\n{pulse_body}"
                ),
            },
        },
        req_id=3,
    )
    print("gmail draft:", json.dumps(draft)[:500])
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
