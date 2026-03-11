# DESIGN.md

Design system reference for auto-invest. Covers all surfaces: web frontend, emails, and any future frontends.

---

## Logos

| File | Use case |
|---|---|
| `core/assets/logo_trans.png` | Transparent background — use on light backgrounds |
| `core/assets/logo_white.png` | White version — use on dark/colored backgrounds |
| `web/src/assets/logo.png` | Web frontend (light mode) |
| `web/src/assets/logo_white.png` | Web frontend sidebar (dark header) |

The sidebar renders the logo at `h-9 w-9` (36px). Emails embed it as `cid:logo` at 68×68px.

---

## Color Palette

### Primary (Blue)

The brand color is a deep blue. It appears as `#1e3a8a` in emails and as `oklch(0.379 0.146 265.522)` in the web (same perceptual blue, different color space).

| Role | Email (hex) | Web (oklch) |
|---|---|---|
| Primary / header background | `#1e3a8a` | `oklch(0.379 0.146 265.522)` |
| Primary foreground | `#ffffff` | `oklch(0.985 0 0)` |
| Light blue accent / subtitle | `#93c5fd` | — |
| Page background | `#f0f4ff` | `oklch(1 0 0)` (white) |
| Card background | `#ffffff` | `oklch(1 0 0)` |

### Web-only tokens (CSS custom properties in `web/src/index.css`)

```
--primary:            oklch(0.379 0.146 265.522)   /* deep blue */
--accent:             oklch(0.94 0.03 265)          /* light blue tint */
--sidebar:            oklch(0.379 0.146 265.522)    /* same as primary */
--sidebar-primary:    oklch(0.55 0.22 258)
--muted:              oklch(0.97 0 0)
--destructive:        oklch(0.58 0.22 27)           /* red */
--border:             oklch(0.922 0 0)
--radius:             0.625rem
```

### Chart colors (5 shades of blue, light → dark)

| Token | Value |
|---|---|
| `--chart-1` | `oklch(0.809 0.105 251.813)` |
| `--chart-2` | `oklch(0.623 0.214 259.815)` |
| `--chart-3` | `oklch(0.546 0.245 262.881)` |
| `--chart-4` | `oklch(0.488 0.243 264.376)` |
| `--chart-5` | `oklch(0.424 0.199 265.638)` |

### Status badge colors (web)

| Status | Style |
|---|---|
| `FILLED` | green-100 / green-800 / green-200 border |
| `FINISHED` | blue-100 / blue-800 / blue-200 border |
| `CREATED` | gray-100 / gray-700 / gray-200 border |
| `FAILED` | red-100 / red-800 / red-200 border |
| `SUBMITTED` | yellow-100 / yellow-800 / yellow-200 border |
| `CANCELLED` | orange-100 / orange-800 / orange-200 border |

---

## Typography

| Surface | Font |
|---|---|
| Web | **Geist Variable** (`@fontsource-variable/geist`), sans-serif fallback |
| Emails | `Arial, Helvetica, sans-serif` |

### Email type scale

| Role | Size | Weight | Color |
|---|---|---|---|
| Eyebrow label | 11px | 600 | `#93c5fd` (uppercase, 2px letter-spacing) |
| Page title (h1) | 24px | 700 | `#ffffff` |
| Subtitle / date | 15px | 400 | `#93c5fd` |
| Section heading (h2) | 14px | 700 | `#1e3a8a` (uppercase, 1px letter-spacing) |
| Body / table text | 12–13px | 400 | `#374151` / `#111827` |
| Footer | 12px | 400 | `#9ca3af` |

---

## Email Layout

- Max width: **600px**, centered
- Outer background: `#f0f4ff`
- Card: white, `border-radius: 8px`, `box-shadow: 0 2px 12px rgba(30,58,138,0.10)`
- Header: `#1e3a8a` with 28px top/bottom padding, 40px left padding
- Content sections: 40px horizontal padding
- Table header rows: `background-color: #dbeafe` (light blue)

### Email templates (`core/templates/emails/`)

| File | Purpose |
|---|---|
| `investment_confirmation.html` | Sent after each successful investment run |
| `balance_alert.html` | Low balance warning |
| `btc_withdrawal_confirmation.html` | BTC withdrawal notification |
| `error_alert.html` | Error/failure alert |
| `monthly_summary.html` | Monthly portfolio summary |

---

## Web Component Conventions

- **UI library:** shadcn/ui (components in `web/src/components/ui/`)
- **Shared components:** `web/src/components/shared/` — e.g. `StatusBadge`
- **Layout:** `web/src/components/layout/` — `AppSidebar`, `Layout`
- **Icons:** Lucide React

### Number formatting

Always use `formatNumber(value)` from `@/lib/utils`. It formats with **non-breaking spaces** as thousand separators (e.g. `1 234 567`). For decimals: `formatNumber(value, 2)`.

Never use `.toLocaleString()` or `.toFixed()` directly for display values.

---

## Dark Mode

The web supports dark mode via the `.dark` class. All semantic tokens (`--primary`, `--background`, etc.) have dark overrides defined in `web/src/index.css`. The sidebar in dark mode uses `oklch(0.28 0.13 265)` as its background.
