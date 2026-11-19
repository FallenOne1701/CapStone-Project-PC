---
name: Support Deck
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3e4944'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6e7a74'
  outline-variant: '#bdc9c2'
  surface-tint: '#006c53'
  primary: '#005f49'
  on-primary: '#ffffff'
  primary-container: '#0d7a5f'
  on-primary-container: '#a8ffdf'
  inverse-primary: '#7cd8b8'
  secondary: '#286956'
  on-secondary: '#ffffff'
  secondary-container: '#aef0d7'
  on-secondary-container: '#2f6f5c'
  tertiary: '#005f49'
  on-tertiary: '#ffffff'
  tertiary-container: '#007a5f'
  on-tertiary-container: '#a5ffde'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#98f4d3'
  primary-fixed-dim: '#7cd8b8'
  on-primary-fixed: '#002117'
  on-primary-fixed-variant: '#00513e'
  secondary-fixed: '#aef0d7'
  secondary-fixed-dim: '#93d4bc'
  on-secondary-fixed: '#002118'
  on-secondary-fixed-variant: '#05513f'
  tertiary-fixed: '#86f7d1'
  tertiary-fixed-dim: '#68dab6'
  on-tertiary-fixed: '#002117'
  on-tertiary-fixed-variant: '#00513e'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.5rem
    fontWeight: '700'
    lineHeight: 2rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.75rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 1rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.9375rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.125rem
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1rem
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.25rem
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-dense: 0.5rem
  margin: 1.5rem
  margin-mobile: 0.75rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style

This design system establishes a visual language for the Support Deck dual loops (response + weekly product), high-velocity drafting, and audit-ready human review. The interface supports support agents, product/growth, compliance/ops, and leadership reviewing fee explainers and reply drafts—aligned with the problem statement audience, not an “operator console” brand.

### Aesthetic Paradigm
- **Direction:** Corporate Modern with dense data pragmatism and Swiss utility. 
- **Tone:** Grounded, trustworthy, objective, and quiet. The interface steps back completely to let financial ledger IDs, transaction payloads, fee breakdowns, and drafting diffs take center stage.
- **Strict Guardrails:** Absolutely zero decorative gradients, neon glow outlines, purple ambient blurs, emoji-based status icons, or floating cards with excessive whitespace. Surfaces must feel structured, disciplined, and physical like an institutional terminal.

## Colors

The palette balances Groww-derived institutional teal with cold technical slate neutrals. Every color role maintains rigorous contrast to enable rapid scanning without visual fatigue.

### Core Swatches
- **Primary Brand Teal:** `#0D7A5F` (interactive actions, affirmative states, primary controls).
- **Primary Dark/Hover:** `#095341` (pressed/hover state for teal actions, active navigation label).
- **Vibrant Teal Accent:** `#139A79` (subtle metrics highlight, active focus rings).
- **Teal Subtle Tint:** `#E6F4F1` (active tab background, selected list items, highlighted split-pane rows).
- **Teal Border Tint:** `#C8EAE2` (borders for active selection items, primary badges).

### Neutrals & Surfaces
- **Canvas / App Background:** `#F8FAFC` (slate-50).
- **Panels & Surface Base:** `#FFFFFF` (clean white for split panes, tables, review drawers).
- **Primary Structural Divider:** `#E2E8F0` (slate-200, used for split panes, table rows, and grid boundaries).
- **Secondary Border / Form Stroke:** `#CBD5E1` (slate-300, input borders, button outlines).

### Typography Tones
- **Primary Text:** `#0F172A` (slate-900, headline text, active customer messages, fee values).
- **Secondary Text:** `#475569` (slate-600, labels, timestamps, metadata keys).
- **Muted Text:** `#64748B` (slate-500, placeholder text, secondary status counts).
- **Monospace / Code Text:** `#334155` (slate-700, transaction hashes, ticket IDs, payloads).

### Functional Status Indicators
- **Positive / Approved / Active:** Background `#ECFDF5`, Border `#A7F3D0`, Text `#065F46`.
- **Caution / Under Review / Pending:** Background `#FFFBEB`, Border `#FDE68A`, Text `#92400E`.
- **Critical / Rejected / Disputed:** Background `#FEF2F2`, Border `#FECACA`, Text `#991B1B`.
- **Neutral / Queued / System Log:** Background `#F1F5F9`, Border `#CBD5E1`, Text `#334155`.

## Typography

The typography hierarchy uses **Plus Jakarta Sans** for UI chrome, headings, customer message transcripts, and narrative drafting review panels. **JetBrains Mono** is reserved exclusively for ledger IDs, ticket references, fee rate tables, audit run hashes, and JSON diffs.

### Hierarchy & Application Rules
- **Headline Large:** Sticky top console title (`Support Deck`).
- **Headline Medium:** Major pane titles and drawer views (`Review Approval Gate`, `Fee Calculation Audit`).
- **Headline Small:** Section partition titles (`Customer Prompt`, `AI Draft Iteration`, `System Context`).
- **Body Regular (`body-md` / `body-sm`):** The primary reading plane for conversation logs, policy clauses, and ticket communications.
- **Label Small (`label-sm`):** All uppercase status badges, form field identifiers, table column headers.
- **Code Tokens (`code-md` / `code-sm`):** All ticket reference codes (e.g., `TCK-8921-X`), account handles, API timestamps, and numerical fee formula steps.

## Layout & Spacing

The console follows a desktop-first, dense fixed-fluid operational split-view design. White space is utilized strictly for grouping comprehension rather than aesthetic padding.

### Layout Topology
1. **Master Header (Fixed):** Height `56px`, fixed top with sticky z-index. Holds branding, subtitle, tab navigation (`Queue`, `Pulse`, `Explainers`, `Approvals`, `Sources`), and secondary contextual utilities.
2. **Dense Split Pane (Queue & Approvals Views):**
   - **Left Column (List / Ingestion Stream):** Fixed width of `380px` to `420px`. Houses incoming queue items, sort switches, and status summaries.
   - **Right Column (Workspace / Stage):** Fluid width filling remainder of canvas. Houses ticket interaction timeline, draft review panel, and the human gate approval bar.
3. **Table & Audit Grid:** Edge-to-edge layout within white panel containers, featuring explicit 1px slate boundaries (`#E2E8F0`).

### Responsive Adaptation
- **Desktop (>= 1280px):** True dual-column split view with independent vertical scrolling panels.
- **Laptop / Tablet Landscape (1024px - 1279px):** Split pane remains, left column narrows to `320px`, collapsing auxiliary metadata tags.
- **Tablet / Mobile (< 1023px):** Collapses to stacked step flow: view switches between List Mode and Stage Mode via top breadcrumb navigation.

## Elevation & Depth

This design system avoids deep Drop Shadows and floating material elevations in favor of clean planar containment and thin boundary lines.

### Depth Hierarchy
- **Level 0 (Canvas):** Base background `#F8FAFC`.
- **Level 1 (Panels & Workspaces):** Flat `#FFFFFF` panels defined by crisp `1px solid #E2E8F0` borders. No shadow.
- **Level 2 (Active Item / Focus):** Active item within an ingestion list receives background `#E6F4F1`, a left edge marker of `3px solid #0D7A5F`, and border `#C8EAE2`.
- **Level 3 (Sticky Controls & Popovers):** Action bars, filter dropdown menus, and sticky approval footers utilize:
  `box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.08), 0 1px 2px -1px rgba(15, 23, 42, 0.04);`
  with surface `#FFFFFF` and border `1px solid #CBD5E1`.

## Shapes

The design system maintains a balanced, professional geometry (`roundedness: 2`). Corners are clean and refined, providing adequate modern software polish while avoiding excessive bubbly radiuses that compromise dense layouts.

- **Inputs, Buttons, Filter Bars:** `0.5rem` (`rounded-md` / `rounded-lg`).
- **Status Chips & Pills:** `0.375rem` (`rounded-md`) to ensure compact alignment within tabular metadata.
- **Panels & Split Dividers:** Sharp outer edges against browser boundaries (`0px`), with internal sub-containers using `0.5rem`.

## Components

### Header & Navigation
- **Height & Frame:** Sticky `56px` height, `#FFFFFF` background, bottom border `1px solid #E2E8F0`.
- **Title Block:** `Support Deck` rendered in `headline-sm` font-bold text `#0F172A`, paired with an inline separator and muted subtitle `Dual loops · human approval gate` in `body-sm` `#64748B`.
- **Navigation Tabs:** Horizontal pill tabs with `space-xs` padding.
  - *Inactive:* Transparent background, text `#475569`, hover `#F1F5F9`.
  - *Active:* Background `#E6F4F1`, text `#095341`, font weight `600`, border `1px solid #C8EAE2`.

### Buttons
- **Primary:** Background `#0D7A5F`, text `#FFFFFF`, hover `#095341`, active `#063D2F`. Padding `0.5rem 1rem`, typography `label-md`. Shadow: `0 1px 2px rgba(0, 0, 0, 0.05)`.
- **Secondary / Outline:** Background `#FFFFFF`, border `1px solid #CBD5E1`, text `#334155`, hover background `#F8FAFC`.
- **Destructive Outline:** Background `#FFFFFF`, border `1px solid #FECACA`, text `#DC2626`, hover background `#FEF2F2`.
- **Compact Icon Buttons:** `32px x 32px` square, `rounded-md`, border `1px solid #E2E8F0`, icon size `16px`.

### Status Badges & Chips
- Padding: `0.125rem 0.5rem`, font `label-sm`, letter spacing `0.02em`, uppercase.
- **Approved / Drafted / Active:** Background `#ECFDF5`, text `#065F46`, border `1px solid #A7F3D0`.
- **Review / Explainer / Warning:** Background `#FFFBEB`, text `#92400E`, border `1px solid #FDE68A`.
- **Rejected / Disputed:** Background `#FEF2F2`, text `#991B1B`, border `1px solid #FECACA`.
- **Pending / Queued:** Background `#F1F5F9`, text `#334155`, border `1px solid #CBD5E1`.

### Form Controls & Input Fields
- **Text Inputs & Filter Bars:** Background `#FFFFFF`, border `1px solid #CBD5E1`, placeholder `#94A3B8`, text `#0F172A`. Height `36px`, padding `0 0.75rem`. Focus ring: `2px solid #0D7A5F` with `0px` offset.
- **Checkboxes & Radios:** Size `16px x 16px`, border `1.5px solid #94A3B8`, active fill `#0D7A5F`, checked indicator pure white.

### Data Tables & Split Lists
- **Table Headers:** Background `#F8FAFC`, bottom border `1px solid #E2E8F0`, typography `label-sm`, color `#475569`.
- **Table Rows:** Background `#FFFFFF`, alternating hover state `#F8FAFC`, row height `40px` dense, `48px` standard. Border-bottom `1px solid #E2E8F0`.
- **Monospace Trace Viewers:** Background `#F8FAFC`, border `1px solid #E2E8F0`, padding `0.75rem`, font `code-sm`, color `#334155`. Shows full lineage, parameter breakdowns, and payload tokens.