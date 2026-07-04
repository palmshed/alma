# Palmshed Design Tokens

One visual language across all Palmshed products.
React is the reference implementation. Static/Jinja mirrors React exactly.
No implementation-specific styling.

---

## Colors

### Dark theme

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#18181b` | Page background |
| `--surface` | `#27272a` | Card/surface background |
| `--surface-hover` | `#2f2f33` | Surface hover state |
| `--border` | `#3f3f46` | Visible borders |
| `--border-subtle` | `rgba(255,255,255,0.06)` | Subtle borders |
| `--text` | `#f4f4f5` | Primary text |
| `--text-secondary` | `#a1a1aa` | Secondary text |
| `--text-muted` | `#71717a` | Muted/placeholder text |
| `--accent` | `#24d455` | Active, success, focus |
| `--accent-hover` | `#1fbf4a` | Accent hover |

### Light theme

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#fafafa` | Page background |
| `--surface` | `#ffffff` | Card/surface background |
| `--surface-hover` | `#f5f5f5` | Surface hover state |
| `--border` | `#e5e5e5` | Visible borders |
| `--border-subtle` | `rgba(0,0,0,0.06)` | Subtle borders |
| `--text` | `#171717` | Primary text |
| `--text-secondary` | `#737373` | Secondary text |
| `--text-muted` | `#a3a3a3` | Muted/placeholder text |
| `--accent` | `#24d455` | Active, success, focus |
| `--accent-hover` | `#1fbf4a` | Accent hover |

Green (`#24d455`) is the only accent color. Everything else is grayscale.

---

## Typography

| Token | Value | Usage |
|---|---|---|
| `--font` | `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif` | Body font |
| `--font-mono` | `'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', 'DejaVu Sans Mono', monospace` | Code font |
| `--text-xs` | `0.65rem` | Labels, version |
| `--text-sm` | `0.75rem` | UI labels, chips |
| `--text-base` | `0.95rem` | Body, inputs |
| `--text-lg` | `1.25rem` | Product title |
| `--text-xl` | `1.5rem` | Page heading |
| `--lh-tight` | `1.2` | Headings |
| `--lh-normal` | `1.5` | Body |
| `--lh-relaxed` | `1.6` | Reading |

Body text: 16px (1rem), line-height 1.6.

---

## Spacing (4px base)

| Token | rem | px |
|---|---|---|
| `--space-1` | `0.25rem` | 4px |
| `--space-2` | `0.5rem` | 8px |
| `--space-3` | `0.75rem` | 12px |
| `--space-4` | `1rem` | 16px |
| `--space-5` | `1.25rem` | 20px |
| `--space-6` | `1.5rem` | 24px |
| `--space-8` | `2rem` | 32px |
| `--space-10` | `2.5rem` | 40px |

---

## Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-input` | `18px` | Text inputs, search bar |
| `--radius-button` | `12px` | Buttons |
| `--radius-chip` | `999px` | Chips, tags, badges |
| `--radius-card` | `20px` | Cards, containers |

---

## Borders

Borders preferred over shadows.

| Token | Value | Usage |
|---|---|---|
| `--border-width` | `1px` | Standard border |
| `--border-style` | `solid` | Standard style |

---

## Shadows

Almost none. Especially in dark mode.

| Token | Value | Usage |
|---|---|---|
| `--shadow-none` | `none` | Default |
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Elevation (light only) |

---

## Icon Sizing

| Token | Value | Usage |
|---|---|---|
| `--icon-sm` | `14px` | Small actions |
| `--icon-md` | `16px` | Standard UI icons, tabs |
| `--icon-lg` | `18px` | Submit, primary actions |
| `--icon-stroke` | `1.7` | All icon stroke widths |

---

## Animation Timing

| Token | Value | Usage |
|---|---|---|
| `--transition-fast` | `0.15s ease` | Hover, color changes |
| `--transition-normal` | `0.2s ease` | Default |
| `--transition-slow` | `0.3s ease` | Panel reveal |

Never animate purely for decoration.

---

## Focus States

| Rule | Value |
|---|---|
| `outline` | `2px solid var(--accent)` |
| `outline-offset` | `2px` |
| Applies to | `*:focus-visible` |

---

## Dark/Light Parity

Every token must have a dark and light value.
Both themes must be visually complete.
No token should be undefined in either theme.
