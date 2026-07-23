# Design checklist

Before merging any UI-related pull request, verify each item below.

## Consistency

- [ ] No new visual language introduced.
- [ ] Uses the same typographic scale, spacing, and color tokens.
- [ ] Reuses an existing pattern rather than inventing a new one.
- [ ] Visual weight matches the surrounding page — nothing competes for attention.

## Responsive

- [ ] Works at 320, 375, 430, 768, 1024, and 1280 px widths.
- [ ] Works in landscape on phones (short viewports).
- [ ] No horizontal page scrolling at any width.

## Accessibility

- [ ] Keyboard navigable: every interactive element reachable and operable by Tab.
- [ ] Visible focus states on all interactive elements.
- [ ] Touch targets at least 44 x 44 px on mobile.
- [ ] Works without JavaScript where the feature is informational or navigational.

## Writing

- [ ] No defensiveness, pride, or apology in the copy.
- [ ] No absolute language unless it is fact.
- [ ] No duplicated wording across pages.
- [ ] Invites rather than instructs; suggests rather than declares.

## Motion

- [ ] No unnecessary animation.
- [ ] Honors `prefers-reduced-motion` if animation is added.

## Reading comfort

- [ ] No increase in visual weight.
- [ ] No regression in reading rhythm or calm.
- [ ] Code blocks scroll without pushing the layout.
- [ ] Inline code wraps instead of overflowing.

## Tools

- [ ] No production HTML references development-only scripts.
- [ ] No GPU acceleration hints.
