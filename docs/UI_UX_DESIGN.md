# UI/UX Design — Premium Hybrid

> **Status:** DRAFT — decisions of 2026-09-22 recorded
> **Version:** 0.2
> **Date:** 2026-09-22
> **Authoring order:** 8 of 9 (written early to unblock parallel frontend work)
> **Depends on:** root `AGENTS.md`, `PRODUCT_PRD.md`, `TECHNICAL_PRD.md`
> **Primary author:** Developer 1 (Frontend/UI)

## Purpose of this document

The single source of truth for every frontend UI/UX decision. Tokens defined here are the **only**
permitted source of color, typography, spacing, radius, and elevation in the application. A value
that does not appear in this document does not appear in a component.

This document is written to be prescriptive rather than suggestive. Three developers building
different screens from it must produce work that looks like one product, so it states exact values
and exact component names.

**Boundaries.** Product requirements are owned by `PRODUCT_PRD.md` and referenced by ID
(`FR-OPP-07`). Data shapes are owned by `API_CONTRACT.md`. This document decides appearance,
structure, interaction, and state presentation.

---

## 1. Design principles

Seven principles, in priority order. When two conflict, the higher-numbered one yields.

**P1 — Truth is legible.** The four layers — observed fact, AI interpretation, potential
opportunity, recommended action — must be distinguishable at a glance, without reading
(`FR-OPP-14`). This is the product's core promise and outranks every aesthetic consideration.

**P2 — Every number is traceable.** No figure appears without a path to its evidence
(`FR-DASH-08`, `FR-EV-03`). A score never appears without its explanation and factor breakdown
(`FR-SCR-05`). If a design shows a number it cannot justify, the design is wrong.

**P3 — Color carries meaning, never decoration.** The semantic palette (§2.3) is reserved. An amber
element means opportunity or attention. A red element means risk. Nothing is colored to look
interesting.

**P4 — Restraint over density.** This is a command centre, not a wall of widgets. Whitespace and
hierarchy do the work. If a screen needs a legend to be understood, simplify the screen.

**P5 — Honest states are designed states.** Loading, empty, error, insufficient evidence, partial
scan, and cached data are specified components (§34–§37), not afterthoughts. "Nothing observable is
happening" is a legitimate, useful answer and must look deliberate.

**P6 — Enterprise calm.** Subtle elevation, restrained motion, professional typography. The
product should feel like software a director of sales trusts with their pipeline.

**P7 — Impressive through clarity.** Visual impact comes from confident hierarchy, precise
alignment, and quality data presentation — never from glow, gradients, or animation.

### 1.1 Anti-patterns — explicitly forbidden

The approved direction is Premium Hybrid. The following are not stylistic preferences; they are
prohibited because each pushes the product toward an aesthetic we have rejected.

| Forbidden | Why |
|---|---|
| Neon or colored glow shadows | Gaming/hacker aesthetic |
| Dark mode as the default or dominant surface | Only AI panels are dark; the product is a light enterprise interface |
| Gradient text, gradient headings, gradient hero panels | Generic AI-product look |
| Glassmorphism, blur panels, translucent overlays over content | Reduces legibility, reads as consumer |
| Animated particles, pulsing orbs, "thinking" glow effects | Overly glowing AI interface |
| Terminal/monospace styling for general content | Hacker interface |
| Emoji as iconography | Unprofessional in an enterprise tool |
| 3D charts, donut stacks, gauge dials with needles | Admin-template look; poor data density |
| Rainbow-filled category badges | Destroys the semantic palette (P3) |
| Full-width edge-to-edge cards with no containment | Generic admin template |
| More than two accent colors in one viewport region | Visual noise |
| Motion longer than 240ms, bouncing or springing easing | Feels toy-like |

---

## 2. Color system

### 2.1 Foundation scales

Raw palette. Components reference the **semantic tokens** in §2.3, not these values directly.

**Navy — structural foundation** (brand, navigation, headings, primary actions)

| Token | Hex | Use |
|---|---|---|
| `navy-50` | `#EEF2F8` | Tinted backgrounds, selected rows |
| `navy-100` | `#D8E1EF` | Subtle fills, badge backgrounds |
| `navy-200` | `#B3C3DD` | Borders on navy surfaces |
| `navy-300` | `#7F97BE` | Muted text on dark navy |
| `navy-400` | `#4E6B9B` | Focus rings, chart series |
| `navy-500` | `#2F4E7E` | Secondary structure, medium score band |
| `navy-600` | `#1E3A66` | **Primary** — buttons, links, active nav |
| `navy-700` | `#172E52` | Primary hover |
| `navy-800` | `#11223D` | Sidebar background |
| `navy-900` | `#0B1729` | Deepest surface — AI panels, tooltips |

**Indigo — AI and intelligence** (reserved; see §2.4)

| Token | Hex | Use |
|---|---|---|
| `indigo-50` | `#EEF0FE` | Subtle AI surface on light backgrounds |
| `indigo-100` | `#E0E3FC` | AI badge background |
| `indigo-200` | `#C4C9F9` | AI borders |
| `indigo-300` | `#9AA2F2` | AI accents on dark surfaces |
| `indigo-400` | `#7B84EC` | AI text on dark surfaces |
| `indigo-500` | `#5B62E3` | AI accent, focus on dark |
| `indigo-600` | `#4A4FD1` | **AI primary** — AI actions, AI labels |
| `indigo-700` | `#3B3FAC` | AI hover |
| `violet-500` | `#8B5CF6` | AI secondary accent — sparing, charts only |

**Amber — opportunity and attention**

| Token | Hex | Use |
|---|---|---|
| `amber-50` | `#FFF8EB` | Opportunity badge background |
| `amber-100` | `#FEEFC7` | Opportunity fills |
| `amber-300` | `#FCD34D` | Chart fills |
| `amber-500` | `#F59E0B` | Score bars, chart series |
| `amber-600` | `#D97706` | **Opportunity primary** — high band, attention text |
| `amber-700` | `#B45309` | Text on amber-50 where contrast requires |

**Green — positive and healthy**

| Token | Hex | Use |
|---|---|---|
| `green-50` | `#ECFDF5` | Success alert background |
| `green-100` | `#D1FAE5` | Success fills |
| `green-500` | `#10B981` | Chart series |
| `green-600` | `#059669` | **Positive primary** — validated, scan succeeded |
| `green-700` | `#047857` | Text on green-50 |

**Red — risk and failure**

| Token | Hex | Use |
|---|---|---|
| `red-50` | `#FEF2F2` | Error alert background |
| `red-100` | `#FEE2E2` | Error fills |
| `red-500` | `#EF4444` | Chart series |
| `red-600` | `#DC2626` | **Risk primary** — errors, failed sources |
| `red-700` | `#B91C1C` | Text on red-50 |

**Neutral — blue-tinted greys** (chosen to sit harmoniously with navy; never pure grey)

| Token | Hex | Use |
|---|---|---|
| `neutral-0` | `#FFFFFF` | Card surfaces |
| `neutral-50` | `#F7F9FC` | Application background |
| `neutral-100` | `#EEF2F7` | Sunken surfaces, table headers |
| `neutral-200` | `#E2E8F0` | **Default border** |
| `neutral-300` | `#CBD5E1` | Strong border, dividers on fills |
| `neutral-400` | `#94A3B8` | Muted text, disabled, placeholder |
| `neutral-500` | `#64748B` | **Secondary text** |
| `neutral-600` | `#475569` | Body text on tinted fills |
| `neutral-700` | `#334155` | Strong body text |
| `neutral-900` | `#0F172A` | **Primary text** |

### 2.2 Why there is no pure black or pure grey

Every neutral carries a blue tint so that white cards, navy structure, and neutral text read as one
family. Pure `#000000` and pure greys (`#808080`) are forbidden — they make the interface look
assembled from parts.

### 2.3 Semantic tokens

**These are the names components use.** They are also the names referenced by the frontend rule
`premium-hybrid-design-system.mdc`.

| Semantic token | Value | Meaning |
|---|---|---|
| `bg-app` | `neutral-50` | Application background |
| `surface` | `neutral-0` | Standard card / panel |
| `surface-sunken` | `neutral-100` | Table headers, inset regions |
| `surface-selected` | `navy-50` | Selected row or item |
| `surface-ai` | `navy-900` | **Dark AI panel** |
| `surface-ai-subtle` | `indigo-50` | Light AI region on white |
| `border-default` | `neutral-200` | Standard border |
| `border-strong` | `neutral-300` | Emphasis border |
| `border-ai` | `indigo-200` | AI region border |
| `text-primary` | `neutral-900` | Headings and body |
| `text-secondary` | `neutral-500` | Labels, metadata |
| `text-muted` | `neutral-400` | Disabled, placeholder, timestamps |
| `text-inverse` | `neutral-0` | On navy buttons |
| `text-on-ai` | `#E8EBF5` | Body text on `surface-ai` |
| `text-on-ai-muted` | `navy-300` | Secondary text on `surface-ai` |
| `status-opportunity` | `amber-600` | Opportunity / needs attention |
| `status-positive` | `green-600` | Positive / healthy |
| `status-risk` | `red-600` | Risk / failure |
| `status-ai` | `indigo-600` | AI / intelligence |
| `status-neutral` | `neutral-500` | Informational, no valence |
| `interactive` | `navy-600` | Primary action, link |
| `interactive-hover` | `navy-700` | Primary action hover |
| `focus-ring` | `navy-400` | Focus indicator on light surfaces |
| `focus-ring-ai` | `indigo-400` | Focus indicator on `surface-ai` |

### 2.4 Reserved color rules

These rules exist because a three-developer team will otherwise drift within two days.

1. **Indigo/violet is reserved for AI.** If a pixel is indigo, it relates to machine-generated
   content. Never use indigo for a generic link, a primary button, or decoration.
2. **Amber means opportunity or attention.** Never used for branding, never for a neutral
   highlight.
3. **Green means positive or healthy** — a successful scan, a validated signal. It does **not** mean
   "good lead."
4. **Red means risk or failure** — an error, a failed source. It does **not** mean "bad lead," and
   it is never used for a rejected signal (rejection is neutral, §20.3).
5. **Navy is structure**, not status. Navigation, headings, primary actions.

### 2.5 Score band colors

`PRODUCT_PRD.md` §13.3 defines four bands. The instinct is green-to-red; that instinct is wrong
here and would break rules 3 and 4 above — a low-scoring organization is not a "risk," and a
high-scoring one is not "healthy." Bands are encoded as **attention intensity**:

| Band | Range | Token | Treatment |
|---|---|---|---|
| High | 75–100 | `amber-600` | Filled badge, `amber-50` background |
| Medium | 50–74 | `navy-500` | Outlined badge, `navy-50` background |
| Low | 25–49 | `neutral-500` | Outlined badge, `surface-sunken` background |
| Monitor | 0–24 | `neutral-400` | Text only, no fill |

The band label text is always present. Color never carries the meaning alone (§39).

### 2.6 Signal type colors

Seven categories genuinely require categorical encoding in charts. To prevent a rainbow interface,
the categorical palette is **deliberately desaturated** so semantic colors always outrank it in
visual weight.

| # | Signal type | Token name | Hex |
|---|---|---|---|
| 1 | Procurement | `signal-procurement` | `#1E3A66` |
| 2 | Technology initiatives | `signal-technology` | `#2E7DA8` |
| 3 | Leadership changes | `signal-leadership` | `#7C6AB0` |
| 4 | Funding/budget | `signal-funding` | `#2F8F6B` |
| 5 | Strategic announcements | `signal-strategic` | `#B07A2E` |
| 6 | Competitor/vendor | `signal-competitor` | `#A2506B` |
| 7 | Contract/renewal | `signal-contract` | `#5C6B7A` |

**Usage rule.** In charts, these are fills. In badges and lists, the type badge is neutral with a
6px colored dot (§20.1) — the color aids scanning, the neutral background preserves the palette.
A signal type keeps the same color everywhere in the product.

### 2.7 Tailwind theme reference

To be transcribed into `tailwind.config` when frontend implementation begins. Recorded here so the
tokens have one origin.

```js
// Reference only — not application code. Transcribe at implementation time.
theme: {
  extend: {
    colors: {
      navy:   { 50:'#EEF2F8',100:'#D8E1EF',200:'#B3C3DD',300:'#7F97BE',400:'#4E6B9B',
                500:'#2F4E7E',600:'#1E3A66',700:'#172E52',800:'#11223D',900:'#0B1729' },
      indigo: { 50:'#EEF0FE',100:'#E0E3FC',200:'#C4C9F9',300:'#9AA2F2',400:'#7B84EC',
                500:'#5B62E3',600:'#4A4FD1',700:'#3B3FAC' },
      surface: { DEFAULT:'#FFFFFF', sunken:'#EEF2F7', selected:'#EEF2F8',
                 ai:'#0B1729', 'ai-subtle':'#EEF0FE' },
      status:  { opportunity:'#D97706', positive:'#059669', risk:'#DC2626',
                 ai:'#4A4FD1', neutral:'#64748B' },
      signal:  { procurement:'#1E3A66', technology:'#2E7DA8', leadership:'#7C6AB0',
                 funding:'#2F8F6B', strategic:'#B07A2E', competitor:'#A2506B',
                 contract:'#5C6B7A' },
    },
  },
}
```

---

## 3. Typography

### 3.1 Families

| Role | Family | Notes |
|---|---|---|
| Interface | **Inter** | All UI text. Variable weight. Self-hosted via `@fontsource/inter` so the demo does not depend on an external CDN |
| Numeric data | Inter with `tabular-nums` | Scores, metrics, table numbers. No second font |
| Identifiers | System monospace stack | Source URLs, record identifiers only. Never body text |

**Decision (resolves the open question in the previous placeholder): Inter.** One family. It is
neutral, enterprise-appropriate, excellent at 13–14px, and has a true variable axis. A display
typeface was considered and rejected — it would add weight and a drift risk across three
developers for no product benefit.

Fallback stack: `Inter, -apple-system, "Segoe UI", Roboto, sans-serif`.

### 3.2 Weights

Only four: 400 regular, 500 medium, 600 semibold, 700 bold. Bold is reserved for score values and
`display` only. Weight 300 and 800+ are forbidden — they read as consumer.

---

## 4. Font hierarchy

Exact scale. Name, size/line-height, weight, and permitted use. Nothing outside this table.

| Token | Size / Line | Weight | Use |
|---|---|---|---|
| `text-display` | 30 / 36 | 600 | Page title on dashboard only |
| `text-h1` | 24 / 32 | 600 | Page titles |
| `text-h2` | 20 / 28 | 600 | Section headings, card group titles |
| `text-h3` | 16 / 24 | 600 | Card titles |
| `text-body-lg` | 16 / 24 | 400 | Advisor answers, long-form AI text |
| `text-body` | 14 / 20 | 400 | **Default** — all interface text |
| `text-body-sm` | 13 / 18 | 400 | Table cells, dense lists, evidence snippets |
| `text-caption` | 12 / 16 | 400 | Timestamps, metadata, helper text |
| `text-label` | 11 / 16 | 600 | Uppercase, `tracking-[0.06em]` — field labels, table headers, layer labels |
| `text-metric` | 28 / 32 | 600 | Dashboard metric values, `tabular-nums` |
| `text-metric-lg` | 36 / 40 | 600 | Primary metric, `tabular-nums` |
| `text-score` | 44 / 48 | 700 | Opportunity score only, `tabular-nums` |

### 4.1 Hierarchy rules

- Default body size is **14px**, not 16px. This is an enterprise data product; 14px is the
  correct density for tables and cards. Long-form AI prose uses 16px for readability.
- One `text-h1` per page. One `text-display`, on the dashboard only.
- `text-label` is the workhorse for the interface's structure: every field, table header, and
  layer marker uses it. Consistent use of this single token is most of what makes the product look
  designed.
- Never use color as the only distinction between hierarchy levels; size or weight must also
  differ.
- Line length for prose is capped at `max-w-[68ch]`.

---

## 5. Spacing system

4px base unit. Tailwind's default scale, constrained to these steps:

| Step | px | Primary use |
|---|---|---|
| `1` | 4 | Icon-to-text gap, badge internal |
| `2` | 8 | Inline element gap, tight stacks |
| `3` | 12 | Form control internal padding, list item gap |
| `4` | 16 | Standard element gap, compact card padding |
| `5` | 20 | Table cell vertical padding |
| `6` | 24 | **Card padding**, gap between cards |
| `8` | 32 | Page padding, gap between sections |
| `10` | 40 | Gap between major page regions |
| `12` | 48 | Dashboard section separation |
| `16` | 64 | Empty-state vertical padding |

Steps 7, 9, 11, 14 are not used. Arbitrary values (`p-[13px]`) are forbidden.

### 5.1 Layout constants

| Constant | Value |
|---|---|
| Sidebar width (expanded) | 260px |
| Sidebar width (collapsed rail) | 72px |
| Header height | 64px |
| Page content max width | 1440px |
| Page horizontal padding | 32px (`8`) |
| Evidence drawer width | 480px |
| Advisor panel width | 440px |
| Card padding | 24px (`6`) |
| Grid gutter | 24px (`6`) |
| Modal max width | 560px (standard), 800px (wide) |

### 5.2 Grid

12-column grid within the content area, 24px gutters. Dashboard metric row is 4 equal columns at
`xl` and above.

---

## 6. Border radius

| Token | Value | Use |
|---|---|---|
| `rounded-sm` | 4px | Badges, chips, small inputs, tooltips |
| `rounded-md` | 6px | Buttons, inputs, dropdowns, selects |
| `rounded-lg` | 8px | **Cards, panels, tables, alerts** |
| `rounded-xl` | 12px | Modals, drawers, AI panels |
| `rounded-full` | 9999px | Pills, avatars, status dots, progress tracks |

Nothing above 12px except pills. Large radii read as consumer software. Nested elements use a
radius one step smaller than their container.

---

## 7. Shadows

Elevation is deliberately shallow. Depth comes from borders and background contrast, not from
shadow.

| Token | Value | Use |
|---|---|---|
| `shadow-xs` | `0 1px 2px rgba(15,23,42,0.04)` | Resting cards |
| `shadow-sm` | `0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)` | Hovered cards, sticky header |
| `shadow-md` | `0 4px 12px rgba(15,23,42,0.08)` | Dropdowns, popovers, tooltips |
| `shadow-lg` | `0 12px 32px rgba(15,23,42,0.12)` | Modals, drawers |

**Rules.** Every shadow uses `neutral-900` at low alpha — never a colored shadow. Colored glows are
forbidden (§1.1). A card at rest uses `shadow-xs` plus `border-default`; the border does most of
the separation work. Never stack shadows to imply importance; use hierarchy instead.

### 7.1 Z-index scale

| Layer | z-index |
|---|---|
| Base content | 0 |
| Sticky table header | 10 |
| Application header | 20 |
| Sidebar | 30 |
| Dropdown / popover | 40 |
| Drawer (evidence, advisor) | 50 |
| Modal | 60 |
| Toast | 70 |

### 7.2 Motion

| Token | Duration | Easing | Use |
|---|---|---|---|
| `motion-fast` | 120ms | `ease-out` | Hover, focus, color change |
| `motion-base` | 180ms | `ease-out` | Dropdowns, tooltips, accordions |
| `motion-slow` | 240ms | `ease-out` | Drawers, modals |

Nothing exceeds 240ms. No spring, no bounce, no infinite animation except the two permitted
indeterminate indicators: the skeleton shimmer (§34) and the scan progress bar (§33). All motion
respects `prefers-reduced-motion`.

---

## 8. Icon usage

**Library: `lucide-react`** — approved 2026-09-22. MIT licensed, tree-shakeable, consistent 24px
grid, stroke-based. It is the only icon set in the product. Imports are limited to the icons
named in §8.1. Hand-authored one-off SVGs are not used.

| Size | Value | Use |
|---|---|---|
| `icon-sm` | 16px | Inline with `text-body`, table cells, badges |
| `icon-md` | 20px | Buttons, navigation, card headers |
| `icon-lg` | 24px | Page headers, empty states |
| `icon-xl` | 32px | Empty and error state illustrations |

**Rules.** Stroke width 1.75 at all sizes. Icons inherit `currentColor` — never independently
colored. An icon never appears without a text label except in the collapsed sidebar rail and
icon-only buttons, both of which require a tooltip and `aria-label`. Emoji are forbidden.

### 8.1 Assigned icons

Fixed assignments so the same concept is never drawn two ways.

| Concept | Icon |
|---|---|
| Dashboard | `LayoutDashboard` |
| Organizations | `Building2` |
| Signals | `Radio` |
| Opportunities | `Target` |
| AI Advisor | `Sparkles` |
| Evidence | `FileText` |
| Source link | `ExternalLink` |
| Scan Now | `RefreshCw` |
| Search | `Search` |
| Filter | `SlidersHorizontal` |
| Score / factors | `BarChart3` |
| Correlation | `GitMerge` |
| Recommended action | `ArrowRightCircle` |
| Cached data | `Archive` |
| Date unavailable | `CalendarOff` |
| Success | `CheckCircle2` |
| Warning / attention | `AlertTriangle` |
| Error | `AlertCircle` |
| Information | `Info` |
| Insufficient evidence | `SearchX` |

| Signal type | Icon |
|---|---|
| Procurement | `FileSignature` |
| Technology initiatives | `Cpu` |
| Leadership changes | `UserCog` |
| Funding/budget | `Landmark` |
| Strategic announcements | `Megaphone` |
| Competitor/vendor | `Users` |
| Contract/renewal | `FileClock` |

---

## 9. Buttons

Component: `Button`.

### 9.1 Variants

| Variant | Background | Text | Border | Use |
|---|---|---|---|---|
| `primary` | `navy-600` | `text-inverse` | none | The one main action per view |
| `secondary` | `surface` | `navy-600` | `border-default` | Standard actions |
| `tertiary` | transparent | `neutral-600` | none | Low-emphasis, toolbar actions |
| `ai` | `indigo-600` | `text-inverse` | none | Ask Advisor, AI-invoking actions only |
| `danger` | `red-600` | `text-inverse` | none | Destructive — rare in this read-only product |
| `link` | transparent | `navy-600` | none | Inline navigation, underline on hover |

### 9.2 Sizes

| Size | Height | Padding X | Text | Icon |
|---|---|---|---|---|
| `sm` | 32px | 12px | `text-body-sm` | 16px |
| `md` | 40px | 16px | `text-body` | 20px |
| `lg` | 48px | 24px | `text-body` | 20px |

Radius `rounded-md`. Weight 500. Icon-to-label gap 8px.

### 9.3 States

| State | Treatment |
|---|---|
| Hover | `primary` → `navy-700`; `ai` → `indigo-700`; `secondary`/`tertiary` → `surface-sunken` |
| Active | Same as hover, plus `translate-y-[1px]` |
| Focus | `ring-2 ring-focus-ring ring-offset-2`; on `surface-ai` use `focus-ring-ai` |
| Disabled | `opacity-50`, `cursor-not-allowed`, no hover |
| Loading | Spinner replaces leading icon, label retained, button disabled, width held stable |

**Rules.** One `primary` per view region. `ai` variant only for actions that invoke the AI —
using it as a second primary breaks the indigo reservation (§2.4). Labels are verbs: "Scan Now",
"Ask Advisor", "View Evidence".

---

## 10. Inputs

Component: `Input`, `Textarea`.

| Property | Value |
|---|---|
| Height | 40px (`md`), 32px (`sm`) |
| Padding | 12px horizontal |
| Border | `border-default`, 1px |
| Radius | `rounded-md` |
| Background | `surface` |
| Text | `text-body`, `text-primary` |
| Placeholder | `text-muted` |

| State | Treatment |
|---|---|
| Hover | Border `border-strong` |
| Focus | Border `navy-400`, `ring-2 ring-focus-ring/20`, no outline |
| Error | Border `red-600`, message below in `text-caption` `status-risk` |
| Disabled | `surface-sunken`, `text-muted`, `cursor-not-allowed` |
| With leading icon | 16px icon at 12px inset, text padding 36px |

Labels sit above the field in `text-label`, 8px gap. Helper text sits below in `text-caption`
`text-secondary`. A field never relies on placeholder text as its label.

Search inputs carry a leading `Search` icon and a clear affordance when populated.

---

## 11. Dropdowns

Components: `Select` (single value), `MultiSelect` (filters), `Menu` (actions).

**Trigger** matches `Input` dimensions with a trailing `ChevronDown` (16px, `text-secondary`).

**Panel:** `surface`, `border-default`, `rounded-md`, `shadow-md`, 4px padding, 4px offset from
trigger, min-width matching trigger, max-height 320px with scroll. Animates in over
`motion-base`.

**Option:** 36px height, 12px horizontal padding, `text-body`. Hover `surface-sunken`. Selected
`surface-selected` with a trailing `Check` (16px, `navy-600`). Keyboard focus uses the same visual
treatment as hover plus a 2px inset `navy-400` left bar.

**MultiSelect** uses checkboxes, keeps the panel open on selection, and shows a count in the
trigger ("Signal type: 3 selected"). Panels with more than 8 options include a filter input.

**Menu** groups actions with 1px `border-default` dividers; destructive items use
`status-risk`.

---

## 12. Tables

Component: `DataTable`.

| Element | Treatment |
|---|---|
| Container | `surface`, `border-default`, `rounded-lg`, overflow hidden |
| Header row | `surface-sunken`, `text-label`, `text-secondary`, 40px height, sticky |
| Body row | 52px height, `border-b border-default` (last row none) |
| Cell padding | 16px horizontal, 20px vertical |
| Cell text | `text-body-sm`, `text-primary` |
| Secondary cell text | `text-caption`, `text-secondary` |
| Row hover | `surface-sunken`, `cursor-pointer` when navigable |
| Selected row | `surface-selected`, 2px `navy-600` left border |
| Zebra striping | **Not used** — borders provide separation |

**Rules.** Numeric columns are right-aligned with `tabular-nums`. Date columns use
`MMM D, YYYY`; a missing date renders the "date unavailable" treatment (§37.2), never a blank cell
and never a placeholder date. Sortable headers show a 14px direction indicator; only one column
sorts at a time. Column count is capped at 7 — beyond that, move detail into the row detail view.
Actions occupy the final column, right-aligned, as `tertiary` icon buttons.

Tables scroll vertically within the page, not inside a fixed-height container, so the browser
scrollbar governs.

---

## 13. Cards

Component: `Card`, with `CardHeader`, `CardBody`, `CardFooter`.

| Property | Value |
|---|---|
| Background | `surface` |
| Border | 1px `border-default` |
| Radius | `rounded-lg` |
| Shadow | `shadow-xs` at rest, `shadow-sm` on hover when interactive |
| Padding | 24px |
| Header | `text-h3` title, optional `text-caption` `text-secondary` subtitle, optional right-aligned action |
| Header separation | 16px gap; a divider only when the body is a list or table |

**Variants**

| Variant | Treatment | Use |
|---|---|---|
| `default` | As above | Everything standard |
| `metric` | Same shell, `text-label` label above `text-metric` value | Dashboard metrics |
| `interactive` | Adds hover shadow, `cursor-pointer`, focus ring | Cards that navigate |
| `ai` | `surface-ai` background, `text-on-ai`, 3px `indigo-500` left border, AI label | AI-authored content only |
| `attention` | `border-l-4 border-status-opportunity` on a standard card | High-band opportunities |

An `ai` card never contains raw factual data presented as fact — it contains interpretation
(§18.1).

---

## 14. Badges

Component: `Badge`.

Base: `rounded-full`, 22px height, 10px horizontal padding, `text-caption` weight 500, optional
leading 12px icon or 6px dot.

| Style | Background | Text | Border |
|---|---|---|---|
| `solid-opportunity` | `amber-600` | white | none |
| `soft-opportunity` | `amber-50` | `amber-700` | `amber-100` |
| `soft-positive` | `green-50` | `green-700` | `green-100` |
| `soft-risk` | `red-50` | `red-700` | `red-100` |
| `soft-ai` | `indigo-100` | `indigo-700` | `indigo-200` |
| `soft-neutral` | `surface-sunken` | `neutral-600` | `border-default` |
| `outline-navy` | transparent | `navy-600` | `navy-200` |

**Rules.** Badge text is always meaningful on its own — a color-only badge is prohibited (§39).
Maximum two colored badges per row or card; beyond that, colour stops communicating. Signal type
badges always use `soft-neutral` plus the type's colored dot (§2.6, §20.1).

---

## 15. Alerts

Component: `Alert`. Inline, within page flow. Never used for transient feedback (that is a toast).

Layout: 20px icon, left-aligned, 12px gap; `text-body` weight 500 title; optional `text-body-sm`
description; optional right-aligned action. Padding 16px, `rounded-lg`, 1px border, 3px left
border in the accent color.

| Variant | Background | Border/Accent | Icon |
|---|---|---|---|
| `info` | `navy-50` | `navy-600` | `Info` |
| `success` | `green-50` | `green-600` | `CheckCircle2` |
| `attention` | `amber-50` | `amber-600` | `AlertTriangle` |
| `error` | `red-50` | `red-600` | `AlertCircle` |
| `ai` | `indigo-50` | `indigo-600` | `Sparkles` |
| `cached` | `surface-sunken` | `neutral-400` | `Archive` |

The `cached` variant is the standard treatment for fallback data notices (`FR-FB-03`, §37.3).

**Toasts** are separate: bottom-right, `surface`, `shadow-lg`, `rounded-lg`, max 400px,
auto-dismiss after 5s (errors persist until dismissed), maximum 3 stacked.

---

## 16. Tooltips

`surface-ai` background, `text-inverse`, `text-caption`, 8px/10px padding, `rounded-sm`,
`shadow-md`, max-width 280px, 6px offset, 150ms open delay, no close delay, `motion-fast` fade.

**Required on:** icon-only buttons, collapsed sidebar items, truncated text, abbreviated metric
labels, and every score factor name (explaining what the factor measures).

Tooltips carry supplementary information only. Anything required to understand the interface must
be visible without hovering, and tooltips are never the only place evidence appears.

---

## 17. Charts

Library: Recharts, per `AGENTS.md` §11.

### 17.1 Global chart style

| Element | Treatment |
|---|---|
| Container | Inside a standard `Card`; chart height 240px (standard), 320px (primary) |
| Grid | Horizontal lines only, `neutral-200`, 1px, `strokeDasharray="3 3"` |
| Axes | No axis lines; `text-caption` `text-secondary` labels |
| Y-axis | Maximum 5 ticks, abbreviated (`1.2k`) |
| Tooltip | Custom, matching §16 styling; never the Recharts default |
| Legend | Below the chart, `text-caption`, horizontal; omit when one series |
| Empty state | Chart region replaced by §35 empty state, never an empty axis frame |
| Animation | 240ms on mount only; no re-animation on data refresh |

### 17.2 Series colors

**Sequential/general charts**, in order: `navy-600`, `indigo-500`, `amber-500`, `green-600`,
`navy-300`, `violet-500`.

**Signal type charts** always use the §2.6 assignments so a type has one color product-wide.

### 17.3 Chart types

| Chart | Type | Where |
|---|---|---|
| Signal volume over time | Area, single series, 8% fill opacity | Dashboard, organization profile |
| Signal type distribution | Horizontal bar | Dashboard |
| Opportunity score distribution | Vertical bar, 4 band columns | Dashboard |
| Competitor/vendor activity | Horizontal bar | Dashboard |
| Score history | Sparkline, 64×24px, no axes | Opportunity detail |

Pie and donut charts are permitted only for the signal type distribution and only if a horizontal
bar proves insufficient — bars are preferred because seven categories are hard to read in a pie.
Gauges, radial progress rings, and 3D variants are forbidden (§1.1).

---

## 18. AI components

The visual language that separates machine-generated content from observed fact. This is the most
important component group in the product (P1).

### 18.1 The AI surface rule

Dark surface alone does **not** mean AI — the sidebar is dark and is structural. AI content is
identified by **three markers together**:

1. `surface-ai` background (or `surface-ai-subtle` for light inline regions)
2. A 3px `indigo-500` left border
3. A visible `AiLabel` (§18.2)

All three are required. Two out of three is not sufficient, because partial application is how the
distinction erodes.

### 18.2 `AiLabel`

An uppercase `text-label` marker with a 12px `Sparkles` icon, in `indigo-400` on dark surfaces or
`indigo-600` on light. Required text values, used verbatim:

| Context | Label |
|---|---|
| Any AI interpretation | `AI INTERPRETATION` |
| Score explanation | `AI EXPLANATION` |
| Correlation reasoning | `WHY THESE SIGNALS ARE CONNECTED` |
| Recommended action | `RECOMMENDED RESEARCH / ACTION` |
| Advisor answer | `AI SALES ADVISOR` |

### 18.3 `AiPanel`

`surface-ai`, `rounded-xl`, 24px padding, 3px `indigo-500` left border, `AiLabel` at top with 12px
gap to content. Body text `text-on-ai` at `text-body-lg`; metadata `text-on-ai-muted`. Links and
citations within use `indigo-300`.

### 18.4 `AiInlineNote`

The light-surface counterpart for short interpretation inside an otherwise factual card:
`surface-ai-subtle`, `border-ai`, `rounded-md`, 12px padding, `AiLabel`, `text-body-sm`
`neutral-700`.

### 18.5 `InsufficientEvidenceNotice`

Used whenever the system cannot support an answer (`FR-ADV-04`). Presented as a **designed state,
not an error**: `surface-sunken`, `border-default`, `rounded-lg`, 20px padding, 20px `SearchX` icon
in `neutral-500`, title "Insufficient evidence" in `text-body` weight 500, description in
`text-body-sm` `text-secondary` explaining what was searched, and a `secondary` action offering
"Run a scan" where relevant. Never red, never an alert, never a hidden component.

### 18.6 `AiUnavailableNotice`

When the provider fails (`TECHNICAL_PRD.md` §13): `surface-sunken` with a `status-neutral` icon,
"AI explanation unavailable", and the note that the score and evidence below are unaffected. The
factual content around it renders normally.

### 18.7 Forbidden AI treatments

No typing animation, no pulsing glow, no "thinking" orb, no gradient AI panels, no robot or brain
iconography, no chat avatar illustrations. AI presence is communicated by the three markers in
§18.1 and nothing else.

---

## 19. Opportunity components

### 19.1 `ScoreDisplay`

The single most important component. It is **structurally impossible to render a score alone**: the
component requires score, band, factor breakdown, and explanation as props, satisfying `FR-SCR-05`
by construction.

Layout, top to bottom:

```
┌──────────────────────────────────────────────────────┐
│ OPPORTUNITY SCORE                    ← text-label    │
│                                                      │
│   84 / 100        [ HIGH ]           ← text-score,   │
│                                        band badge    │
│   ───────────────────────────────    ← divider       │
│   SCORE FACTORS                      ← text-label    │
│   Procurement relevance   ████████░░  26 / 30        │
│   Related signal strength ███████░░░  19 / 25        │
│   Assessment relevance    ██████░░░░  14 / 20        │
│   Recency                 ████████░░  12 / 15        │
│   Source reliability      ██████████  10 / 10        │
│                                                      │
│ ┌──────────────────────────────────────────────────┐ │
│ │▌AI EXPLANATION                                   │ │  ← AiPanel
│ │ Explanation prose…                               │ │
│ └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

Specification: score value `text-score` in `text-primary`; "/ 100" in `text-h2` `text-secondary`;
band badge per §2.5. Factor rows are 32px tall with the name in `text-body-sm` `text-secondary`, a
6px `rounded-full` track in `surface-sunken` filled with `amber-500`, and the contribution as
`text-body-sm` `tabular-nums`. Factor names carry tooltips (§16). Bar widths are proportional to
contribution against the factor maximum, never against the total.

When score history exists (`FR-OPP-13`), a sparkline and a delta indicator ("+6 since Sep 14") sit
beside the score; the delta uses `status-neutral`, not green or red — a score movement is neither
healthy nor risky.

### 19.2 `OpportunityCard`

List representation. `interactive` card, plus `attention` left border when the band is High.
Contains: organization name (`text-h3`), organization type and state (`text-caption`
`text-secondary`), compact score (`text-metric` with band badge), contributing signal count with
type dots, most recent signal date, and a truncated one-line AI summary carrying an inline
`AiLabel`.

### 19.3 `CorrelationExplanation`

Renders why signals were connected (`FR-OPP-10`, `FR-COR-02`). An `AiPanel` with the
`WHY THESE SIGNALS ARE CONNECTED` label, followed by the reasoning, followed by the contributing
signals as a vertical list — each row a signal type dot, type name, date, and title, linking to
the signal detail.

A connector rail (1px `navy-200` vertical line with 8px dots) links the signal rows visually. This
is the only decorative line permitted in the product, because it encodes a real relationship.

### 19.4 `RecommendedAction`

An `AiPanel` with the `RECOMMENDED RESEARCH / ACTION` label, the recommendation in
`text-body-lg`, and an evidence reference row linking to the evidence it rests on (`FR-OPP-12`).
Never styled as a button or a task — it is advice to a human, and the interface must not imply the
system will act.

---

## 20. Signal components

### 20.1 `SignalTypeBadge`

`soft-neutral` badge with a 6px `rounded-full` dot in the type's color (§2.6), the 12px type icon
(§8.1), and the full type name. The type name is never abbreviated and never replaced by color
alone.

### 20.2 `SignalCard`

Left-aligned type icon in a 32px `surface-sunken` rounded square, then: title (`text-body`
weight 500), `SignalTypeBadge`, state badge, observed date or "date unavailable" (§37.2), source
count ("3 sources" when clustered), and a one-line factual summary in `text-body-sm`
`text-secondary`. Any AI summary carries an inline `AiLabel` and is visually separated
(`FR-SIG-14`).

### 20.3 `SignalStateBadge`

| State | Style | Label |
|---|---|---|
| `detected` | `soft-neutral` | Detected |
| `validated` | `soft-positive` | Validated |
| `rejected` | `soft-neutral`, `text-muted` | Rejected |
| `merged` | `outline-navy` | Merged |
| `superseded` | `soft-neutral`, `text-muted` | Superseded |

Rejected is deliberately **not** red: rejection is a correct system outcome, not a risk (§2.4
rule 4). A rejected signal displays its reason inline in `text-caption` `text-secondary`
(`FR-SIG-15`).

### 20.4 `SignalTimeline`

Vertical timeline for an organization's signal history. 1px `border-default` rail, 10px type-colored
dots, date markers in `text-label` `text-secondary`, grouped by month. Used on the organization
profile.

---

## 21. Evidence components

Evidence presentation is a product requirement (`FR-EV-01`–`FR-EV-07`), not a detail.

### 21.1 `EvidenceItem`

```
┌─────────────────────────────────────────────────────┐
│ SAM.gov                    Published Jun 14, 2026 ↗ │  ← source, date, link
│ ┌─────────────────────────────────────────────────┐ │
│ │ "…verbatim snippet from the source…"            │ │  ← quoted snippet
│ └─────────────────────────────────────────────────┘ │
│ Supports: procurement signal detected for this org  │  ← relationship
└─────────────────────────────────────────────────────┘
```

Source name in `text-body-sm` weight 500; date in `text-caption` `text-secondary`, or the
"date unavailable" treatment (§37.2); the snippet in `text-body-sm` `neutral-700` on
`surface-sunken` with a 2px `navy-200` left border and 12px padding; the relationship line in
`text-caption` `text-secondary` prefixed "Supports:"; and an `ExternalLink` opening the original
URL in a new tab (`FR-EV-05`). Snippets are truncated at 280 characters with an expand control —
never silently cut.

### 21.2 `EvidenceList`

Stacked `EvidenceItem`s with 12px gaps, headed by a count ("4 sources"). For a clustered signal,
**every** contributing source appears (`FR-EV-04`); there is no "show first source" mode.

### 21.3 `EvidenceDrawer`

Right-side drawer, 480px, `surface`, `shadow-lg`, slides in over `motion-slow`. Header states what
the evidence supports; body is an `EvidenceList`; a persistent close control and Escape both
dismiss it. Opened from any `View Evidence` affordance. The drawer never covers the item whose
evidence it shows on screens wider than 1280px — the content area shifts instead.

### 21.4 `SourceChip`

Compact inline reference: `soft-neutral` badge, 12px `FileText` icon, source name, opening the
evidence drawer on click. Used inline in Advisor answers as a numbered citation `[1]` and beneath
AI conclusions.

---

## 22. Navigation

Persistent left sidebar plus top header. No secondary top navigation, no breadcrumb bar except on
detail pages.

**Primary items:** Dashboard, Organizations, Signals, Opportunities, AI Advisor.

**Routes and titles**

| Route | Page title |
|---|---|
| `/` | Intelligence Command Center |
| `/organizations` | Organizations |
| `/organizations/:id` | *Organization name* |
| `/signals` | Signals |
| `/signals/:id` | Signal detail |
| `/opportunities` | Potential Opportunities |
| `/opportunities/:id` | *Organization name* — Potential Opportunity |
| `/advisor` | AI Sales Advisor |
| `/login` | — |

Detail pages show a back affordance and a breadcrumb in `text-caption` `text-secondary`
("Organizations / Riverside Unified"). Breadcrumbs never exceed two levels.

---

## 23. Sidebar

| Property | Value |
|---|---|
| Width | 260px expanded, 72px rail |
| Background | `navy-800` |
| Border | 1px `navy-700` right |
| Logo area | 64px, matching header height, `navy-900` |
| Item height | 44px |
| Item padding | 12px horizontal, 12px from sidebar edge |
| Item text | `text-body` weight 500, `navy-300` |
| Item icon | 20px, `navy-300` |
| Hover | `navy-700` background, text `neutral-0` |
| Active | `navy-900` background, text `neutral-0`, 3px `indigo-500` left bar |
| Section label | `text-label` `navy-400`, 24px top margin |

The active indicator is the one structural use of indigo outside AI content, and it is justified:
it marks position, not intelligence. The AI Advisor item additionally carries a `Sparkles` icon so
the AI destination reads as AI.

Footer region: user name, role badge (`outline-navy`, "Sales Representative" / "Sales Manager"),
and a sign-out action.

Below 1280px the sidebar collapses to the icon rail with tooltips; below 1024px it becomes an
overlay drawer opened from the header.

---

## 24. Header

64px, `surface`, 1px `border-default` bottom, sticky at z-20, 24px horizontal padding.

**Left** — page title in `text-h1`, with breadcrumb above on detail pages.

**Center** — global organization search (§30), 420px, collapsing to an icon below 1280px.

**Right**, in order:

1. `ScanStatusIndicator` — a status dot plus `text-caption` label: `status-positive` "All scans
   current"; `status-ai` with a 1.5s pulse "Scan running"; `status-opportunity` "Partial — 1 source
   failed"; `status-risk` "Last scan failed"; `text-muted` "No scans yet". Clicking opens the scan
   status popover (`FR-DASH-04`).
2. Notifications — deferred; not in MVP.
3. User menu — initials avatar in `navy-100`/`navy-700`, opening a `Menu` with name, email, role,
   and sign out.

---

## 25. Dashboard — Hybrid Intelligence Command Center

The approved direction is command-centre overview **plus** actionable opportunity focus. The layout
resolves that by giving the top band to situational awareness and the largest region to the
prioritized opportunity list.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Intelligence Command Center                          [ Scan All ]      │
├────────────┬────────────┬────────────┬─────────────────────────────────┤
│ POTENTIAL  │ SIGNALS    │ COMPETITOR │ SCAN STATUS                     │
│ OPPS       │ (30 DAYS)  │ ACTIVITY   │ ● All scans current             │
│ 12         │ 148        │ 9          │ Last: Today 06:00               │
│ 4 high ▲2  │ 7 types    │ 3 new      │ 18 orgs · 0 failed              │
├────────────┴────────────┴────────────┴─────────────────────────────────┤
│ PRIORITIZED POTENTIAL OPPORTUNITIES        │ AI INSIGHTS               │
│ ┌────────────────────────────────────────┐ │ ┌───────────────────────┐ │
│ │▌Riverside Unified SD      84 [HIGH]    │ │ │▌AI INTERPRETATION     │ │
│ │  4 signals ●●●●  ·  updated 2d ago     │ │ │ Interpretation text…  │ │
│ └────────────────────────────────────────┘ │ │ [1] [2]               │ │
│ ┌────────────────────────────────────────┐ │ └───────────────────────┘ │
│ │  State University          71 [MEDIUM] │ │                           │
│ └────────────────────────────────────────┘ │ SIGNAL ACTIVITY           │
│                        [ View all ]        │ ┌───────────────────────┐ │
│                                            │ │ area chart, 30 days   │ │
│ SIGNAL TYPE DISTRIBUTION                   │ └───────────────────────┘ │
│ ┌────────────────────────────────────────┐ │ RECENT SIGNALS            │
│ │ horizontal bars, 7 types               │ │ compact list, 6 items     │
│ └────────────────────────────────────────┘ │                           │
└────────────────────────────────────────────┴───────────────────────────┘
```

**Structure.** Metric row: 4 equal columns, `metric` cards, 24px gutters. Below: two columns at
`2xl` and `xl` in a 2:1 ratio (main 66%, rail 33%), stacking below `lg`.

**Metric cards** (`FR-DASH-01`–`FR-DASH-04`): `text-label` label, `text-metric` value, and a
`text-caption` `text-secondary` sub-line. Each is clickable and navigates to the filtered list
behind it (`FR-DASH-08`). Trend indicators use a 12px arrow with `status-neutral` text — never
green/red, since more signals is neither healthy nor risky.

**Prioritized opportunities** (`FR-DASH-05`): `OpportunityCard` list in descending score order,
maximum 5, with "View all".

**AI insights** (`FR-DASH-07`): `AiPanel` in the rail with citations. If insufficient data exists,
`InsufficientEvidenceNotice` renders in its place (§18.5) — the panel is never hidden.

**Signal activity** (`FR-DASH-06`): 30-day area chart plus a compact recent signal list.

**Competitor/vendor activity** (`FR-DASH-03`): derived from type 6 signals; the metric card links
to signals filtered to that type.

**Cached data** (`FR-DASH-09`): if any displayed figure derives from the fallback dataset, a
`cached` alert sits directly below the page title, and affected cards carry an `Archive` icon with
a tooltip stating the original retrieval date.

**Empty dashboard** (`FR-DASH-10`): metric cards render with an em-dash and "No data yet"; the main
region shows the §35 empty state with a "Scan an organization" action. No fabricated placeholder
figures, ever.

**Role differences.** Approved: both `SALES_REP` and `SALES_MANAGER` see every tracked organization
and the same dashboard (`PRODUCT_PRD.md` `FR-ROLE-04`). There is no scoped metric row and no
manager-only screen. The signed-in role is shown in the sidebar so the user knows which role they
hold; it does not change the data.

---

## 26. Organization profile

```
┌────────────────────────────────────────────────────────────────────────┐
│ ‹ Organizations / Riverside Unified School District                    │
│ Riverside Unified School District          [ Ask Advisor ] [ Scan Now ]│
│ K-12 District · California · riversideunified.org ↗                    │
│ Last scanned: Today 06:04 · 4 of 4 sources                             │
├────────────────────────────────────────────────────────────────────────┤
│ INSTITUTIONAL REFERENCE (NCES IPEDS)                    Reference data │
│ Enrollment 42,180 · Locale Suburban · Source IPEDS 2024 ↗              │
├──────────────────────────────────────────┬─────────────────────────────┤
│ [ Signals ] [ Opportunities ] [ Timeline]│ AI SUMMARY                  │
│                                          │ ┌─────────────────────────┐ │
│ filter bar: type · date · state          │ │▌AI INTERPRETATION       │ │
│ ┌──────────────────────────────────────┐ │ │ Summary with citations  │ │
│ │ SignalCard                           │ │ └─────────────────────────┘ │
│ │ SignalCard                           │ │ SIGNAL VOLUME               │
│ └──────────────────────────────────────┘ │ ┌─────────────────────────┐ │
│                                          │ │ area chart              │ │
└──────────────────────────────────────────┴─────────────────────────────┘
```

**Identity header** (`FR-ORG-01`): name in `text-h1`; type, state, and website in `text-body-sm`
`text-secondary` with the website as an external link. Scan metadata (`FR-ORG-07`) in
`text-caption` `text-muted`, naming sources covered.

**Reference band** (`FR-ORG-02`): a distinct `surface-sunken` strip, **not** a card, carrying the
`text-label` heading "INSTITUTIONAL REFERENCE (NCES IPEDS)" and a right-aligned `soft-neutral`
badge reading "Reference data". The visual demotion is deliberate: IPEDS is enrichment, never a
signal (`FR-DATA-07`), and it must not be mistaken for detected activity.

**Tabs**: Signals (`FR-ORG-03`), Opportunities (`FR-ORG-04`), Timeline. Tab style: 40px height,
`text-body` weight 500, `text-secondary` inactive, `navy-600` active with a 2px `navy-600`
underline, 1px `border-default` rail beneath.

**Rail**: AI summary (`AiPanel` with citations), signal volume chart, and a source coverage list
showing each approved source with its last successful retrieval and any failure.

**Empty** (`FR-ORG-08`): "No signals detected yet" with a description clarifying that this means
nothing observable was found in approved public sources — not that collection failed — and a
"Scan Now" action.

---

## 27. Opportunity details

Two columns: 66% main, 33% evidence rail. The rail is the point — evidence sits permanently beside
the conclusion rather than behind a click.

**Order of the main column, which encodes the four layers top to bottom (`FR-OPP-14`):**

1. **Header** — organization name (`text-h1`), a `soft-opportunity` "Potential Opportunity" badge,
   organization type and state, created and updated dates, and `Ask Advisor` (`FR-OPP-15`).
2. **`ScoreDisplay`** (§19.1) — score, band, factor breakdown, AI explanation (`FR-OPP-07`,
   `FR-OPP-08`, `FR-OPP-13`).
3. **Observed signals** — `text-label` "OBSERVED SIGNALS" over a `SignalCard` list on white
   surfaces. This region is factual and carries no AI styling (`FR-OPP-09`).
4. **`CorrelationExplanation`** (§19.3) — AI panel (`FR-OPP-10`).
5. **`RecommendedAction`** (§19.4) — AI panel (`FR-OPP-12`).

The alternation is intentional and must be preserved: white factual regions, dark AI regions, in
that repeating order. A reader scrolling the page sees the boundary between fact and interpretation
without reading a word.

**Evidence rail** (`FR-OPP-11`): sticky `EvidenceList` of every evidence item behind the
opportunity, grouped by signal, headed by a total count. Below 1280px it becomes the
`EvidenceDrawer` opened from a "View all evidence" button.

**Required copy.** The page never uses "opportunity" unqualified — it is always "potential
opportunity" (`FR-OPP-05`). Forbidden phrasings: "will issue", "expected RFP", "confirmed
opportunity", "guaranteed".

---

## 28. Signal details

Single column, max-width 960px, with evidence inline rather than in a rail — a signal is small
enough that separation would be artificial.

1. **Header** — `SignalTypeBadge`, `SignalStateBadge`, title (`text-h1`), organization link, and
   observed/published date or the "date unavailable" treatment (`FR-SIG-09`, `FR-SIG-10`).
2. **Observed content** (`FR-SIG-14`) — `text-label` "WHAT THE SOURCE STATED" over the extracted
   factual content on a white surface.
3. **AI summary** — `AiInlineNote`, present only when one exists, clearly separated from 2.
4. **Sources** (`FR-SIG-11`, `FR-SIG-12`) — `text-label` "SOURCES (3)" over the full
   `EvidenceList`. When the signal is clustered, an `info` alert states that these sources describe
   the same event and were merged.
5. **Contributing to** (`FR-SIG-13`) — linked `OpportunityCard`s, or an explicit "This signal does
   not currently contribute to any potential opportunity", which is informative rather than empty.
6. **Rejection reason** (`FR-SIG-15`) — for rejected signals, a `soft-neutral` panel at the top
   stating why, so the user sees it before the content.

---

## 29. AI Sales Advisor

Available in two forms sharing one component: a full page at `/advisor`, and a 440px right-side
panel opened from an organization or opportunity (`FR-ORG-05`, `FR-OPP-15`). The panel is preferred
in context because it keeps the evidence visible beside the answer.

**Scope indicator.** A persistent bar at the top of the conversation shows the active scope —
`soft-ai` badge reading "Riverside Unified School District" — so the user always knows what the
Advisor can see (`FR-ADV-01`). Follow-up questions retain scope without restating it.

**User message.** Right-aligned, `navy-50` background, `navy-900` text, `rounded-lg` with a squared
bottom-right corner, max-width 80%.

**Advisor message.** Full width, `AiPanel` treatment with the `AI SALES ADVISOR` label. Body at
`text-body-lg`, `max-w-[68ch]`. Inline citations render as `SourceChip` numbered markers `[1]`
`[2]` in `indigo-300`, opening the `EvidenceDrawer` (`FR-ADV-03`). Beneath the answer sits a
`text-label` "SOURCES" row with a compact `SourceChip` list.

**Fact versus inference** (`FR-ADV-06`). The Advisor must mark inference inline. Sentences derived
from sources carry citations; interpretive sentences are prefixed with an italic
`text-on-ai-muted` marker "Interpretation:". A paragraph with neither is not permitted.

**Insufficient evidence** (`FR-ADV-04`). Renders `InsufficientEvidenceNotice` (§18.5) in place of an
answer, stating what was searched. This is a normal, non-error outcome and must look like a
considered response.

**Out of scope** (`FR-ADV-07`). A plain `AiPanel` response declining and naming what the Advisor
can answer about. Never an error state.

**Pending state.** A 3-dot indicator in `indigo-400` with `AI SALES ADVISOR` already visible, plus
the text "Searching evidence…" then "Composing answer…". No typing animation, no glow (§18.7).

**Suggested questions.** When a conversation is empty, show 4 `secondary` buttons drawn from the
question categories in `PRODUCT_PRD.md` §15 — a real discoverability aid, since users will not
guess what the Advisor can do.

**Input.** Pinned to the bottom, `Textarea` auto-growing from 40px to 120px, `ai` variant send
button, Enter to send and Shift+Enter for newline. Disabled with an explanatory note while a
response is pending.

---

## 30. Search

**Global search** sits in the header and covers organizations only (`FR-SRCH-01`, `FR-SRCH-08`).

Trigger: 420px `Input` with a leading `Search` icon, placeholder "Search organizations", and a
`⌘K` / `Ctrl K` hint chip in `text-caption` `text-muted`.

Results panel: `shadow-md`, `rounded-md`, max-height 400px, opening after 2 characters with a
250ms debounce. Each result is 52px tall showing organization name (`text-body` weight 500) with
the matched substring in weight 600, and type plus state in `text-caption` `text-secondary`, and a
right-aligned signal count. Keyboard navigation with arrows, Enter to open, Escape to dismiss.

States: fewer than 2 characters shows a hint; searching shows 3 skeleton rows; no matches shows
"No organizations found" with a note that search covers tracked organizations only, which is the
honest explanation of `FR-SRCH-08` rather than a dead end.

**List search** within Signals and Opportunities is a filter-bar input scoped to that list, not the
global component.

---

## 31. Filters

A `FilterBar` sits directly beneath the page title, inside a `surface` container with
`border-default` and `rounded-lg`, 16px padding, controls in a row with 12px gaps, wrapping below
`lg`.

| Page | Filters |
|---|---|
| Signals | Signal type (multi), organization, date range, lifecycle state (`FR-SRCH-02`) |
| Opportunities | Score band (multi), organization, organization type, date, US state (`FR-SRCH-03`, `FR-SRCH-05`) |
| Organizations | Organization type, US state, has opportunities |

Sorting sits at the right of the bar as a `Select` (`FR-SRCH-04`): "Score, high to low" and "Most
recent".

**Active filters** render as removable `soft-neutral` chips below the bar, each with a 12px `X`,
alongside a "Clear all" `link` button and a result count in `text-body-sm` `text-secondary`
("18 signals"). Filter state lives in Zustand and is reflected in the URL query string so a filtered
view can be shared — which matters for a manager pointing a rep at something.

Empty results render the §35 empty state with a "Clear filters" action (`FR-SRCH-06`).

---

## 32. Scan Now interaction

Trigger: `secondary` button with a `RefreshCw` icon, labelled "Scan Now", on the organization
profile header (`FR-ORG-06`). The dashboard carries "Scan All" as a `secondary` button.

Interaction sequence:

1. **Idle** — enabled, with a `text-caption` `text-muted` sub-line showing the last scan time.
2. **Triggered** — the button enters loading state immediately; the `ScanProgress` panel (§33)
   appears directly beneath the header with a `motion-base` expand.
3. **Already running** — if a scan is already active for this organization
   (`TECHNICAL_PRD.md` §7.3), the button shows "Scan in progress" disabled, and the UI attaches to
   the existing run rather than reporting an error.
4. **Rate limited** — an `attention` toast stating when the next scan may be triggered
   (`FR-SCAN-06`). The constraint is explained, never silently enforced.
5. **Complete** — `ScanProgress` transitions to the result summary (§33.3) and the affected queries
   refresh.

The interface never blocks. The user can navigate away during a scan; returning to the organization
reattaches to the run.

**Scan All** (approved) lives on the dashboard as a `secondary` button. It starts a scan for every
tracked organization and opens a batch panel, not the single-organization stepper. The panel lists
each organization with a status of pending, running, complete, partial, or failed. Selecting a
running row shows that organization's stage stepper (§33.1) and per-source rows (§33.2). The batch
obeys the same rate limits as a single scan; the button shows how many organizations are still
outstanding ("Scanning 4 of 16"). Completion summarises new signals, updated opportunities, score
movements, and any failed sources across the batch.

---

## 33. Scan progress state

Satisfies `FR-SCAN-03`–`FR-SCAN-05`. Rendered as a `Card` beneath the organization header.

### 33.1 Stage indicator

A horizontal stepper of the six user-visible stages, mapped from the pipeline in
`TECHNICAL_PRD.md` §21:

```
● Collecting ─── ● Extracting ─── ◐ Validating ─── ○ Deduplicating ─── ○ Correlating ─── ○ Scoring
   complete        complete          active            pending            pending          pending
```

| Stage state | Treatment |
|---|---|
| Complete | `status-positive` filled dot, `text-body-sm` `text-secondary` label |
| Active | `status-ai` dot with a 1.5s pulse, label `text-body-sm` weight 500 `text-primary` |
| Pending | `neutral-300` hollow dot, `text-muted` label |
| Failed | `status-risk` dot with an `AlertCircle`, label `status-risk` |

The connecting rail is 2px, filled `status-positive` behind completed stages and `neutral-200`
ahead. An indeterminate 2px `indigo-500` bar sits beneath the active stage. The pulse is the only
pulsing element permitted in the product.

### 33.2 Per-source status

Beneath the stepper, one row per approved source: source name, status icon, and a `text-caption`
detail — "SAM.gov · 12 records"; "State DOE site · failed: timeout after 30s" in `status-risk`.
A failed source never stops the display of the others (`FR-SCAN-05`).

### 33.3 Result summary

On completion, the panel becomes a result summary (`FR-SCAN-04`):

| Outcome | Treatment |
|---|---|
| Changes found | `success` alert: "Scan complete — 3 new signals, 1 signal updated, 1 potential opportunity updated (score 78 → 84)" |
| No changes | `info` alert: "Scan complete — no new signals found." Explicitly a success (`FR-SCAN-09`) |
| Partial | `attention` alert naming which sources failed and what was still collected |
| Failed | `error` alert naming the reason, with a retry action |
| Interrupted | `attention` alert: "Scan interrupted — the server restarted during this scan", with retry |

Score movements render as "78 → 84" in `tabular-nums` with a `status-neutral` arrow. The summary
persists until dismissed or until the next scan.

---

## 34. Loading states

Skeletons, not spinners, for anything with known structure. A spinner communicates nothing about
what is arriving.

| Context | Treatment |
|---|---|
| Page load | Skeleton layout matching the real structure: header bar, metric row, card placeholders |
| Card content | Skeleton lines at the real text sizes, 60–90% widths, varied |
| Table | 5 skeleton rows at true row height |
| Chart | `surface-sunken` block at true chart height with a centered `text-caption` "Loading…" |
| Metric value | Skeleton block at `text-metric` dimensions |
| Button action | In-button spinner, label retained, width held |
| Advisor response | Pending state per §29 |
| Inline refresh | 2px `indigo-500` bar at the top of the affected card; existing data stays visible |

Skeleton style: `surface-sunken` fill, `rounded-sm`, 1.5s shimmer of a `neutral-200` gradient,
disabled under `prefers-reduced-motion` in favour of a static fill.

**Rules.** Data already loaded is never replaced by a skeleton on refetch — refreshing keeps the
stale value visible with the inline indicator. Layout must not shift when real content arrives, so
skeletons occupy true dimensions.

---

## 35. Empty states

Component: `EmptyState`. Centered, 64px vertical padding, containing a 32px icon in `neutral-400`
inside a 64px `surface-sunken` circle, a `text-h3` title, a `text-body-sm` `text-secondary`
description capped at 48ch, and an optional primary action.

| Context | Title | Description | Action |
|---|---|---|---|
| No scans yet (dashboard) | No intelligence collected yet | Run a scan to collect public information about a tracked organization. | Scan an organization |
| No signals (organization) | No signals detected yet | Nothing observable was found in the approved public sources for this organization. | Scan Now |
| No opportunities (organization) | No potential opportunities yet | Potential opportunities appear when multiple related signals are detected. | — |
| Filtered to nothing | No results match these filters | Try widening the date range or clearing a filter. | Clear filters |
| No search results | No organizations found | Search covers organizations tracked by the system. | — |
| Empty conversation | Ask about this organization | The Advisor answers from collected evidence about this organization. | Suggested questions |
| Signal in no opportunity | Not part of a potential opportunity | This signal has not been correlated with other signals yet. | — |

**Rules.** Empty is never blank. The copy distinguishes "nothing was found" from "nothing was
collected" — the first is a product answer, the second is a prompt to act (P5). No illustrations
beyond the single icon.

---

## 36. Error states

Scoped to the smallest region that failed. A failed chart never blanks the page.

| Scope | Treatment |
|---|---|
| Page | Centered `error` state: `AlertCircle` at 32px, `text-h2` "Something went wrong", `text-body-sm` description, Retry primary and Back secondary |
| Section / card | `error` alert inside the card shell, retaining the card title, with an inline Retry |
| Inline value | An em-dash with a tooltip stating why the value is unavailable |
| Form | Field-level messages in `text-caption` `status-risk` beneath each field, plus a summary alert |
| Network | Toast: "Connection lost. Retrying…" then a success toast when restored |
| 401 unauthenticated | Redirect to login with a `text-body-sm` note that the session expired |
| 403 unauthorized | Page-level state: "You do not have access to this view", no retry |
| 404 | Page-level state naming what was not found, with a link back to the relevant list |
| 500 | Page-level state with a reference identifier for the failed request |

**Error copy rules.** State what failed, in plain language, and what the user can do. Never expose
stack traces, internal identifiers beyond a reference code, or provider names. Never use humour.
Never blame the user.

**Source failure is not an error state** — it is scan result data and uses §33.2 and §33.3
(`FR-SCAN-05`).

---

## 37. No-evidence and data-integrity states

The states that keep the product honest. Each is a designed component, never an absence.

### 37.1 Insufficient evidence

`InsufficientEvidenceNotice` (§18.5), used wherever an AI conclusion cannot be supported
(`FR-ADV-04`). Neutral, not red. The component is always rendered — a hidden AI panel would
silently convert "we don't know" into "nothing to see", which is exactly the failure P1 exists to
prevent.

### 37.2 Date unavailable

When a source provides no publication or observed date (`FR-EV-02`, `FR-SIG-04`), render a 12px
`CalendarOff` icon with the `text-caption` `text-muted` label "Date unavailable", carrying a
tooltip "This source did not publish a date." Never show a blank, an em-dash, the retrieval date
in its place, or an inferred date.

### 37.3 Cached / fallback data

Whenever displayed data derives from the fallback dataset (`FR-FB-03`): a `cached` alert (§15) at
the top of the affected region reading "Showing cached data from [date] — [source] was unavailable
during the last scan", and an `Archive` icon on each affected card with a tooltip giving the
original retrieval date. The label is never suppressed, and cached data is never styled to look
live.

### 37.4 AI unavailable

`AiUnavailableNotice` (§18.6). The surrounding factual content — score, signals, evidence —
renders normally, because none of it depends on the model.

### 37.5 Partial results

When a scan completed with some sources failing, affected lists carry an `attention` alert:
"These results are incomplete — 1 of 4 sources failed during the last scan", linking to the scan
detail. Incomplete data is never presented as complete.

---

## 38. Responsive behavior

Desktop-first. Mobile applications are out of scope (`AGENTS.md` §13); the product degrades
gracefully to tablet and remains usable, not optimised, below that.

| Breakpoint | Width | Behaviour |
|---|---|---|
| `2xl` | ≥1536px | Full layout, content capped at 1440px |
| `xl` | 1280–1535px | Full layout; evidence rail becomes a drawer on opportunity detail |
| `lg` | 1024–1279px | Sidebar collapses to the 72px rail; dashboard columns stack; metric row becomes 2×2 |
| `md` | 768–1023px | Sidebar becomes an overlay drawer; header search collapses to an icon; tables become stacked rows |
| `sm` | <768px | Single column; metric cards stack; Advisor becomes full screen; functional but not optimised |

**Table-to-card transformation** below `md`: each row becomes a bordered block with `text-label`
field names above values, preserving every column as a labelled line rather than hiding columns.

**Touch targets** are at least 44×44px below `lg`, which increases button and row heights at those
breakpoints.

**Never hidden at any width:** opportunity scores, band labels, evidence access, AI labels, and the
cached-data indicator. Responsive rules may re-flow the interface; they may not remove the
information that makes it honest.

---

## 39. Accessibility basics

Target: WCAG 2.1 AA for the MVP.

**Contrast.** All token pairings in this document meet 4.5:1 for body text and 3:1 for large text
and interface boundaries. `text-secondary` (`neutral-500`) on `surface` and `text-on-ai`
(`#E8EBF5`) on `surface-ai` both pass. `text-muted` (`neutral-400`) is permitted only for
non-essential metadata at `text-caption`, never for meaningful content.

> NEEDS VERIFICATION — contrast ratios for `amber-600` on `amber-50` and `indigo-600` on
> `indigo-50` must be measured during implementation; if either falls short, use the `-700` shade
> for text. The palette is designed to allow that substitution without visual change elsewhere.

**Never color alone** (P3, and a hard requirement): every score band shows its text label; every
signal type shows its name; every status dot has adjacent text; every chart series is labelled or
legended. A user with a colour vision deficiency must lose nothing.

**Keyboard.** Every interactive element is reachable and operable by keyboard in a logical order.
Focus is always visible (`ring-2 ring-focus-ring ring-offset-2`) and is never suppressed. Modals
and drawers trap focus, close on Escape, and return focus to their trigger. A skip-to-content link
precedes the sidebar.

**Semantics.** Landmark elements for header, navigation, and main; one `h1` per page with correct
heading order; tables use real `th` with scope; every input has an associated label; icon-only
controls carry `aria-label`; external links announce that they open in a new tab.

**Live regions.** Scan progress announces stage changes politely; toasts use an appropriate live
role; the Advisor announces when an answer has arrived. Nothing announces more than once per
change.

**Motion.** `prefers-reduced-motion` disables the skeleton shimmer, stage pulse, and all
transitions, replacing them with immediate state changes.

---

## 40. Component inventory

Exact names, so three developers build one library rather than three. Anything not on this list
requires agreement before it is created.

| Group | Components |
|---|---|
| Primitives | `Button` `IconButton` `Input` `Textarea` `Select` `MultiSelect` `Menu` `Checkbox` `Badge` `Alert` `Toast` `Tooltip` `Card` `Skeleton` `Spinner` `Tabs` `Modal` `Drawer` `Pagination` |
| Layout | `AppShell` `Sidebar` `Header` `PageHeader` `Breadcrumb` `ContentGrid` |
| Data | `DataTable` `MetricCard` `EmptyState` `ErrorState` `FilterBar` `FilterChip` `SortSelect` |
| Charts | `AreaChartCard` `BarChartCard` `ScoreDistributionChart` `Sparkline` `ChartTooltip` `ChartEmpty` |
| AI | `AiLabel` `AiPanel` `AiInlineNote` `InsufficientEvidenceNotice` `AiUnavailableNotice` |
| Opportunity | `ScoreDisplay` `ScoreBandBadge` `FactorBreakdown` `OpportunityCard` `CorrelationExplanation` `RecommendedAction` `ScoreHistorySparkline` |
| Signal | `SignalCard` `SignalTypeBadge` `SignalStateBadge` `SignalTimeline` `SignalTypeDot` |
| Evidence | `EvidenceItem` `EvidenceList` `EvidenceDrawer` `SourceChip` `DateUnavailable` `CachedDataNotice` |
| Scan | `ScanNowButton` `ScanProgress` `ScanStageStepper` `ScanSourceStatus` `ScanResultSummary` `ScanStatusIndicator` |
| Advisor | `AdvisorPanel` `AdvisorMessage` `AdvisorInput` `AdvisorScopeBar` `SuggestedQuestions` |
| Search | `GlobalSearch` `SearchResultItem` |

---

## 41. Consistency checklist

Applied before any UI pull request is approved.

- [ ] No hex value, arbitrary spacing, or font size outside this document
- [ ] Semantic tokens used, not raw palette scales
- [ ] Indigo appears only on AI content and the active navigation indicator
- [ ] Amber appears only for opportunity or attention
- [ ] Every AI region carries all three markers from §18.1
- [ ] No score rendered without band, factor breakdown, and explanation
- [ ] Every AI conclusion reaches its evidence in one interaction
- [ ] Missing dates use the §37.2 treatment, never blanks or inferred dates
- [ ] Cached data is labelled wherever it appears
- [ ] Loading, empty, error, and insufficient-evidence states implemented for every data view
- [ ] Copy says "potential opportunity" and "may indicate"; no certainty language
- [ ] Meaning never conveyed by color alone
- [ ] Keyboard reachable with a visible focus ring
- [ ] No forbidden pattern from §1.1

---

## Open questions

| # | Question | Section | Status |
|---|---|---|---|
| U1 | `lucide-react` as the icon set | §8 | **Decided:** yes |
| U2 | Verify contrast for `amber-600`/`amber-50` and `indigo-600`/`indigo-50` | §39 | Measure at implementation; fall back to `-700` text shades |
| U3 | Is the Advisor primarily a contextual panel or a full page? | §29 | Both, sharing one component; prioritise the panel, since evidence stays visible |
| U4 | Does the Sales Manager need a distinct screen? | §25 | **Decided:** no. Both roles see the same screens and the same organizations |
| U5 | Pie/donut permitted for signal type distribution? | §17.3 | No — horizontal bars read better with seven categories |

> Also resolved: typeface is Inter (§3.1). The 0–24 score band is labelled **Monitor**, matching
> `PRODUCT_PRD.md` §13.3. Sign-in is Clerk's interface, themed toward navy and Inter as far as
> Clerk allows; the application shell after sign-in follows this document. Login layout is
> specified in `AUTHENTICATION.md`, not here.
