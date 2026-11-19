# MCP runbook — Support Deck gated Docs + Gmail

Checklist to publish an **approved** Support Deck action via **[MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1)** (Google Workspace MCP).

Nothing is written or drafted until a human approves **that** `docs_append` or `gmail_draft` action. Reject never calls MCP. Reply finalize is a separate queue gate and does **not** use these tools.

Success for v1 is **Doc append + Gmail draft** — do **not** call `gmail_send_email` unless a human explicitly wants to send.

Sibling (pulse-only) checklist: [`Docs-MCP-&-RAG/mcp-runbook.md`](../Docs-MCP-&-RAG/mcp-runbook.md).

---

## Tool status (MCP-Server-1)

| Capability | MCP tool | Status |
|------------|----------|--------|
| Publish pulse into Doc | `google_docs_append_content` | verified (local MCP HTTP dry-run 2026-11-18; Support Deck bridge dry-run receipts) |
| Create Gmail draft | `gmail_create_draft` | verified (same) |
| Send email | `gmail_send_email` | unused for v1 |

---

## Modes

| Mode | How | Behavior |
|------|-----|----------|
| **Dry-run (default)** | `MCP_LIVE` unset/`0` | `ApprovalService.approve` → `mcp_bridge` writes a JSON receipt under `support-deck/data/fixtures/mcp-receipts/` with the exact tool name + arguments. No Google call. |
| **Live HTTP** | `MCP_LIVE=1` plus `MCP_URL` + `MCP_API_KEY` | Bridge calls MCP-Server-1 `tools/call` over HTTP (same shape as `pulse/scripts/dry_run_mcp_delivery.py`). Fails closed if `PULSE_DOC_ID` / `PULSE_DRAFT_TO` missing. |
| **Cursor chat tools** | Human / agent in Cursor with MCP registered | After approve (or instead of HTTP live), call the two tools below with the receipt/`payload_preview` values. |

---

## 1. Prerequisites (one-time)

### 1.1 MCP-Server-1

1. Clone and install: [FallenOne1701/MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1)
2. Google Cloud: enable **Gmail API** + **Google Docs API**; OAuth client; redirect matching `GOOGLE_REDIRECT_URI`
3. Copy `.env.example` → `.env` in that repo; fill client id/secret, redirect, token path
4. Authorize once: `npm run auth` (never commit tokens)
5. Build: `npm run build`

### 1.2 Register in Cursor

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "node",
      "args": ["C:/path/to/MCP-Server-1/dist/server.js"],
      "env": {
        "GOOGLE_CLIENT_ID": "your-client-id",
        "GOOGLE_CLIENT_SECRET": "your-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:3000/oauth2callback",
        "GOOGLE_TOKEN_STORAGE": "C:/path/to/MCP-Server-1/.tokens/google-token.json",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

Reload MCP. Confirm tools: `google_docs_append_content`, `gmail_create_draft` (`gmail_send_email` unused).

### 1.3 Support Deck env

In `support-deck/.env` (gitignored):

| Variable | Purpose |
|----------|---------|
| `PULSE_DOC_ID` | Pre-created Google Doc id (MCP cannot create Docs) |
| `PULSE_DRAFT_TO` | Draft recipient (self/alias) |
| `MCP_LIVE` | `0` dry-run receipts; `1` live HTTP |
| `MCP_URL` / `MCP_API_KEY` | Required only when `MCP_LIVE=1` |

How to get `PULSE_DOC_ID`: open the Doc; id is the segment after `/d/` in  
`https://docs.google.com/document/d/<PULSE_DOC_ID>/edit`.

---

## 2. Weekly path (Support Deck)

1. Run weekly (sample or live) so pending actions exist:
   ```bash
   # API
   curl -X POST "http://127.0.0.1:8001/api/support-deck/weekly/run?live=false"
   # or UI: Support Deck → Pulse → Prepare publish
   ```
2. Open **Approvals**. Confirm two pending actions: `docs_append`, `gmail_draft` with payload preview + destinations.
3. Optionally **edit** one action’s content; siblings must stay unchanged.
4. **Approve** Docs (then Gmail) — or reject either. Reject never publishes.
5. **Dry-run check:** open the newest file under `support-deck/data/fixtures/mcp-receipts/`. Confirm `tool` is `google_docs_append_content` or `gmail_create_draft` and `arguments` match the approved body.
6. **Live Cursor publish (optional):** copy arguments from the receipt (or Approvals panel) and call the MCP tools in chat (section 3).
7. Do **not** call `gmail_send_email` for v1 success.

---

## 3. Cursor / agent MCP tool calls

Only after the matching action is **approved** (or when intentionally replaying a dry-run receipt by hand).

### `google_docs_append_content`

```json
{
  "document_id": "<PULSE_DOC_ID>",
  "content": "<approved pulse body or edited_content>",
  "add_newline_before": true
}
```

### `gmail_create_draft`

```json
{
  "to": ["<PULSE_DRAFT_TO>"],
  "subject": "Groww Weekly Review Pulse — YYYY-MM-DD",
  "body": "Weekly pulse ready.\n\nDoc: https://docs.google.com/document/d/<PULSE_DOC_ID>/edit\n\n---\n<pulse body>"
}
```

---

## 4. Explicit non-goals

- No `google-api-python-client` inside `support-deck/` as the primary path  
- No LangChain Google toolkits as primary Docs/Gmail  
- No auto-send (`gmail_send_email` unused for v1)  
- No Doc **create** via MCP — create the Doc once manually  
- No publish on reject, and no Docs/Gmail tools for `reply_finalize`

---

## 5. Verification checklist

- [ ] Approving Docs writes a dry-run receipt **or** live append (`appended_characters` > 0)
- [ ] Approving Gmail writes a dry-run receipt **or** creates a Draft (`draft_id`); not sent
- [ ] Rejecting either action creates **no** receipt and no MCP call
- [ ] Editing/approving one action does not mutate the sibling
- [ ] Receipt / published body has no review PII (PAN/phone/email/account tokens)
- [ ] FAQ `/api/ask` and Support Deck queue still healthy

---

## 6. Dry-run record (template)

| Field | Value |
|-------|-------|
| Date | |
| Pulse / action ids | |
| Mode | dry-run receipt / MCP_LIVE / Cursor tools |
| Doc append | |
| Gmail draft | |
| Notes | |

---

## Related

- Bridge: `support-deck/src/mcp_bridge.py`
- Approval gate: `support-deck/src/approval/service.py`
- Architecture: [`Architecture.md`](./Architecture.md)
- MCP server: https://github.com/FallenOne1701/MCP-Server-1
