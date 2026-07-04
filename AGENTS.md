# Alma - Architecture Guide

This document describes the architectural principles for contributors. It intentionally avoids implementation history, completed migrations, and temporary project status.

---

## Architecture

The application is organized into clear ownership boundaries.

```
Application
│
├── UI
│   ├── Layouts
│   ├── Components
│   └── Hooks
│
├── Application Services
│
├── Platform Services
│   ├── Mail
│   ├── Auth (future)
│   ├── Storage (future)
│   └── Notifications (future)
│
└── Infrastructure
```

### Layouts

- Compose screens.
- Own page structure only.
- Accept slots (`ReactNode`) where appropriate.
- Never perform API calls.
- Never contain business logic.

### Components

- Own presentation and interaction.
- Receive data through props.
- Emit events through callbacks.
- Avoid coordinating unrelated features.

### Hooks

- Own one responsibility.
- Encapsulate UI behavior and state.
- Avoid monolithic hooks.
- Never communicate directly with external systems unless that is the hook's sole purpose.

### Services

- Operate at the product layer (application-specific).
- Coordinate calls to Platform Services.
- Never import React.
- Never depend on UI components.
- Provide stable interfaces for hooks.

### Platform Services

Platform services provide reusable infrastructure shared across Palmshed products.

A capability belongs in Platform Services when it is reusable across
products, owns external integrations or infrastructure, and can evolve
independently of any single application.

Examples:

- Mail
- Authentication (future)
- Storage (future)
- Notifications (future)

Platform services:

- are product-agnostic
- expose stable public APIs
- own external integrations
- never depend on application-specific modules
- are designed for future extraction without changing consumers

### Utils

- Pure helper functions only.
- No React.
- No side effects.
- No application state.

---

## Dependency Direction

Dependencies should always flow downward.

```
UI
↓
Application Services
↓
Platform Services
↓
Infrastructure
```

Never introduce upward dependencies.

---

## Application

Code lives under the Application umbrella. It composes UI, routes
requests to services, and owns product-specific behavior.

Application code may depend on Platform Services but must never import
from other application modules in a way that creates tight coupling
across unrelated features.

---

## Ownership Rules

Before creating something new, ask:

1. Can an existing component, hook, or service be extended?
2. Is it reusable UI?
3. Is it UI behavior?
4. Is it external communication?
5. Is it a pure helper?

Use the following mapping:

| Responsibility | Location |
|---------------|----------|
| Page composition | Layout |
| Presentation | Component |
| UI behavior | Hook |
| External communication | Service |
| Shared infrastructure | Platform Service |
| Pure logic | Utils |

Avoid introducing new layers without a clear long-term responsibility.

---

## Architecture Decision Records

Major architectural decisions are documented in `docs/architecture/`.

AGENTS.md explains **how** contributors work.

ADRs explain **why** important decisions were made.

Current records:

- `0001-platform-services.md` — introducing the Platform Services layer
- `0002-mail-service.md` — mail as a reusable platform capability

---

## Composition Philosophy

Prefer extending existing ownership boundaries over introducing new ones.

Do not extract code simply to reduce file size.

Extract only when a new module has:

- a single responsibility
- a clear owner
- long-term reuse
- reduced cognitive load

The goal is architectural clarity, not maximum decomposition.

---

## Design System

Use shared design tokens throughout the application.

Avoid introducing one-off colors, spacing, timing values, or typography.

### Buttons

Use the shared `.btn` foundation for common interaction behavior.

Prefer variants over independent implementations.

Examples:

- `.btn--primary`
- `.btn--secondary`
- `.btn--ghost`

Specialized controls (composer actions, chips, segmented controls, toolbar controls) may define their own geometry while reusing the shared interaction model and design tokens.

---

## React and Static Parity

The React interface and the static implementation represent the same application.

Unless a documented technical constraint exists:

- layout should match
- interactions should match
- spacing should match
- behavior should match
- visual hierarchy should match

Changes affecting one implementation should normally be reflected in the other.

---

## Conversation Architecture

There is exactly one implementation of the **New conversation** action.

Every entry point delegates to the same logic.

Examples:

- Header logo
- Sidebar
- Keyboard shortcuts
- Future menus

Confirmation, state clearing, and navigation should never be duplicated.

---

## Branding

Publisher:

**Palmshed**

Product:

**Alma**

The product is always the primary identity.

The publisher should appear only where ownership is being communicated (for example About, footer, legal information).

Never give the publisher and product equal visual weight.

---

## Naming

Use descriptive names rather than implementation-specific names.

Prefer:

- `BrandLogo`
- `ConversationLayout`
- `ApiService`

Avoid names that unnecessarily encode historical branding or temporary implementation details.

---

## Contributor Principles

- Keep modules cohesive.
- Prefer explicit ownership.
- Avoid duplicate implementations.
- Prefer composition over inheritance.
- Keep public APIs stable.
- Reuse existing abstractions before creating new ones.
- Document architectural decisions rather than implementation history.

---

## When Unsure

Choose the option that makes the repository easier to understand for a new contributor.

Code should read like an outline of the application rather than a collection of implementation details.
