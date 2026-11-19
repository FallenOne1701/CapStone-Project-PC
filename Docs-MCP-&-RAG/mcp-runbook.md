# MCP runbook — Groww weekly pulse → Docs + Gmail draft

Checklist to publish a validated pulse artifact via **[MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1)** (Google Workspace MCP).

This path does **not** use `google-api-python-client`, LangChain Google toolkits, or custom Google OAuth in `pulse/`. Success for v1 is **Doc append + Gmail draft** — do **not** call `gmail_send_email` unless a human explicitly wants to send.

---

## Tool status (MCP-Server-1)

| Capability | MCP tool (MCP-Server-1) | Status |
|------------|-------------------------|--------|
| Publish pulse into Doc | `google_docs_append_content` | verified (local MCP HTTP dry-run 2026-11-18) |
| Create Gmail draft | `gmail_create_draft` | verified (local MCP HTTP dry-run 2026-11-18) |
| Send email | `gmail_send_email` | unused for v1 |

Update **Status** to `verified` after a successful dry-run (Step 2 below).

---

## 1. Prerequisites (one-time)

### 1.1 MCP-Server-1

1. Clone and install: [FallenOne1701/MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1)
2. In Google Cloud: enable **Gmail API** + **Google Docs API**; create OAuth client; set redirect `http://localhost:3000/oauth2callback` (or match `GOOGLE_REDIRECT_URI`)
3. Copy `.env.example` → `.env` in that repo; fill `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_TOKEN_STORAGE`
4. Authorize once: `npm run auth` (writes tokens; never commit them)
5. Build: `npm run build` (or use `npm run dev` for TypeScript)

### 1.2 Register in Cursor

Add to Cursor MCP settings (`mcpServers`), pointing at your local install (adjust paths):

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

Reload MCP / restart Cursor. Confirm tools appear: `google_docs_append_content`, `gmail_create_draft` (and `gmail_send_email`, unused here).

### 1.3 Pulse env

In `pulse/.env` (gitignored):

| Variable | Purpose |
|----------|---------|
| `PULSE_DOC_ID` | ID of a **pre-created** blank (or template) Google Doc. MCP appends only — it cannot create Docs. |
| `PULSE_DRAFT_TO` | Draft recipient (self or alias), e.g. `you@gmail.com` |

How to get `PULSE_DOC_ID`: open the Doc in Drive; ID is the path segment after `/d/` in  
`https://docs.google.com/document/d/<PULSE_DOC_ID>/edit`.

Also set in `pulse/.env.example` as placeholders (no real secrets).

---

## 2. Inputs (each week)

| Input | Source |
|-------|--------|
| Pulse markdown | Latest `pulse/out/pulse-YYYY-MM-DD.md` (from `python -m src.run_pulse` or Actions artifact) |
| `PULSE_DOC_ID` | `pulse/.env` |
| `PULSE_DRAFT_TO` | `pulse/.env` |
| Date label | `YYYY-MM-DD` from the pulse filename / title |

Optional: `pulse/out/themes.json` for run context — not required by MCP tools.

---

## 3. Steps (agent / human)

1. **Generate or download** the pulse (if not already done):
   ```bash
   cd pulse
   python -m src.run_pulse --sample   # or --live
   ```
2. **Read** `pulse/out/pulse-YYYY-MM-DD.md` into memory (full body).
3. **Append to Google Doc** — call MCP tool `google_docs_append_content`:
   - `document_id`: value of `PULSE_DOC_ID` (ID only, not a full URL)
   - `content`: optional dated heading + pulse body, e.g.  
     `Groww Weekly Review Pulse — YYYY-MM-DD\n\n` + file contents  
   - Optional: `add_newline_before` = `true` (default)
4. **Note Doc URL**: `https://docs.google.com/document/d/<PULSE_DOC_ID>/edit`
5. **Create Gmail draft** — call MCP tool `gmail_create_draft`:
   - `to`: `[ "<PULSE_DRAFT_TO>" ]` (array of emails)
   - `subject`: `Groww Weekly Review Pulse — YYYY-MM-DD`
   - `body`: full pulse text **or** short note + Doc URL from step 4  
   - Do **not** set HTML unless needed (`is_html` default false)
6. **Do not** call `gmail_send_email` for v1 success criteria. Human sends from Gmail if desired.

### Example payloads

`google_docs_append_content`:

```json
{
  "document_id": "<PULSE_DOC_ID>",
  "content": "Groww Weekly Review Pulse — 2026-11-18\n\n# Groww Weekly Review Pulse — 2026-11-18\n...",
  "add_newline_before": true
}
```

`gmail_create_draft`:

```json
{
  "to": ["you@example.com"],
  "subject": "Groww Weekly Review Pulse — 2026-11-18",
  "body": "Weekly pulse ready.\n\nDoc: https://docs.google.com/document/d/<PULSE_DOC_ID>/edit\n\n---\n<paste pulse markdown or leave Doc link only>"
}
```

---

## 4. Explicit non-goals

- No `google-api-python-client` (or equivalent) inside `pulse/` for this delivery path  
- No LangChain Google toolkits as the primary Docs/Gmail path  
- No auto-send (`gmail_send_email` unused for v1)  
- No Doc **create** via MCP — create the Doc once manually  

---

## 5. Verification checklist

After dry-run or weekly publish:

- [ ] Google Doc body shows the new append (`google_docs_append_content` success; `appended_characters` > 0)
- [ ] Gmail **Drafts** contains the message (`draft_id` returned); **not** sent automatically
- [ ] Subject / heading date matches the pulse file date
- [ ] No usernames, emails, or phones from reviews in the published body (auditor already enforced on `pulse/out/`)
- [ ] FAQ `frontend/` / `backend/` / `corpus_index` untouched

---

## 6. Dry-run record

| Field | Value |
|-------|-------|
| Date | 2026-11-18 |
| Pulse file | `pulse/out/pulse-2026-11-18.md` |
| `PULSE_DOC_ID` | set in `pulse/.env` (not committed) |
| Doc append | PASS — 859 characters appended to `PULSE_DOC_ID` |
| Gmail draft | PASS — `draft_id` created (not sent) |
| Notes | Local MCP-Server-1 HTTP after `npm run auth`. Doc: https://docs.google.com/document/d/1AqN2ubfts7Ub6SWPfRj8pIp_rLiVv7xk7x9Klhoa3VY/edit |

### Local auth (Railway is currently 404)

1. Create OAuth **Desktop** client in [Google Cloud Credentials](https://console.cloud.google.com/apis/credentials); enable Gmail API + Docs API.
2. Put `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` in `C:\Users\PC\Desktop\CapStone Project\MCP-Server-1\.env`.
3. In that folder: `npm run auth` (browser consent → writes `token.json`).
4. Reload Cursor MCP (Tools & MCP) so `google-workspace-local` connects.
5. Tell the agent to re-run: `python pulse/scripts/dry_run_mcp_delivery.py` **or** call the two MCP tools from chat.

---

## Related

- Pipeline CLI: [`pulse/README.md`](../pulse/README.md)
- Weekly Actions (artifacts only): [`weekly-actions.md`](weekly-actions.md)
- MCP server: https://github.com/FallenOne1701/MCP-Server-1
