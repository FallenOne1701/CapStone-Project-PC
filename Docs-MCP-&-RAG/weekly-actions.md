# Weekly pulse via GitHub Actions

Thin ops layer on top of `python -m src.run_pulse --live`. CI writes artifacts only; Docs/Gmail stay manual via MCP.

## Secret

| Name | Where | Value |
|------|--------|--------|
| `GROQ_API_KEY` | Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** | Same Groq key as `pulse/.env` ([console.groq.com](https://console.groq.com/)) |

Optional repo **Variables** (not secrets): `PULSE_LOOKBACK_WEEKS`, `PULSE_MAX_REVIEWS`, `GROQ_CHAT_MODEL`. If unset, workflow uses Settings defaults.

## Run

1. Ensure `GROQ_API_KEY` is set.
2. **Actions** → **pulse-weekly** → **Run workflow** (or wait for Monday `03:00` UTC cron).
3. Open the run → **Artifacts** → download `pulse-YYYY-MM-DD` (`pulse-*.md` + `themes.json`).
4. Publish with [MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1) per `mcp-runbook.md` when that runbook exists.

Job fails (and notifies) if the secret is missing, Play/clean yields no reviews, Groq errors, or the auditor rejects the pulse.

## Non-goals

- No Docs append / Gmail draft from Actions
- No commit of `pulse/data/raw/` (PII risk before clean)
