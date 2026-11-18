# Problem Statement: Groww Weekly Review Pulse (MCP Docs + Gmail)

## Overview

Turn raw public mobile-store feedback for the **Groww** app into a **weekly pulse** the team can scan in minutes: what users care about, what they actually said, and what to do next.

Reviews are already public. This track aggregates, themes, and summarizes them, then delivers insight through familiar surfaces—**Google Docs** for the written pulse and **Gmail** for a draft you can send yourself—**via MCP**, without handling Google credentials or REST wiring yourself.

**Product focus:** [Groww on Google Play](https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN) (Stocks, Mutual Fund, IPO). App Store reviews may be included when a compliant public export is available.

This is the **second track** of the capstone monorepo. It is designed and built **beside** the Mutual Fund FAQ Assistant (`Docs-FAQ/`), then composed into **one combined demo** after both tracks are complete. Existing Vercel/Railway FAQ deployments stay as-is until that merge; they can be **updated in place** rather than replaced.

## Objective

Design and implement a lightweight review-intelligence pipeline that:

- Imports recent public Play Store (and, where available, App Store) reviews for Groww
- Clusters reviews into a small set of themes (at most 5)
- Distills a scannable one-page weekly note
- Publishes that note to Google Docs via MCP
- Creates a Gmail draft (to yourself or an alias) containing the note or a clear pointer to it, via MCP

## Target Users

| Audience | Why |
|----------|-----|
| Product / Growth | Prioritize fixes and improvements from real signals |
| Support | Align messaging with what users are actually saying |
| Leadership | One-page health check without drowning in raw reviews |

## End-to-End Flow (“Done”)

1. Pull recent App Store and/or Play Store reviews for Groww (within the rules below).
2. Cluster them into a small set of themes and distill a one-page weekly note.
3. Put that note where stakeholders can read it (**Google Docs** via MCP).
4. Create a **draft email** to yourself (or an alias) that contains or links to that pulse (**Gmail** via MCP).

## Scope of Work

### 1. Review Import

- Import reviews from roughly the **last 8–12 weeks**
- Use fields such as rating, title, text, and date (whatever the export provides)
- **Public review exports only**—no scraping behind store logins or ToS-violating automation
- Primary Play listing: `com.nextbillion.groww` ([Play Store page](https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN))

### 2. Theming

- Group reviews into **at most 5 themes**
- Example theme names (adapt to what the data shows): onboarding, KYC, payments, statements, withdrawals, app performance, customer support, etc.
- The written pulse highlights the **top 3** themes (subset of the ≤5)

### 3. Weekly One-Page Pulse

The note must include:

- **Top themes** — what people are talking about most (top 3 in the written pulse)
- **Real user quotes** — verbatim snippets from reviews; no invented wording
- **Three action ideas** — concrete next steps grounded in the themes

**Length:** Keep the note scannable and **≤250 words** where applicable.

### 4. Delivery via MCP (required path)

- **Google Docs:** create or update the pulse document using MCP tools (not a bespoke OAuth + REST client as the primary path)
- **Gmail:** create a draft message containing the weekly note or a clear pointer (e.g. Doc link) using MCP tools
- Choose MCP servers/connectors the environment provides for Docs and Gmail; requirement is **MCP-first**

### 5. Relationship to FAQ Track (combined demo later)

| Track | Role now | Role after merge |
|-------|----------|------------------|
| FAQ (`Docs-FAQ/`, existing frontend/backend) | Live facts-only Q&A | Remains chat surface |
| Review pulse (this doc) | Built separately under this folder + dedicated code area | Composed into one demo (hub or shared UI); Docs/Gmail stay MCP-driven |

Do **not** fold pulse logic into the FAQ RAG corpus or force custom Google API plumbing into the FAQ backend during this track.

## Constraints

### Reviews and Compliance

- Public exports only; respect store terms and rate limits of any official/public tooling used
- No login-gated scraping or unauthorized automation

### Themes and Content

- Maximum **5** themes for clustering; pulse prose highlights **top 3**
- Quotes must be **verbatim** from reviews
- Action ideas must be grounded in themes (no generic filler)

### Privacy

Do **not** include PII in any artifact:

- No usernames, emails, device IDs, or other identifiable reviewer data
- Quotes should be anonymous / stripped of identifiers as needed

### Integrations

- Docs and Gmail via **MCP**, not primary hand-rolled Google OAuth/REST clients
- Avoid duplicating auth and HTTP plumbing that MCP already provides

## Expected Deliverables

### Weekly pulse document (Google Docs)

- Top 3 themes
- 3 real user quotes
- 3 action ideas
- Scannable; ≤250 words where applicable

### Gmail draft

- Draft to yourself or an alias
- Contains the weekly note or a clear pointer to the Doc

### Documentation (this track)

- This problem statement
- Architecture overview (pipeline, theming, MCP Docs/Gmail)
- Setup / run instructions and known limitations
- Notes on how this track will merge with the FAQ demo later

## Success Criteria

- Reviews from ~8–12 weeks ingested from compliant public sources
- Clustering into ≤5 themes; pulse highlights top 3
- One-page note with themes, verbatim quotes, and 3 action ideas
- Pulse published to Google Docs via MCP
- Gmail draft created via MCP with note or Doc pointer
- No PII in Docs, email, or intermediate artifacts
- FAQ track left intact until an explicit combined-demo merge

## Summary

Build a trustworthy, scannable **weekly review pulse** for Groww: aggregate public store feedback, theme it, summarize it, and deliver it through **Google Docs** and a **Gmail draft**—using **MCP** as the integration path. Develop this track separately from the FAQ assistant, then merge into one combined demo without replacing the existing Vercel/Railway deployments.
