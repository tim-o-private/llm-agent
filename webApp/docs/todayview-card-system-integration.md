# TodayView Card System Integration Guide

## Overview

This document explains how the `TodayViewMockup.tsx` transforms the existing TodayView into a card-based stacking system that implements the visual design patterns from the design system while incorporating feedback from the design iteration document.

## Key Transformations

### 1. Layout Architecture Change

**Before (Original TodayView):**
```
┌─────────────────────────────────────────────────────────────┐
│                    Single Column Layout                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                Header                               │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Fast Task Input                        │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Task List Group                        │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [Chat Panel slides in from right as overlay]              │
└─────────────────────────────────────────────────────────────┘
```

**After (Card System):**
```
┌─────────────────────────────────────────────────────────────┐
│                    Split Pane Layout                        │
├─────────────────────────────┬───────────────────────────────┤
│        Primary Pane         │      Secondary Pane           │
│           (60%)             │           (40%)               │
│                             │                               │
│  ┌─────────────────────┐    │    ┌─────────────────────┐    │
│  │   Tasks Card        │    │    │   Chat Card         │    │
│  │                     │    │    │                     │    │
│  └─────────────────────┘    │    └─────────────────────┘    │
│ ┌─────────────────────┐     │     ┌─────────────────────┐   │
│┌─────────────────────┐      │      ┌─────────────────────┐  │
││   Calendar Card     │      │      │   Focus Card        ││ │
│└─────────────────────┘      │      └─────────────────────┘│ │
│ └─────────────────────┘     │     └─────────────────────┘   │
└─────────────────────────────┴───────────────────────────────┘
```

### 2. Context Modes Implementation

The mockup implements the context modes from the feedback document:

#### A. Split-Pane Mode (Default)
- **Primary pane (60%)**: Main workspace for tasks
- **Secondary pane (40%)**: Context like chat, calendar, focus
- **Both panes visible**: Maintains context while working
- **Keyboard navigation**: Tab switches focus, ⌘1-4 quick switch

#### B. Progressive Disclosure
- **Stack depth limit**: Maximum 2 stacked cards visible
- **Edge visibility**: Stacked cards show edges for discoverability
- **Click to reveal**: Clicking stacked edges brings cards forward
- **Smooth animations**: 500ms transitions with ease-out timing

#### C. Focus Indicators
- **Visual focus ring**: Active pane shows brand-primary ring
- **Pane labels**: Header shows current primary/secondary panes
- **Keyboard shortcuts**: Visual indicators for ⌘1-4 shortcuts

## Implementation Details

### 3. Card Stacking System

#### A. StackedCard Component
```typescript
interface StackedCardProps {
  pane: PaneType;
  isActive: boolean;
  isExiting: boolean;
  isPrimary: boolean;
  stackDepth: number;
  onSwitch: () => void;
  children: React.ReactNode;
}
```

**Key Features:**
- **Transform calculations**: Horizontal/vertical offsets based on stack depth
- **Exit animations**: Cards fly out to respective sides (left/right)
- **Glassmorphic styling**: Progressive transparency for depth
- **Pointer events**: Only active cards receive interactions

#### B. Transform Logic
```typescript
const transform = useMemo(() => {
  let horizontalOffset = 0;
  let verticalOffset = 0;
  
  if (isExiting) {
    horizontalOffset = isPrimary ? -200 : 200; // Fly left/right
    verticalOffset = -50; // Lift up
  } else if (stackDepth > 0) {
    horizontalOffset = isPrimary ? -stackDepth * 20 : stackDepth * 20;
    verticalOffset = stackDepth * 8;
  }
  
  const scale = isExiting ? 0.8 : 1 - stackDepth * 0.05;
  
  return `translateX(${horizontalOffset}px) translateY(${verticalOffset}px) translateZ(-${stackDepth * 10}px) scale(${scale})`;
}, [isExiting, isPrimary, stackDepth]);
```

### 4. Keyboard Navigation

#### A. Implemented Shortcuts
| Shortcut | Action | Implementation |
|----------|--------|----------------|
| `Tab` | Switch focus between panes | `setFocusedPane('primary' \| 'secondary')` |
| `⌘1-4` | Quick switch to pane type | Maps to `['tasks', 'chat', 'calendar', 'focus']` |
| `←→` | Cycle through panes | Increments/decrements pane index |

#### B. useKeyboardNavigation Hook
```typescript
const useKeyboardNavigation = (
  panes: PaneType[],
  primaryPane: PaneType,
  secondaryPane: PaneType,
  focusedPane: 'primary' | 'secondary',
  onPrimarySwitch: (pane: PaneType) => void,
  onSecondarySwitch: (pane: PaneType) => void,
  onFocusSwitch: (focus: 'primary' | 'secondary') => void
) => {
  // Event listener implementation
};
```

### 5. Pane Content Integration

#### A. Tasks Pane
- **Preserves existing functionality**: FastTaskInput, TaskListGroup, DnD
- **Card wrapper**: Adds header with icon and title
- **Scrollable content**: Task list scrolls within card bounds
- **Empty state**: Maintains original empty state design

#### B. Chat Pane
- **ChatPanelV2 integration**: Uses existing assistant-ui implementation
- **Header consistency**: Matches other pane headers
- **Full height**: Chat takes full card height minus header

#### C. Future Panes
- **Calendar**: Placeholder with consistent styling
- **Focus**: Placeholder for focus session controls
- **Extensible**: Easy to add new pane types

### 6. Visual Design System Integration

#### A. Glassmorphic Effects
```css
.glassmorphic-card {
  background: var(--ui-element-bg);
  backdrop-filter: blur(12px);
  border: 1px solid var(--ui-border-glow/50);
  box-shadow: var(--shadow-elevated);
}
```

#### B. Background Hierarchy
- **Active cards**: `bg-ui-element-bg` - solid, opaque
- **Stacked depth 1**: `bg-ui-surface` - darker for depth
- **Stacked depth 2**: `bg-ui-surface/80` - even darker
- **Progressive borders**: Border opacity decreases with depth

#### C. Animation Classes
```css
.transition-all duration-500 ease-out
```
- **Consistent timing**: 500ms for all transitions
- **Smooth easing**: ease-out for natural feel
- **Hardware acceleration**: transform3d for 60fps

## Addressing Design Feedback

### 7. Context Modes from Feedback Document

#### A. Split-Pane ✅
- **Implementation**: Default mode with 60/40 split
- **Both panes visible**: Always maintains context
- **Interactive**: Both panes can receive focus and input

#### B. Focus Mode (Future Enhancement)
- **Planned**: Full-bleed single card mode
- **Trigger**: Keyboard shortcut or button
- **Return**: Escape key returns to split-pane

#### C. Modal Overlay ✅
- **Preserved**: TaskDetailView and PrioritizeViewModal
- **Overlay behavior**: Dims background, takes full attention
- **Return mechanism**: Close button or escape key

### 8. Mobile Adaptation (Future)

#### A. Responsive Breakpoints
```typescript
// Future implementation
const isMobile = useMediaQuery('(max-width: 768px)');

if (isMobile) {
  return <MobileSingleCardView />;
}
```

#### B. Mobile Patterns
- **Single card**: Only one card visible at a time
- **Swipe navigation**: Horizontal swipes to switch cards
- **Bottom navigation**: Tab bar for quick switching
- **Stack indicators**: Badges showing card count

### 9. Stack Depth & Visual Indicators

#### A. Current Implementation
- **2-card limit**: Maximum 2 stacked cards visible
- **Edge peek**: Stacked cards show 20px offset edges
- **Progressive styling**: Darker backgrounds for depth
- **Hover effects**: Stacked cards highlight on hover

#### B. Alternative Patterns (Future)
- **Badge indicators**: Numeric badges for stack count
- **Animated peek**: Hover reveals more of stacked cards
- **Gesture reveals**: Touch/trackpad gestures for stack navigation

## Migration Strategy

### 10. Gradual Adoption

#### A. Phase 1: Mockup Validation
- **Current**: `TodayViewMockup.tsx` for testing
- **Feedback**: Gather user feedback on card system
- **Iteration**: Refine based on usability testing

#### B. Phase 2: Feature Parity
- **Drag & Drop**: Implement task reordering in card system
- **All handlers**: Ensure all existing functionality works
- **Performance**: Optimize animations and rendering

#### C. Phase 3: Enhanced Features
- **Focus mode**: Full-bleed single card mode
- **Mobile responsive**: Adaptive layout for small screens
- **Custom layouts**: User-defined pane arrangements

### 11. Preserving Existing Functionality

#### A. State Management ✅
- **useTaskStore**: All existing store interactions preserved
- **useTaskViewStore**: Focus and selection state maintained
- **API hooks**: All mutation hooks work unchanged

#### B. Component Integration ✅
- **TaskListGroup**: Renders within tasks pane
- **FastTaskInput**: Preserved with same functionality
- **Modals**: TaskDetailView and PrioritizeViewModal unchanged

#### C. Keyboard Shortcuts ✅
- **Enhanced**: Adds pane navigation shortcuts
- **Preserved**: Existing task navigation still works
- **Conflict prevention**: Input focus state prevents conflicts

## Testing Strategy

### 12. Validation Points

#### A. Functionality Testing
- [ ] All existing task operations work
- [ ] Keyboard navigation functions correctly
- [ ] Animations perform smoothly
- [ ] Modal overlays work properly

#### B. Usability Testing
- [ ] Users can discover stacked cards
- [ ] Pane switching feels intuitive
- [ ] Context preservation improves workflow
- [ ] Keyboard shortcuts are learnable

#### C. Performance Testing
- [ ] 60fps animations on target devices
- [ ] Memory usage remains acceptable
- [ ] Large task lists render efficiently
- [ ] Smooth transitions under load

## Next Steps

### 13. Implementation Roadmap

1. **Validate Mockup**: Test with real data and user feedback
2. **Refine Animations**: Optimize performance and feel
3. **Add Focus Mode**: Implement full-bleed single card mode
4. **Mobile Adaptation**: Create responsive mobile version
5. **User Customization**: Allow pane arrangement preferences
6. **Advanced Features**: Drag & drop between panes, gesture support

### 14. Success Metrics

- **Reduced cognitive load**: Users report easier context switching
- **Improved productivity**: Faster task completion with context
- **High adoption**: Users prefer card system over original layout
- **Accessibility**: Full keyboard navigation and screen reader support

---

*This integration guide provides a comprehensive roadmap for transforming TodayView into a modern, card-based interface that reduces cognitive load while maintaining full functionality.* 