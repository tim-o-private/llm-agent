# Visual Design System

## Overview

This document outlines the visual design system developed for the application, focusing on modern UI patterns, glassmorphic effects, and innovative layout concepts that reduce cognitive load while maintaining functionality.

## Core Design Philosophy

### 1. Calm Productivity
- **Animation Philosophy**: Calm productivity over energetic engagement
- **Purpose**: Reduce cognitive load through clever AI and design
- **Goal**: Make "what do I need to do right now?" very clear
- **Accessibility**: Information should be a keystroke away, not a click away

### 2. Context Preservation
- **Split Screen Paradigm**: Primary (60%) and Secondary (40%) panes
- **Always Visible**: Both panes remain visible, no navigation away from work
- **Contextual AI**: AI can modify workspace layout and content contextually

## Layout System

### Primary/Secondary Pane Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Workspace Layout                         │
├─────────────────────────────┬───────────────────────────────┤
│        Primary Pane         │      Secondary Pane           │
│           (60%)             │           (40%)               │
│                             │                               │
│  ┌─────────────────────┐    │    ┌─────────────────────┐    │
│  │   Active Card       │    │    │   Active Card       │    │
│  │                     │    │    │                     │    │
│  └─────────────────────┘    │    └─────────────────────┘    │
│ ┌─────────────────────┐     │     ┌─────────────────────┐   │
│┌─────────────────────┐      │      ┌─────────────────────┐  │
││   Stacked Cards     │      │      │   Stacked Cards     ││ │
│└─────────────────────┘      │      └─────────────────────┘│ │
│ └─────────────────────┘     │     └─────────────────────┘   │
└─────────────────────────────┴───────────────────────────────┘
```

### Key Features
- **Keyboard Navigation**: Tab (switch focus), ⌘1-4 (quick switch), ←→ (cycle)
- **Visual Focus**: Clear borders and labels show active pane
- **Card Stacking**: Maximum 2 visible stacked cards behind active card
- **Edge Visibility**: Left pane stacks left, right pane stacks right

## Card Stacking System

### Visual Hierarchy
1. **Active Card**: Solid, opaque background - fully readable
2. **Stacked Cards**: Progressively darker backgrounds for depth
3. **Exit Animations**: Cards fly out to respective sides when switching

### Positioning Logic
```css
/* Primary Pane (Left Side) */
.active-card {
  left: 32px;  /* Space for stacked card edges */
  right: 0;
}

.stacked-cards {
  left: 0;     /* Can extend into padding area */
  right: 0;
  transform: translateX(-20px * stackDepth);  /* Fan left */
}

/* Secondary Pane (Right Side) */
.active-card {
  left: 0;
  right: 32px; /* Space for stacked card edges */
}

.stacked-cards {
  left: 0;
  right: 0;    /* Can extend into padding area */
  transform: translateX(20px * stackDepth);   /* Fan right */
}
```

### Transform Calculations
```javascript
// Stacking Effect
const horizontalOffset = isPrimary ? -stackDepth * 20 : stackDepth * 20;
const verticalOffset = stackDepth * 8;
const scale = 1 - stackDepth * 0.05;

// Exit Animation
const exitHorizontalOffset = isPrimary ? -200 : 200;
const exitVerticalOffset = -50;
const exitScale = 0.8;
```

## Animation System

### Animation Principles
1. **One Primary Animation Per View**: Avoid competing animations
2. **Reduce Motion When Inactive**: Scale with importance
3. **Accessibility**: Full `prefers-reduced-motion` support
4. **Smooth Transitions**: 500ms duration with ease-out timing

### Card Transition States

#### 1. Stacking Animation
- **Duration**: 500ms
- **Easing**: ease-out
- **Properties**: translateX, translateY, translateZ, scale
- **Z-Index**: Active (10), Stacked (10-depth), Exiting (15)

#### 2. Exit Animation
- **Horizontal Movement**: ±200px (left/right based on pane)
- **Vertical Lift**: -50px upward
- **Scale**: 0.8 (shrink)
- **Opacity**: 0 (fade out)
- **Cleanup**: Automatic after 500ms

#### 3. Restacking Animation
- **Current Card**: Slides down/scales smaller
- **New Card**: Slides up from stack
- **Other Cards**: Reposition smoothly
- **Effect**: "Pulling card from deck to front"

## Color System

### Background Hierarchy
```css
/* Active Cards */
.active-card {
  background: var(--ui-element-bg);           /* Solid, opaque */
  border: var(--ui-border-glow) / 50%;
}

/* Stacked Cards (Progressive Depth) */
.stacked-depth-1 {
  background: var(--ui-surface);              /* Darker for depth */
  border: var(--ui-border) / 40%;
}

.stacked-depth-2 {
  background: var(--ui-surface) / 80%;        /* Even darker */
  border: var(--ui-border) / 30%;
}

/* Focus States */
.focused-pane {
  ring: 2px var(--brand-primary) / 30%;
  shadow: var(--shadow-glow-lg);
}
```

### Theme Integration
- **Primary Branding**: `var(--brand-primary)` for active states
- **Semantic Colors**: Status-based colors for task states
- **Glass Effects**: `backdrop-blur-glass` for subtle transparency
- **Glow Effects**: `shadow-glow`, `shadow-glow-lg` for depth

## Glassmorphic Effects

### Implementation Strategy
```css
.glassmorphic-element {
  background: var(--ui-element-bg) / 90%;     /* Subtle transparency */
  backdrop-filter: blur(12px);                /* Blur background */
  border: 1px solid var(--ui-border-glow) / 50%;
  box-shadow: var(--shadow-glow);
}
```

### Usage Guidelines
- **Active Elements**: Minimal transparency (90% opacity)
- **Overlay Elements**: More transparency (70% opacity)
- **Stacked Elements**: Progressive transparency (60%, 50%, 40%)
- **Background Blur**: Only on elements that overlay content

## Responsive Behavior

### Container Overflow
```css
.pane-container {
  overflow: visible;                          /* Allow card edges to show */
  transform-style: preserve-3d;               /* Enable 3D transforms */
  perspective: 1000px;                        /* 3D perspective */
}
```

### Padding Strategy
- **Left Pane**: 48px left padding for visible stacked edges
- **Right Pane**: 48px right padding for visible stacked edges
- **Active Cards**: Inset by 32px to show stacked card edges

## Keyboard Interaction

### Shortcuts
| Key Combination | Action |
|----------------|--------|
| `Tab` | Switch focus between primary/secondary panes |
| `⌘1` - `⌘4` | Quick switch to specific pane type |
| `←` / `→` | Cycle through panes in focused area |
| `Space` | Activate/interact with focused element |

### Focus Management
- **Visual Indicators**: Ring and glow effects
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader**: Proper ARIA labels and roles

## Implementation Notes

### React Key Management
```javascript
// Unique keys prevent React conflicts
const uniqueKey = `${paneType}-${pane}-${isExiting ? 'exiting' : 'normal'}`;

// Proper cleanup of exit animations
setTimeout(() => setExitingPane(null), 500);
```

### Performance Considerations
- **Transform-based Animations**: Use transforms for smooth 60fps animations
- **Layer Promotion**: Cards automatically promoted to GPU layers
- **Cleanup**: Automatic cleanup of exit states prevents memory leaks

## Future Enhancements

### Planned Features
1. **Drag & Drop Reordering**: Allow manual card stack reordering
2. **Custom Layouts**: User-defined pane arrangements
3. **Gesture Support**: Touch/trackpad gestures for navigation
4. **Theme Variants**: Multiple glassmorphic intensity levels

### Accessibility Roadmap
1. **High Contrast Mode**: Alternative color schemes
2. **Reduced Motion**: Simplified animations for accessibility
3. **Voice Navigation**: Voice commands for pane switching
4. **Screen Reader**: Enhanced screen reader support

## Design Tokens

### Spacing
- **Card Inset**: 32px (space for stacked edges)
- **Container Padding**: 48px (visible stack area)
- **Stack Offset**: 20px per depth level
- **Vertical Stack**: 8px per depth level

### Timing
- **Transition Duration**: 500ms
- **Exit Animation**: 500ms
- **Cleanup Delay**: 500ms
- **Easing**: ease-out

### Z-Index Hierarchy
- **Active Cards**: 10
- **Stacked Cards**: 10 - stackDepth
- **Exiting Cards**: 15 (above all others)
- **UI Controls**: 20+

---

*This design system provides a foundation for creating intuitive, accessible, and visually appealing interfaces that reduce cognitive load while maintaining full functionality.* 