# Groww weekly review pulse

On-demand pipeline that pulls public Google Play reviews for Groww, strips PII, clusters themes with Groq via LangChain, writes a short pulse note, and audits grounding / structure before writing artifacts.

## Setup

```bash
cd pulse
copy .env.example .env
# set GROQ_API_KEY in .env
pip install -r requirements.txt
```

## Run

**Sample (default, offline fixture):**

```bash
python -m src.run_pulse
# or
python -m src.run_pulse --sample
```

Uses `data/samples/reviews_sample.jsonl`. Safe for local/CI without hitting Play.

**Live Play fetch:**

```bash
python -m src.run_pulse --live
```

Fetches public reviews for `PULSE_APP_ID` (default `com.nextbillion.groww`) within `PULSE_LOOKBACK_WEEKS`, then runs the same clean → theme → write → audit path.

## Outputs

| Path | Contents |
|------|----------|
| `data/raw/play-YYYY-MM-DD.jsonl` | Raw live fetch (live only) |
| `data/clean/reviews.jsonl` | PII-stripped reviews in window |
| `out/themes.json` | ≤5 themes, top 3 ids |
| `out/pulse-YYYY-MM-DD.md` | Pulse markdown (≤250 words target) |

## Weekly GitHub Actions job

Workflow: [`.github/workflows/pulse-weekly.yml`](../.github/workflows/pulse-weekly.yml)

| Item | Detail |
|------|--------|
| Schedule | Mondays `03:00` UTC (`0 3 * * 1`) |
| Manual | Actions → **pulse-weekly** → **Run workflow** |
| Command | `python -m src.run_pulse --live` |
| Required secret | `GROQ_API_KEY` (same value as local `pulse/.env`) |
| Optional Variables | `PULSE_LOOKBACK_WEEKS`, `PULSE_MAX_REVIEWS`, `GROQ_CHAT_MODEL` (omit to use `Settings` defaults) |
| Artifact | `pulse-YYYY-MM-DD` containing `pulse-*.md` + `themes.json` |

CI does **not** call Docs/Gmail. Download the artifact, then publish via MCP (below). Raw Play dumps stay on the runner and are not uploaded.

**Add the secret once:** GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** → name `GROQ_API_KEY`, value from [console.groq.com](https://console.groq.com/).

## Publish (Docs + Gmail draft)

This package does **not** call Google APIs. After a successful local or Actions run, follow [`Docs-MCP-&-RAG/mcp-runbook.md`](../Docs-MCP-&-RAG/mcp-runbook.md) and use [MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1) to append the pulse to a Google Doc and create a Gmail draft.

## Tests

```bash
pytest -v
```

Unit tests stay offline; they do not call Play or Groq.
