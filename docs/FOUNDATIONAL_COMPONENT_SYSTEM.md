# Foundational Component System (Phase 1)

## Overview
Phase 1 introduces foundational React components that map 1:1 to the existing CSS classes in `web/public/styles.css`. The goal is zero visual change while creating a composable system for future consolidation.

Key principles:
- Zero visual changes (pixel parity with existing UI)
- Composition over configuration
- Single source of truth for styling through foundational components
- Type-safe React + TypeScript APIs
- Existing CSS classes remain intact for Phase 1

## Component Inventory
All foundational components live under `web/components/foundational/` and are exported via `web/components/foundational/index.ts`.

### Text
- `Text.H1`, `Text.H2`, `Text.H3`, `Text.Body`, `Text.Small`, `Text.Emphasis`
- Default classes: `text-h1`, `text-h2`, `text-h3`, `text-body`, `text-small`, `text-emphasis`
- Props: `align`, `color`, `marginAll`, `margiall`, `withBase`

### Container
- `Container` (generic wrapper)
- Props: `as`, `variant`, `padding`, `borderRadius`, `background`, `backdropFilter`, `border`, `maxWidth`
- Use `variant` to attach existing class names (e.g., `section`, `pricing-card`, `project-box`).

### Layout
- `Layout.Flex`, `Layout.Grid`, `Layout.TwoCol`
- Props: `as`, `variant`, `gap`, `align`, `justify`, `direction`, `wrap`, `columns`

### Color
- `Color.Background`, `Color.Text`
- Props: `as`, `variant`, `background`, `color`

### Border
- `Border`
- Utilities: `resolveRadius`, `getConcentricRadius`
- Props: `as`, `radius`, `width`, `borderStyle`, `color`
- Border radius minimum: 25px (enforced for numeric/px values)
- Concentric logic: `inner`, `middle = inner + 8`, `outer = inner + 16`

### Spacing
- `Spacing`
- Utility: `space(value)` (8px grid)
- Props: `as`, `variant`, `margin`, `marginX`, `marginY`, `padding`, `paddingX`, `paddingY`

### Button
- `Button.Primary` -> `cta-button`
- `Button.Secondary` -> `cta-button2` (use `fixed` for `cta-button2-fixed`)
- `Button.Ghost` -> `cta-button2-fixed`
- `Button.Link` -> `terms-link`
- `Button.Base` accepts `variant` for other button classes

### Input
- `Input.Text`, `Input.TextArea`
- Use `variant` to map existing input classes (e.g., `auth-input`, `waitlist-input`, `feedback-input`).

### Modal
- `Modal.Overlay`, `Modal.Content`
- Use `variant` to map modal overlay/content classes (e.g., `terms-modal-overlay`).

### Section
- `Section` wraps `section` elements and applies the base `section` class by default.
- Props: `as`, `variant`, `withBase`.

## Composition Patterns
- Use `Section` + `Layout` + `Container` to rebuild existing layouts.
- Use `Text.*` components where unified typography is desired; set `withBase={false}` when a local stylesheet targets the tag directly.
- Use `Button.*` variants for CTAs and `Button.Base` for special-case buttons.

## Migration Guide
1. Replace raw layout elements (`div`, `section`) with `Container`/`Section`/`Layout` while preserving class names via `variant`.
2. Replace text elements with `Text.*` components. Use `withBase={false}` when local styles rely on tag selectors (e.g., modal-specific `h2`).
3. Replace buttons and inputs with `Button.*` and `Input.*` components.
4. Keep existing CSS classes in place for Phase 1.

## Best Practices
- Preserve existing class names via `variant` to maintain visual parity.
- Use `withBase={false}` for text inside local styles that target tags (e.g., `.terms-modal-content h1`).
- Avoid introducing new classes during Phase 1; defer consolidation to Phase 2.
