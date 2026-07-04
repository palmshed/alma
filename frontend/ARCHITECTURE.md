# Alma Frontend Architecture

## Module layers

```
src/
├── layouts/        Arrange components into views.
├── components/     Render UI. No business logic.
├── hooks/          Manage UI behavior. One responsibility per hook.
├── services/       Talk to external APIs. Never depend on React.
├── types/          Shared interfaces.
└── utils/          Pure helper functions.
```

## Dependency direction

```
UI Components
      ↓
    Hooks
      ↓
  Services
      ↓
    API
```

- A hook may depend on another hook or a service.
- A service must never depend on React.
- Components communicate only with hooks.
- Hooks communicate with services.

## Component hierarchy

```
App
├── Header
├── LandingLayout
│   ├── hero (palm logo + title)
│   ├── composer
│   ├── suggestions (optional chips)
│   └── modes (segmented control)
└── ConversationLayout
    ├── messages (scrollable response area)
    ├── composer
    └── sidebar (reserved for future use)
```

## Current implementation

```
App
├── useComposer()        → draft text, clear
├── useConversation()    → messages, loading, submit(), clear()
│   └── api              → HTTP calls (services/api.ts)
├── useStreaming()       → (future: partial tokens, cancellation)
│
├── Header
├── LandingLayout        → hero, composer, suggestions, modes
└── ConversationLayout   → messages, composer
```

## Hook ownership

| Hook | Owns |
|---|---|
| `useComposer` | Draft text, clear |
| `useConversation` | Messages (response, thinking, image), loading state, conversation lifecycle, submit orchestration |
| `useStreaming` | (future) Partial responses, cancellation, completion |

## Service ownership

| Service | Owns |
|---|---|
| `api` | HTTP requests, error handling, base URL resolution |

## Key principles

- **React is the design source of truth.** The static Flask interface
  (`deploy/static/web/`) mirrors the React output exactly — no drift.

- **Layouts own composition only.** They receive fully constructed
  components as props (ReactNode slots). They never contain business logic,
  API calls, or state beyond what their slot arrangement requires.

- **Components render UI.** They are presentation-focused, composable, and
  reusable across both landing and conversation layouts. They receive
  behavior through props/callbacks only.

- **Hooks own one responsibility each.** No monolithic hook that manages
  everything. Each hook extracts a single concern (conversation state,
  composer state, streaming).

- **The Composer has a single implementation.** It is defined once in `App`
  and passed to whichever layout is active. It never knows whether it
  renders on the landing page or in the conversation view.

## Transition model

The landing → conversation transition is a **layout swap** driven by
`conversationStarted` in `useConversation`. The same Composer component
instance (JSX reference) is used in both layouts, changing only its visual
context.

## Directory

- `frontend/src/` — React application (source of truth)
  - `layouts/LandingLayout.tsx`
  - `layouts/ConversationLayout.tsx`
  - `components/` — 12 components (Composer, Header, Chip, SegmentedControl, LoadingDots, etc.)
  - `hooks/useComposer.ts`, `hooks/useConversation.ts`
  - `services/api.ts`
  - `types/index.ts`
  - `utils/index.tsx`
  - `App.tsx` — orchestrator (wires hooks to components)
  - `index.css` — all styles via Palmshed design tokens
- `deploy/static/web/` — Flask static mirror (static HTML/CSS/JS)
  - `index.html` — standalone static page
  - `templates/index.html` — Jinja2 template (mirrors index.html)
  - `static/css/main.css` — static CSS (mirrors frontend/src/index.css)
  - `static/js/main.js` — static JS behavior

## Verified differences between React and static

| Area | React | Static | Rationale |
|---|---|---|---|
| **Composer** | Single JSX instance, rendered in whichever layout is active | Two separate `<textarea>` elements (`#landing-input`, `#conversation-input`), values synced via JS | Static HTML cannot dynamically move a DOM node between layouts. Both textareas share identical structure, class, and styling. |
| **Loading (response area)** | Wrapped in `.conversation-loading` (flex, centered, 2rem padding) | Wrapped in `.response-container` (standard card padding) | Static injects loading HTML directly into `conversation-scroll`. Slight padding difference, visually equivalent. |
| **Theme toggle** | Conditional render: Sun icon in dark mode, Moon icon in light (Lucide) | Both SVGs always in DOM, visibility toggled via `.sun-icon` / `.moon-icon` CSS classes | CSS-driven approach avoids runtime conditional logic. Same visual result. |
| **Attach button** | Conditionally rendered (only when `onAttach` prop provided) | Always in DOM, no click handler wired | Static pre-renders all elements; handler can be added later. No visual impact. |
| **Clear button** | Conditionally rendered (only when `hasText && onClear`) | Always in DOM, `display:none` by default, toggled via JS | Static pre-renders for JS to manage. Same visual behavior. |
| **Cookie notification** | Not implemented | Present in HTML | Flask-specific feature. Not part of React UI. |
| **API endpoint URLs** | `http://localhost:8000/api/…` | `/api/…` (relative) | Development convenience vs deployment. React uses absolute URL during dev; static uses relative for same-origin Flask. |

## File sizes (after Phase 3 refactor)

| File | Lines | Role |
|---|---|---|
| `App.tsx` | 99 | Orchestrator (was 170, reduced by 42%) |
| `services/api.ts` | 48 | HTTP abstraction (extracted from App) |
| `hooks/useConversation.ts` | 72 | Conversation lifecycle + submit orchestration |
| `hooks/useComposer.ts` | 18 | Draft text state |
| `utils/index.tsx` | 20 | MODES, SUGGESTIONS, endpoint helpers |
| `types/index.ts` | 14 | Shared interfaces |
| Largest component: `Composer.tsx` | 119 | Input, send button, attach, loading states |
| Largest CSS: `index.css` | 616 | All React styles |
| Largest static JS: `main.js` | 367 | DOM behavior + API calls |
| Largest static CSS: `main.css` | 764 | All static styles |
