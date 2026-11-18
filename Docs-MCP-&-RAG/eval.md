# Eval Checklist — Groww Weekly Review Pulse

Acceptance checks for the pulse track, taken from `implementation-plan.md` (Task 9 + global constraints) and aligned with `Architecture.md` / `ProblemStatement.md`.

**How to use:** Run the sample path first, then optional live + MCP. Tick each box only when verified. Record date, mode, and result in §7.

**Related:** `edge-case.md` (corner cases), `mcp-runbook.md` (Task 8 delivery steps), `pulse/README.md` (run instructions).

---

## 0. Preconditions

- [ ] `pulse/` installable (`pip install -r requirements.txt`)
- [ ] `pulse/.env` has `GROQ_API_KEY` (not committed)
- [ ] `PULSE_LOOKBACK_WEEKS` ∈ **[8, 12]** (default 10)
- [ ] `PULSE_APP_ID=com.nextbillion.groww`
- [ ] Unit suite green (no live fetch required):

```bash
cd pulse
pytest -v
```

- [ ] Sample pipeline exits 0:

```bash
cd pulse
python -m src.run_pulse --sample
```

Expected artifacts:

| Path | Purpose |
|------|---------|
| `pulse/data/clean/reviews.jsonl` | PII-stripped reviews in window |
| `pulse/out/themes.json` | ≤5 themes + top theme ids |
| `pulse/out/pulse-YYYY-MM-DD.md` | One-page pulse |

---

## 1. Ingest & window

- [ ] Lookback weeks ∈ **[8, 12]**
- [ ] Reviews are for Groww Play (`com.nextbillion.groww`) only (v1)
- [ ] Source is public listing / sample fixture — no store-login scrape
- [ ] Cleaned set has **review_count > 0** (empty window must fail CLI with exit 1, no publish)
- [ ] (Optional live) `python -m src.run_pulse --live` completes with rate-limited fetch and in-window filter

---

## 2. Themes

- [ ] `themes.json` has **1–5** themes (hard cap 5; never 6+)
- [ ] No theme with zero supporting reviews (or empty themes dropped)
- [ ] Written pulse highlights **exactly top 3** theme labels
- [ ] Theme labels are product-feedback oriented (not investment advice)

---

## 3. Pulse content contract

Open latest `pulse/out/pulse-*.md`:

- [ ] Has sections: **Top themes**, **What users said**, **Action ideas**
- [ ] Exactly **3** themes called out
- [ ] Exactly **3** quotes
- [ ] Exactly **3** action ideas
- [ ] Body word count **≤ 250** (use same rules as `count_words` / auditor)
- [ ] Actions are concrete and tied to observed themes (manual skim)
- [ ] No investment-advice framing

---

## 4. Quote grounding & PII

- [ ] Each quote is a **substring** of some cleaned review body (auditor / manual check)
- [ ] Quotes are verbatim — not paraphrased or invented
- [ ] Prefer distinct quotes (not the same line repeated 3×)
- [ ] No email / phone patterns in `pulse/out/` (`themes.json`, `pulse-*.md`)
- [ ] No usernames, device IDs, or account handles in artifacts
- [ ] Cleaned reviews under `data/clean/` also free of email/phone patterns

Quick PII skim (example):

```bash
cd pulse
rg -n "@|\\+?[0-9]{10,}" out data/clean
```

Expect: no real emails/phones in those paths.

---

## 5. Auditor / CLI gates

- [ ] Passing run: CLI exit **0**; `pulse-*.md` written
- [ ] Invented-quote case would fail audit (covered by `tests/test_audit.py`)
- [ ] Audit failure does **not** publish via MCP (exit 2 / stop before delivery)
- [ ] No `google-api-python-client` / LangChain Gmail-Drive toolkit as primary Docs/Gmail path in `pulse/`

---

## 6. MCP delivery (MCP-Server-1)

Prereqs: server from [FallenOne1701/MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1) authorized in Cursor; blank Doc id in `PULSE_DOC_ID`; draft recipient in `PULSE_DRAFT_TO`. Follow `mcp-runbook.md` when present.

- [ ] Google Doc updated via **`google_docs_append_content`** (pre-created `PULSE_DOC_ID`)
- [ ] Appended content matches audited pulse (or dated heading + pulse body)
- [ ] Gmail **draft** created via **`gmail_create_draft`** to self/alias
- [ ] Draft body contains pulse text **or** clear Doc link/pointer
- [ ] Draft was **not** auto-sent (`gmail_send_email` unused for success)
- [ ] No PII in Doc or draft

| Capability | MCP tool | Pass? |
|------------|----------|-------|
| Publish pulse into Doc | `google_docs_append_content` | |
| Create Gmail draft | `gmail_create_draft` | |
| Send email | `gmail_send_email` | N/A (unused) |

---

## 7. FAQ isolation

- [ ] FAQ `backend/corpus_index` (and Chroma / processed FAQ corpus) **untouched**
- [ ] No pulse review text mixed into FAQ RAG
- [ ] FAQ stack still imports:

```bash
cd backend
python -c "import main; print('faq ok')"
```

- [ ] Vercel / Railway FAQ deploys not replaced by this track

---

## 8. Out of scope (do not require for pass)

These are later-plan items — **not** eval failures if missing:

- Combined demo hub / `/pulse` on Vercel
- Railway trigger endpoint
- Auto Docs/Gmail from CI (weekly Actions may exist for fetch + artifacts only)
- App Store ingest
- Merging pulse into FAQ RAG corpus
- `gmail_send_email` as part of the demo

---

## 9. Run record

| Field | Value |
|-------|-------|
| Date | |
| Mode | `--sample` / `--live` |
| Lookback weeks | |
| Review count | |
| Themes file | `pulse/out/themes.json` |
| Pulse file | `pulse/out/pulse-____-__-__.md` |
| Word count | |
| Doc id / URL | |
| Draft id | |
| pytest | PASS / FAIL |
| Overall | **PASS** / **FAIL** |

**Blockers / notes:**

-

---

## 10. Pass rule (summary)

**PASS** only if all of the following are true:

1. Lookback ∈ [8, 12] and cleaned reviews &gt; 0  
2. Themes ≤ 5; pulse has top 3 themes, 3 grounded quotes, 3 actions; ≤250 words  
3. No PII in `out/` (and delivery artifacts)  
4. Doc appended + Gmail draft created via MCP-Server-1  
5. FAQ corpus / deploy isolation held  

Offline batch (1–3 + tests) can be recorded as **PARTIAL PASS** if MCP is unavailable; full track success requires §6.
