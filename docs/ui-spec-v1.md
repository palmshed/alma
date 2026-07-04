# Alma UI Specification v1

Do not redesign the layout again. Instead, implement this specification and refine
it incrementally.

## Overall feeling

Alma should feel like a calm workspace.

Not ChatGPT.

Not Claude.

Not Linear.

Not Notion.

It should feel like a Palmshed application.

Quiet.
Balanced.
Purposeful.

---

# 1. Navigation

Keep it extremely small.

```
┌────────────────────────────────────────────────────────────┐
 Palm                                     Theme  Settings
──────────────────────────────────────────────────────────────
```

No shadows.

One divider.

Nothing else.

The current header is close.

---

# 2. Landing

Everything should be visually centered.

```
        Palm

       Alma

   Ask anything...

 suggestion chips

 modes
```

This is the only page that is centered.

---

# 3. Conversation

After first prompt the landing page disappears.

Instead

```
Header

Conversation

Conversation

Conversation

──────────────────────────

Composer fixed to bottom
```

Never keep the composer floating in the middle.

---

# 4. Composer

This is the primary component.

It deserves the most polish.

```
┌───────────────────────────────┐
 Search icon

 Ask anything...

               Attach

               Send
────────────────────────────────
Canvas  Thinking  Web  Images
└───────────────────────────────┘
```

The send button should only appear active when text exists.

---

# 5. Search icon

The search icon currently serves no purpose.

Either remove it or make it open search history.

Never decorative.

---

# 6. Chips

Current chips look acceptable.

Reduce to three.

Rotate them.

Examples

```
Summarize article
Explain code
Generate release notes
```

---

# 7. Modes

Current modes should become segmented controls.

Instead of

```
□ Canvas
□ Thinking
□ Web
```

Use

```
[ Canvas ] Thinking Web Images
```

Selected mode gets

- subtle filled background
- brighter icon
- slightly bolder label

No bright orange.

---

# 8. Colors

The orange is too dominant.

Palmshed already has green.

Use green sparingly.

Everything else should be grayscale.

Only one accent color.

---

# 9. Corners

Current radius is inconsistent.

Define one system.

Example

```
Inputs      18 px
Buttons     12 px
Chips       999 px
Cards       20 px
```

Never eyeball it.

---

# 10. Shadows

Almost none.

Dark mode especially.

Prefer border over shadow.

---

# 11. Icons

Every icon comes from Glimpse.

No exceptions.

Builder should never download another icon pack.

---

# 12. Motion

Landing

↓

Card fades in

↓

Cursor appears

↓

User types

↓

Conversation slides upward

↓

Composer docks bottom

↓

Response streams

Those transitions define the product.

---

# 13. Empty states

Instead of `Start with a question...` use

```
Ask a question, explore an idea, or drop a file.
```

Better guidance.

---

# 14. Loading

Never `Thinking...`

Instead

```
● ○ ○
Generating...
```

or animated dots beside the assistant avatar.

---

# 15. Typography

This needs the most work.

Current heading `Alma` feels disconnected.

Use

```
Palm icon
Alma
16–18 px
Semibold
```

Don't make the title oversized.

The product is the workspace. Not the logo.

---

# 16. Future layout

The interface should naturally support

- conversation history
- projects
- attachments
- generated images
- artifacts
- code blocks

without redesigning the homepage.

That means the landing page is temporary.

The conversation page is the real application.

---

## Guiding principle

> Design Alma as a workspace, not as a marketing landing page. The welcome screen
> exists only to start a conversation. Once the user sends a message, the interface
> should transform into a focused working environment where the conversation becomes
> the primary content. Every component should support that transition rather than
> keeping the user on the welcome screen.
