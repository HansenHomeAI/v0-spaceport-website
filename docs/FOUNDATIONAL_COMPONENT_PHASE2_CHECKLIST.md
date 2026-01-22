# Foundational Component Phase 2 Checklist

Purpose: migrate all styling from `web/public/styles.css` into the foundational component system and remove `styles.css` without visual regressions.

## Current status
- `styles.css` copied to `web/components/foundational/legacy.module.css` for 1:1 parity.
- Foundational components now resolve `variant` and `className` tokens via `legacy.module.css` mapping.
- `web/public/styles.css` removed and its import deleted from `web/app/layout.tsx`.

## Selector inventory
- Full selector list: `logs/styles-selectors.txt`
- Class selectors: `logs/styles-selectors-class.txt`
- Global selectors: `logs/styles-selectors-global.txt`

## Mapping approach
- Each legacy class maps to a foundational `variant` token with the same name.
- `className` tokens are also mapped through the same legacy module to preserve any remaining ad hoc class usage while refactoring.

## Verification checklist
- [x] Component library parity check
- [x] Home / Landing parity check
- [x] Pricing parity check
- [x] Create flow parity check
- [x] Auth flow parity check
- [x] Flight viewer / Shape tools parity check
- [x] Modals (New Project, Model Delivery, Terms) open/close
- [x] Forms (waitlist, feedback, auth) input states
- [x] Mobile breakpoints (375px) snapshots
- [x] Desktop breakpoints (1280px) snapshots
