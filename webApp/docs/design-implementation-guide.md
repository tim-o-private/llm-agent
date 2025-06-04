# Design Implementation Guide

## Quick Start

This guide shows how to implement the visual design system patterns in your React components.

## Card Stacking Component Pattern

### Basic Structure

```tsx
interface StackedPaneProps {
  panes: PaneType[];
  activePane: PaneType;
  exitingPane: PaneType | null;
  isPrimary: boolean;
  onPaneSwitch: (pane: PaneType) => void;
}

const StackedPane: React.FC<StackedPaneProps> = ({
  panes,
  activePane,
  exitingPane,
  isPrimary,
  onPaneSwitch
}) => {
  const panesToRender = useMemo(() => {
    const result = [];
    
    // Add regular panes (active + stacked)
    panes.forEach((pane) => {
      const isActive = pane === activePane;
      
      if (isActive) {
        result.push({ pane, isActive: true, isExiting: false, stackDepth: 0 });
      } else {
        const stackDepth = calculateStackDepth(pane, activePane, panes);
        if (stackDepth <= 2) { // Limit to 2 stacked cards
          result.push({ pane, isActive: false, isExiting: false, stackDepth });
        }
      }
    });
    
    // Add exiting pane if different from current
    if (exitingPane && exitingPane !== activePane) {
      result.push({ pane: exitingPane, isActive: false, isExiting: true, stackDepth: 0 });
    }
    
    return result;
  }, [panes, activePane, exitingPane]);

  return (
    <div className="relative overflow-visible" style={{ transformStyle: 'preserve-3d' }}>
      {panesToRender.map(({ pane, isActive, isExiting, stackDepth }) => (
        <StackedCard
          key={`${isPrimary ? 'primary' : 'secondary'}-${pane}-${isExiting ? 'exiting' : 'normal'}`}
          pane={pane}
          isActive={isActive}
          isExiting={isExiting}
          isPrimary={isPrimary}
          stackDepth={stackDepth}
          onSwitch={() => onPaneSwitch(pane)}
        />
      ))}
    </div>
  );
};
```

### Card Component

```tsx
interface StackedCardProps {
  pane: PaneType;
  isActive: boolean;
  isExiting: boolean;
  isPrimary: boolean;
  stackDepth: number;
  onSwitch: () => void;
}

const StackedCard: React.FC<StackedCardProps> = ({
  pane,
  isActive,
  isExiting,
  isPrimary,
  stackDepth,
  onSwitch
}) => {
  const transform = useMemo(() => {
    let horizontalOffset = 0;
    let verticalOffset = 0;
    
    if (isExiting) {
      horizontalOffset = isPrimary ? -200 : 200;
      verticalOffset = -50;
    } else if (stackDepth > 0) {
      horizontalOffset = isPrimary ? -stackDepth * 20 : stackDepth * 20;
      verticalOffset = stackDepth * 8;
    }
    
    const scale = isExiting ? 0.8 : 1 - stackDepth * 0.05;
    
    return `translateX(${horizontalOffset}px) translateY(${verticalOffset}px) translateZ(-${stackDepth * 10}px) scale(${scale})`;
  }, [isExiting, isPrimary, stackDepth]);

  return (
    <div
      className={clsx(
        'absolute transition-all duration-500 ease-out',
        // Positioning
        isActive && isPrimary && 'left-8 right-0 top-0 bottom-0',
        isActive && !isPrimary && 'left-0 right-8 top-0 bottom-0',
        (!isActive || isExiting) && 'left-0 right-0 top-0 bottom-0',
        // Opacity for exit animation
        isExiting && 'opacity-0'
      )}
      style={{
        transform,
        zIndex: isActive ? 10 : isExiting ? 15 : 10 - stackDepth,
        pointerEvents: isActive ? 'auto' : 'none'
      }}
      onClick={!isActive ? onSwitch : undefined}
    >
      <div className={clsx(
        'rounded-xl border h-full relative shadow-elevated',
        'transition-all duration-500 ease-out',
        // Background hierarchy
        'bg-ui-element-bg border-ui-border-glow/50',
        stackDepth > 0 && 'bg-ui-surface border-ui-border/40',
        stackDepth > 1 && 'bg-ui-surface/80 border-ui-border/30'
      )}>
        {/* Card content */}
        <PaneContent pane={pane} />
      </div>
    </div>
  );
};
```

## Animation Hooks

### Exit Animation Hook

```tsx
const useExitAnimation = (duration: number = 500) => {
  const [exitingItem, setExitingItem] = useState<string | null>(null);
  
  const triggerExit = useCallback((item: string, newItem: string) => {
    if (item === newItem) return;
    
    setExitingItem(item);
    setTimeout(() => setExitingItem(null), duration);
  }, [duration]);
  
  return { exitingItem, triggerExit };
};

// Usage
const { exitingItem: exitingPane, triggerExit } = useExitAnimation();

const switchPane = useCallback((newPane: PaneType) => {
  triggerExit(currentPane, newPane);
  setCurrentPane(newPane);
}, [currentPane, triggerExit]);
```

### Keyboard Navigation Hook

```tsx
const useKeyboardNavigation = (
  panes: PaneType[],
  primaryPane: PaneType,
  secondaryPane: PaneType,
  focusedPane: 'primary' | 'secondary',
  onPrimarySwitch: (pane: PaneType) => void,
  onSecondarySwitch: (pane: PaneType) => void,
  onFocusSwitch: (focus: 'primary' | 'secondary') => void
) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Quick switch with Cmd/Ctrl + 1-4
      if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '4') {
        e.preventDefault();
        const paneIndex = parseInt(e.key) - 1;
        const targetPane = panes[paneIndex];
        if (targetPane) {
          if (focusedPane === 'primary') {
            onPrimarySwitch(targetPane);
          } else {
            onSecondarySwitch(targetPane);
          }
        }
      }
      
      // Tab to switch focus
      if (e.key === 'Tab' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        onFocusSwitch(focusedPane === 'primary' ? 'secondary' : 'primary');
      }
      
      // Arrow keys to cycle
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const currentPane = focusedPane === 'primary' ? primaryPane : secondaryPane;
        const currentIndex = panes.indexOf(currentPane);
        
        let nextIndex;
        if (e.key === 'ArrowRight') {
          nextIndex = currentIndex < panes.length - 1 ? currentIndex + 1 : 0;
        } else {
          nextIndex = currentIndex > 0 ? currentIndex - 1 : panes.length - 1;
        }
        
        const nextPane = panes[nextIndex];
        if (focusedPane === 'primary') {
          onPrimarySwitch(nextPane);
        } else {
          onSecondarySwitch(nextPane);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [panes, primaryPane, secondaryPane, focusedPane, onPrimarySwitch, onSecondarySwitch, onFocusSwitch]);
};
```

## CSS Utilities

### Glassmorphic Classes

```css
/* Add to your global CSS or Tailwind config */
.backdrop-blur-glass {
  backdrop-filter: blur(12px);
}

.shadow-glow {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 
              0 2px 4px -1px rgba(0, 0, 0, 0.06),
              0 0 0 1px rgba(var(--brand-primary-rgb), 0.1);
}

.shadow-glow-lg {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 
              0 4px 6px -2px rgba(0, 0, 0, 0.05),
              0 0 0 1px rgba(var(--brand-primary-rgb), 0.2),
              0 0 20px rgba(var(--brand-primary-rgb), 0.1);
}

.shadow-elevated {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 
              0 10px 10px -5px rgba(0, 0, 0, 0.04);
}
```

### Animation Classes

```css
.animate-card-enter {
  animation: cardEnter 500ms ease-out forwards;
}

.animate-card-exit {
  animation: cardExit 500ms ease-out forwards;
}

@keyframes cardEnter {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes cardExit {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(-50px) scale(0.8);
  }
}

/* Respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .animate-card-enter,
  .animate-card-exit {
    animation: none;
  }
  
  .transition-all {
    transition: none;
  }
}
```

## Accessibility Implementation

### ARIA Labels and Roles

```tsx
const AccessibleStackedPane: React.FC<StackedPaneProps> = (props) => {
  return (
    <div
      role="tabpanel"
      aria-label={`${props.isPrimary ? 'Primary' : 'Secondary'} workspace pane`}
      aria-describedby="pane-instructions"
    >
      <div id="pane-instructions" className="sr-only">
        Use Tab to switch between panes, Command+1-4 for quick switching, 
        and arrow keys to cycle through pane types.
      </div>
      
      {/* Pane content */}
      <StackedPane {...props} />
    </div>
  );
};
```

### Focus Management

```tsx
const useFocusManagement = (isActive: boolean, paneRef: RefObject<HTMLDivElement>) => {
  useEffect(() => {
    if (isActive && paneRef.current) {
      // Focus the active pane when it becomes active
      paneRef.current.focus();
    }
  }, [isActive, paneRef]);
  
  return {
    tabIndex: isActive ? 0 : -1,
    'aria-hidden': !isActive,
    ref: paneRef
  };
};
```

## Performance Optimizations

### Memoization Strategy

```tsx
const MemoizedStackedCard = React.memo(StackedCard, (prevProps, nextProps) => {
  return (
    prevProps.isActive === nextProps.isActive &&
    prevProps.isExiting === nextProps.isExiting &&
    prevProps.stackDepth === nextProps.stackDepth &&
    prevProps.pane === nextProps.pane
  );
});
```

### Transform Optimization

```tsx
const useOptimizedTransform = (isExiting: boolean, isPrimary: boolean, stackDepth: number) => {
  return useMemo(() => {
    // Use transform3d for hardware acceleration
    let x = 0, y = 0, z = -stackDepth * 10;
    let scale = 1 - stackDepth * 0.05;
    
    if (isExiting) {
      x = isPrimary ? -200 : 200;
      y = -50;
      scale = 0.8;
    } else if (stackDepth > 0) {
      x = isPrimary ? -stackDepth * 20 : stackDepth * 20;
      y = stackDepth * 8;
    }
    
    return `translate3d(${x}px, ${y}px, ${z}px) scale(${scale})`;
  }, [isExiting, isPrimary, stackDepth]);
};
```

## Testing Patterns

### Animation Testing

```tsx
// Test exit animations
it('should trigger exit animation when switching panes', async () => {
  const { getByTestId, rerender } = render(
    <StackedPane activePane="tasks" exitingPane={null} />
  );
  
  rerender(<StackedPane activePane="chat" exitingPane="tasks" />);
  
  const exitingCard = getByTestId('card-tasks-exiting');
  expect(exitingCard).toHaveClass('opacity-0');
  
  // Wait for animation to complete
  await waitFor(() => {
    expect(exitingCard).not.toBeInTheDocument();
  }, { timeout: 600 });
});
```

### Keyboard Navigation Testing

```tsx
it('should switch panes with keyboard shortcuts', () => {
  const onPrimarySwitch = jest.fn();
  render(<StackedPane onPrimarySwitch={onPrimarySwitch} focusedPane="primary" />);
  
  fireEvent.keyDown(window, { key: '2', metaKey: true });
  expect(onPrimarySwitch).toHaveBeenCalledWith('chat');
});
```

## Common Patterns

### Loading States

```tsx
const LoadingCard: React.FC = () => (
  <div className="rounded-xl border bg-ui-element-bg border-ui-border-glow/50 h-full p-4">
    <div className="animate-pulse space-y-4">
      <div className="h-4 bg-ui-surface rounded w-3/4"></div>
      <div className="h-4 bg-ui-surface rounded w-1/2"></div>
      <div className="h-32 bg-ui-surface rounded"></div>
    </div>
  </div>
);
```

### Error States

```tsx
const ErrorCard: React.FC<{ error: string; onRetry: () => void }> = ({ error, onRetry }) => (
  <div className="rounded-xl border bg-ui-element-bg border-red-500/50 h-full p-4 flex flex-col items-center justify-center">
    <div className="text-red-500 mb-4">{error}</div>
    <button 
      onClick={onRetry}
      className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
    >
      Retry
    </button>
  </div>
);
```

---

*This implementation guide provides practical patterns for applying the visual design system in your React components.* 