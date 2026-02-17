---
name: frontend-patterns
description: React, TypeScript, and UI patterns for webApp/src/. Use when writing or modifying TSX/TS files. Covers Radix Themes (provider only, NOT components), semantic color tokens, React Query hooks, auth from Supabase client, Zustand overlays, react-hook-form + Zod, accessibility (WCAG 2.1 AA), and ADHD-friendly design.
---

# Frontend Patterns

## Architecture

```
webApp/src/
  api/hooks/           → React Query hooks (data fetching)
  components/ui/       → Reusable primitives (Card, Modal, Button)
  components/features/ → Domain components (tasks/, auth/)
  features/            → Feature modules (auth/useAuthStore)
  pages/               → Page-level components
  stores/              → Zustand stores
  styles/              → index.css, ui-components.css
```

## Quick Checklist

Before writing frontend code, verify:
- [ ] No `@radix-ui/themes` component imports (only `<Theme>` provider)
- [ ] All colors use semantic tokens (`bg-brand-primary`, `text-text-secondary`)
- [ ] Data fetching via React Query hooks, not useState+useEffect
- [ ] Auth tokens from `supabase.auth.getSession()`, not Zustand
- [ ] Modals via `useOverlayStore`, not local state
- [ ] Loading + error states handled in every data component
- [ ] Forms use react-hook-form + Zod
- [ ] Keyboard support + ARIA labels on interactive elements
- [ ] CSS transitions preferred over framer-motion
- [ ] Path aliases used (`@/`, `@components/` — no relative `../../../`)

## Critical Rule: Radix Themes = Provider Only

```tsx
// ✅ Theme provider in main.tsx
import { Theme } from '@radix-ui/themes';

// ✅ Radix Primitives + Tailwind for components
import * as Dialog from '@radix-ui/react-dialog';

// ❌ NEVER import pre-styled Radix Themes components
import { Button } from '@radix-ui/themes';  // FORBIDDEN
```

## Design Philosophy

This app targets users with ADHD. Prioritize: calm & minimal, clear hierarchy, low friction, encouraging tone, predictable behavior.

## Detailed Reference

For full patterns with code examples (color tokens, React Query, auth, forms, accessibility, keyboard shortcuts, animations), see [reference.md](reference.md).
