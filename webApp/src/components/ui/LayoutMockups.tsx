import React, { useState } from 'react';
import clsx from 'clsx';
import { Button } from './Button';
import { TaskCard } from './TaskCard';
import { Task } from '@/api/types';

import {
  DragHandleDots2Icon,
  CaretLeftIcon,
  CaretRightIcon,
  GridIcon,
  StackIcon,
  LayersIcon,
  MixIcon,
  ChatBubbleIcon,
  CalendarIcon,
  ListBulletIcon,
  MagnifyingGlassIcon,
  Cross2Icon,
  PlusIcon,
  ArrowTopRightIcon
} from '@radix-ui/react-icons';

// Mock data for demonstrations
const mockTasks: Task[] = [
  {
    id: '1',
    user_id: 'demo',
    title: 'Design new layout system',
    status: 'in_progress',
    priority: 3,
    completed: false,
    deleted: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '2', 
    user_id: 'demo',
    title: 'Implement pane navigation',
    status: 'pending',
    priority: 2,
    completed: false,
    deleted: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '3',
    user_id: 'demo', 
    title: 'Create widget dashboard',
    status: 'planning',
    priority: 1,
    completed: false,
    deleted: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
];

type LayoutMode = 'traditional' | 'panes' | 'widgets' | 'hybrid';
type PaneType = 'tasks' | 'chat' | 'calendar' | 'focus';

export const LayoutMockups: React.FC = () => {
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('traditional');
  const [activePanes, setActivePanes] = useState<PaneType[]>(['tasks']);
  const [paneOrder, setPaneOrder] = useState<PaneType[]>(['tasks', 'chat', 'calendar', 'focus']);
  
  // New state for primary/secondary pane system
  const [primaryPane, setPrimaryPane] = useState<PaneType>('tasks');
  const [secondaryPane, setSecondaryPane] = useState<PaneType>('chat');
  const [focusedPane, setFocusedPane] = useState<'primary' | 'secondary'>('primary');
  
  // State for exit animations
  const [exitingPrimaryPane, setExitingPrimaryPane] = useState<PaneType | null>(null);
  const [exitingSecondaryPane, setExitingSecondaryPane] = useState<PaneType | null>(null);
  
  // Functions to handle pane switching with exit animations
  const switchPrimaryPane = (newPane: PaneType) => {
    if (newPane === primaryPane) return;
    
    setExitingPrimaryPane(primaryPane);
    setPrimaryPane(newPane);
    
    // Clear exit state after animation
    setTimeout(() => setExitingPrimaryPane(null), 500);
  };
  
  const switchSecondaryPane = (newPane: PaneType) => {
    if (newPane === secondaryPane) return;
    
    setExitingSecondaryPane(secondaryPane);
    setSecondaryPane(newPane);
    
    // Clear exit state after animation
    setTimeout(() => setExitingSecondaryPane(null), 500);
  };
  
  const [widgetLayout, setWidgetLayout] = useState({
    tasks: { x: 0, y: 0, w: 2, h: 3 },
    chat: { x: 2, y: 0, w: 1, h: 2 },
    calendar: { x: 2, y: 2, w: 1, h: 1 },
  });

  // Keyboard shortcuts for pane switching
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (layoutMode !== 'panes') return;
      
      // Cmd/Ctrl + 1-4 for quick pane switching
      if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '4') {
        e.preventDefault();
        const paneIndex = parseInt(e.key) - 1;
        const targetPane = paneOrder[paneIndex];
        if (targetPane) {
          if (focusedPane === 'primary') {
            switchPrimaryPane(targetPane);
          } else {
            switchSecondaryPane(targetPane);
          }
        }
      }
      
      // Tab to switch focus between primary/secondary
      if (e.key === 'Tab' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setFocusedPane(focusedPane === 'primary' ? 'secondary' : 'primary');
      }
      
      // Arrow keys to cycle through panes in focused area
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const currentPane = focusedPane === 'primary' ? primaryPane : secondaryPane;
        const currentIndex = paneOrder.indexOf(currentPane);
        let nextIndex;
        
        if (e.key === 'ArrowRight') {
          nextIndex = currentIndex < paneOrder.length - 1 ? currentIndex + 1 : 0;
        } else {
          nextIndex = currentIndex > 0 ? currentIndex - 1 : paneOrder.length - 1;
        }
        
        const nextPane = paneOrder[nextIndex];
        if (focusedPane === 'primary') {
          switchPrimaryPane(nextPane);
        } else {
          switchSecondaryPane(nextPane);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [layoutMode, focusedPane, primaryPane, secondaryPane, paneOrder]);

  const renderPane = (paneType: PaneType, isActive: boolean = true, isPrimary?: boolean, isFocused?: boolean, stackDepth: number = 0, isExiting: boolean = false) => {
    const baseClasses = clsx(
      'rounded-xl border transition-all duration-500 ease-out h-full relative',
      'shadow-elevated',
      // All cards are now opaque with solid backgrounds
      'bg-ui-element-bg border-ui-border-glow/50',
      // Focus indicators with glow
      isFocused && 'ring-2 ring-brand-primary/30 shadow-glow-lg',
      !isFocused && 'shadow-glow',
      // Stacked cards get progressively darker backgrounds for depth
      stackDepth > 0 && 'bg-ui-surface border-ui-border/40',
      stackDepth > 1 && 'bg-ui-surface/80 border-ui-border/30',
      // Exit animation styles
      isExiting && 'opacity-0'
    );

    // Calculate transform for stacking effect with horizontal offset
    // Primary pane: stack to the left, Secondary pane: stack to the right
    let horizontalOffset = 0;
    let verticalOffset = 0;
    
    if (isExiting) {
      // Exit animation: fly out to the side and fade
      horizontalOffset = isPrimary ? -200 : 200;
      verticalOffset = -50;
    } else if (stackDepth > 0) {
      horizontalOffset = isPrimary ? -stackDepth * 20 : stackDepth * 20;
      verticalOffset = stackDepth * 8;
    }
    
    const transform = (stackDepth > 0 || isExiting) ? 
      `translateX(${horizontalOffset}px) translateY(${verticalOffset}px) translateZ(-${stackDepth * 10}px) scale(${isExiting ? 0.8 : 1 - stackDepth * 0.05})` : 
      'translateX(0px) translateY(0px) translateZ(0px) scale(1)';
    
    const style = {
      transform,
      zIndex: 10 - stackDepth,
      transformStyle: 'preserve-3d' as const,
    };

    switch (paneType) {
      case 'tasks':
        return (
          <div className={clsx(baseClasses, 'p-4')} style={style}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-semibold text-text-primary">Tasks</h3>
                {isPrimary && <span className="text-xs bg-brand-primary/20 text-brand-primary px-2 py-1 rounded-full">Primary</span>}
                {!isPrimary && <span className="text-xs bg-ui-border/50 text-text-muted px-2 py-1 rounded-full">Secondary</span>}
              </div>
              <ListBulletIcon className="h-5 w-5 text-text-muted" />
            </div>
            {isFocused && (
              <div className="mb-3 text-xs text-brand-primary bg-brand-surface/10 backdrop-blur-sm rounded-lg p-2 border border-brand-primary/20">
                ⌘1-4: Switch pane • ←→: Navigate • Tab: Switch focus
              </div>
            )}
            <div className="space-y-3">
              {mockTasks.slice(0, 3).map(task => (
                <div key={task.id} className="scale-90 origin-left">
                  <TaskCard
                    {...task}
                    onStartTask={() => {}}
                    onEdit={() => {}}
                    className="pointer-events-none bg-ui-element-bg/60 backdrop-blur-sm border border-ui-border/30"
                  />
                </div>
              ))}
            </div>
            {isPrimary && (
              <div className="mt-4 text-xs text-text-muted bg-ui-surface/20 backdrop-blur-sm rounded-lg p-2 border border-ui-border/20">
                <p>💡 Primary focus: Your main work area</p>
                <p className="mt-1 text-text-muted/70">Other cards stack behind this one</p>
              </div>
            )}
          </div>
        );

      case 'chat':
        return (
          <div className={clsx(baseClasses, 'p-4')} style={style}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-semibold text-text-primary">AI Assistant</h3>
                {isPrimary && <span className="text-xs bg-brand-primary/20 text-brand-primary px-2 py-1 rounded-full">Primary</span>}
                {!isPrimary && <span className="text-xs bg-ui-border/50 text-text-muted px-2 py-1 rounded-full">Secondary</span>}
              </div>
              <ChatBubbleIcon className="h-5 w-5 text-text-muted" />
            </div>
            {isFocused && (
              <div className="mb-3 text-xs text-brand-primary bg-brand-surface/20 rounded-lg p-2">
                ⌘1-4: Switch pane • ←→: Navigate • Tab: Switch focus
              </div>
            )}
            <div className="space-y-3">
              <div className="bg-ui-surface/60 rounded-lg p-3">
                <p className="text-sm text-text-secondary">I can help you organize your tasks, set priorities, or switch your workspace layout. What would you like to focus on?</p>
              </div>
              <div className="bg-brand-surface/60 rounded-lg p-3 ml-8">
                <p className="text-sm text-brand-primary">Show me my high priority tasks in the primary pane</p>
              </div>
              <div className="bg-ui-surface/60 rounded-lg p-3">
                <p className="text-sm text-text-secondary">✨ I've switched your primary pane to show high-priority tasks. Would you like me to open your calendar in the secondary pane to see upcoming deadlines?</p>
              </div>
            </div>
            {!isPrimary && (
              <div className="mt-4 text-xs text-text-muted">
                <p>🤖 AI can modify your workspace layout and content</p>
              </div>
            )}
          </div>
        );

      case 'calendar':
        return (
          <div className={clsx(baseClasses, 'p-4')} style={style}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">Calendar</h3>
              <CalendarIcon className="h-5 w-5 text-text-muted" />
            </div>
            <div className="grid grid-cols-7 gap-1 text-xs">
              {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map(day => (
                <div key={day} className="text-center p-2 text-text-muted font-medium">{day}</div>
              ))}
              {Array.from({length: 35}, (_, i) => (
                <div key={i} className={clsx(
                  'text-center p-2 rounded',
                  i === 15 && 'bg-brand-primary text-white',
                  i > 7 && i < 28 && 'text-text-primary hover:bg-ui-interactive-bg-hover'
                )}>
                  {i > 7 && i < 28 ? i - 7 : ''}
                </div>
              ))}
            </div>
          </div>
        );

      case 'focus':
        return (
          <div className={clsx(baseClasses, 'p-4')} style={style}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">Focus Session</h3>
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
            </div>
            <div className="text-center space-y-4">
              <div className="text-3xl font-mono text-brand-primary">25:00</div>
              <p className="text-sm text-text-secondary">Working on: Design new layout system</p>
              <div className="w-full bg-ui-border rounded-full h-2">
                <div className="bg-brand-primary h-2 rounded-full w-1/3 transition-all duration-1000" />
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const renderTraditionalLayout = () => (
    <div className="h-full flex flex-col">
      {/* Top Navigation */}
      <div className="h-16 bg-ui-element-bg border-b border-ui-border flex items-center px-6">
        <h2 className="text-lg font-semibold text-text-primary">Traditional Layout</h2>
        <div className="ml-auto flex space-x-2">
          <Button variant="soft">Tasks</Button>
          <Button variant="soft">Calendar</Button>
          <Button variant="soft">Settings</Button>
        </div>
      </div>
      
      <div className="flex-1 flex">
        {/* Sidebar */}
        <div className="w-64 bg-ui-element-bg border-r border-ui-border p-4">
          <div className="space-y-2">
            <Button variant="soft" className="w-full justify-start">
              <ListBulletIcon className="h-4 w-4 mr-2" />
              All Tasks
            </Button>
            <Button variant="soft" className="w-full justify-start">
              <CalendarIcon className="h-4 w-4 mr-2" />
              Calendar
            </Button>
            <Button variant="soft" className="w-full justify-start">
              <ChatBubbleIcon className="h-4 w-4 mr-2" />
              Chat
            </Button>
          </div>
        </div>
        
        {/* Main Content */}
        <div className="flex-1 p-6">
          {renderPane('tasks')}
        </div>
      </div>
    </div>
  );

  const renderPaneLayout = () => (
    <div className="h-full relative overflow-hidden">
      {/* Keyboard Shortcuts Help */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-20">
        <div className="bg-ui-element-bg/40 backdrop-blur-glass rounded-lg border border-ui-border-glow/30 px-4 py-2 shadow-glow">
          <div className="text-xs text-text-muted text-center">
            <span className="font-medium text-brand-primary">Primary/Secondary Workspace</span> • 
            <span className="ml-1">Tab: Switch focus • ⌘1-4: Quick switch • ←→: Navigate</span>
          </div>
        </div>
      </div>

      {/* Pane Selection Controls */}
      <div className="absolute top-16 left-1/2 transform -translate-x-1/2 z-20">
        <div className="flex space-x-4">
          {/* Primary Pane Selector */}
          <div className="bg-ui-element-bg/50 backdrop-blur-glass rounded-lg border border-ui-border-glow/40 p-3 shadow-glow">
            <div className="text-xs text-text-muted mb-2 text-center font-medium">Primary Focus</div>
            <div className="flex space-x-1">
              {paneOrder.map((pane) => (
                <button
                  key={`primary-selector-${pane}`}
                  onClick={() => switchPrimaryPane(pane)}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300',
                    'backdrop-blur-sm border',
                    primaryPane === pane 
                      ? 'bg-brand-primary/80 text-white shadow-glow border-brand-primary/50' 
                      : 'bg-ui-element-bg/30 text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover/50 border-ui-border/30'
                  )}
                >
                  {pane.charAt(0).toUpperCase() + pane.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Secondary Pane Selector */}
          <div className="bg-ui-element-bg/40 backdrop-blur-glass rounded-lg border border-ui-border-glow/30 p-3 shadow-glow">
            <div className="text-xs text-text-muted mb-2 text-center font-medium">Secondary Context</div>
            <div className="flex space-x-1">
              {paneOrder.map((pane) => (
                <button
                  key={`secondary-selector-${pane}`}
                  onClick={() => switchSecondaryPane(pane)}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300',
                    'backdrop-blur-sm border',
                    secondaryPane === pane 
                      ? 'bg-ui-border/60 text-text-primary shadow-glow border-ui-border/50' 
                      : 'bg-ui-element-bg/20 text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover/30 border-ui-border/20'
                  )}
                >
                  {pane.charAt(0).toUpperCase() + pane.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Split Screen Layout */}
      <div className="h-full flex pt-32 pb-8 px-8 space-x-4 overflow-visible" style={{ perspective: '1000px' }}>
        {/* Primary Pane Stack - Left Side (60% width) with left padding for stack visibility */}
        <div 
          className={clsx(
            'relative transition-all duration-300 cursor-pointer overflow-visible',
            focusedPane === 'primary' && 'ring-2 ring-brand-primary/20 rounded-xl'
          )}
          onClick={() => setFocusedPane('primary')}
          style={{ flexBasis: '60%', transformStyle: 'preserve-3d', paddingLeft: '48px' }}
        >
          {/* Render active pane and up to 2 stacked panes, plus exiting pane */}
          {(() => {
            const panesToRender = [];
            
            // Add regular panes (active + stacked)
            paneOrder.forEach((pane) => {
              const isActive = pane === primaryPane;
              
              if (isActive) {
                panesToRender.push({ pane, isActive: true, isExiting: false, stackDepth: 0 });
              } else {
                const activeIndex = paneOrder.indexOf(primaryPane);
                const paneIndex = paneOrder.indexOf(pane);
                const stackDepth = paneIndex > activeIndex ? 
                  Math.min(paneIndex - activeIndex, 2) : 
                  Math.min(paneOrder.length - activeIndex + paneIndex, 2);
                
                // Only add if within stack limit
                if (stackDepth <= 2) {
                  panesToRender.push({ pane, isActive: false, isExiting: false, stackDepth });
                }
              }
            });
            
            // Add exiting pane if it exists and is different from current panes
            if (exitingPrimaryPane && exitingPrimaryPane !== primaryPane) {
              panesToRender.push({ pane: exitingPrimaryPane, isActive: false, isExiting: true, stackDepth: 0 });
            }
            
            return panesToRender.map(({ pane, isActive, isExiting, stackDepth }) => (
              <div
                key={`primary-${pane}-${isExiting ? 'exiting' : 'normal'}`}
                className={clsx(
                  'absolute',
                  // Active card: positioned away from left edge to show stacked cards
                  isActive && 'left-8 right-0 top-0 bottom-0',
                  // Stacked and exiting cards: can extend into left padding area
                  (!isActive || isExiting) && 'left-0 right-0 top-0 bottom-0'
                )}
                style={{ 
                  zIndex: isActive ? 10 : isExiting ? 15 : 10 - stackDepth,
                  pointerEvents: isActive ? 'auto' : 'none'
                }}
              >
                {renderPane(pane, isActive, true, focusedPane === 'primary' && isActive, stackDepth, isExiting)}
              </div>
            ));
          })()}
        </div>

        {/* Secondary Pane Stack - Right Side (40% width) with right padding for stack visibility */}
        <div 
          className={clsx(
            'relative transition-all duration-300 cursor-pointer overflow-visible',
            focusedPane === 'secondary' && 'ring-2 ring-ui-border/30 rounded-xl'
          )}
          onClick={() => setFocusedPane('secondary')}
          style={{ flexBasis: '40%', transformStyle: 'preserve-3d', paddingRight: '48px' }}
        >
          {/* Render active pane and up to 2 stacked panes, plus exiting pane */}
          {(() => {
            const panesToRender = [];
            
            // Add regular panes (active + stacked)
            paneOrder.forEach((pane) => {
              const isActive = pane === secondaryPane;
              
              if (isActive) {
                panesToRender.push({ pane, isActive: true, isExiting: false, stackDepth: 0 });
              } else {
                const activeIndex = paneOrder.indexOf(secondaryPane);
                const paneIndex = paneOrder.indexOf(pane);
                const stackDepth = paneIndex > activeIndex ? 
                  Math.min(paneIndex - activeIndex, 2) : 
                  Math.min(paneOrder.length - activeIndex + paneIndex, 2);
                
                // Only add if within stack limit
                if (stackDepth <= 2) {
                  panesToRender.push({ pane, isActive: false, isExiting: false, stackDepth });
                }
              }
            });
            
            // Add exiting pane if it exists and is different from current panes
            if (exitingSecondaryPane && exitingSecondaryPane !== secondaryPane) {
              panesToRender.push({ pane: exitingSecondaryPane, isActive: false, isExiting: true, stackDepth: 0 });
            }
            
            return panesToRender.map(({ pane, isActive, isExiting, stackDepth }) => (
              <div
                key={`secondary-${pane}-${isExiting ? 'exiting' : 'normal'}`}
                className={clsx(
                  'absolute',
                  // Active card: positioned away from right edge to show stacked cards
                  isActive && 'left-0 right-8 top-0 bottom-0',
                  // Stacked and exiting cards: can extend into right padding area
                  (!isActive || isExiting) && 'left-0 right-0 top-0 bottom-0'
                )}
                style={{ 
                  zIndex: isActive ? 10 : isExiting ? 15 : 10 - stackDepth,
                  pointerEvents: isActive ? 'auto' : 'none'
                }}
              >
                {renderPane(pane, isActive, false, focusedPane === 'secondary' && isActive, stackDepth, isExiting)}
              </div>
            ));
          })()}
        </div>
      </div>

      {/* Context Indicator */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-20">
        <div className="bg-ui-element-bg/40 backdrop-blur-glass rounded-lg border border-ui-border-glow/30 px-4 py-2 shadow-glow">
          <div className="text-xs text-text-muted flex items-center space-x-2">
            <span className="font-medium text-brand-primary">{primaryPane}</span> 
            <span className="text-ui-border">+</span>
            <span className="font-medium">{secondaryPane}</span>
            {focusedPane === 'primary' && <span className="text-brand-primary">← Primary stack focused</span>}
            {focusedPane === 'secondary' && <span className="text-text-secondary">← Secondary stack focused</span>}
            <span className="text-ui-border/60">•</span>
            <span className="text-text-muted/80">Cards restack on switch</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderWidgetLayout = () => (
    <div className="h-full p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Widget Dashboard</h2>
        <div className="flex space-x-2">
          <Button variant="soft">
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Widget
          </Button>
          <Button variant="soft">
            <GridIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      {/* Grid Layout */}
      <div className="grid grid-cols-3 gap-4 h-full">
        <div className="col-span-2 row-span-3">
          {renderPane('tasks')}
        </div>
        <div className="row-span-2">
          {renderPane('chat')}
        </div>
        <div className="row-span-1">
          {renderPane('calendar')}
        </div>
      </div>
    </div>
  );

  const renderHybridLayout = () => (
    <div className="h-full relative">
      {/* Command Palette Trigger */}
      <div className="absolute top-4 right-4 z-30">
        <Button variant="soft" className="bg-ui-element-bg/90 backdrop-blur-md">
          <MagnifyingGlassIcon className="h-4 w-4 mr-1" />
          Quick Switch
        </Button>
      </div>

      {/* Floating Panels */}
      <div className="h-full p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4 h-2/3">
          <div className="relative">
            {renderPane('tasks')}
            <button className="absolute top-2 right-2 p-1 rounded bg-ui-element-bg/80 hover:bg-ui-interactive-bg-hover">
              <ArrowTopRightIcon className="h-3 w-3" />
            </button>
          </div>
          <div className="relative">
            {renderPane('focus')}
            <button className="absolute top-2 right-2 p-1 rounded bg-ui-element-bg/80 hover:bg-ui-interactive-bg-hover">
              <ArrowTopRightIcon className="h-3 w-3" />
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 h-1/3">
          <div className="relative">
            {renderPane('chat')}
            <button className="absolute top-2 right-2 p-1 rounded bg-ui-element-bg/80 hover:bg-ui-interactive-bg-hover">
              <ArrowTopRightIcon className="h-3 w-3" />
            </button>
          </div>
          <div className="relative">
            {renderPane('calendar')}
            <button className="absolute top-2 right-2 p-1 rounded bg-ui-element-bg/80 hover:bg-ui-interactive-bg-hover">
              <ArrowTopRightIcon className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="h-screen bg-ui-surface">
      {/* Layout Mode Selector */}
      <div className="absolute top-4 left-4 z-30">
        <div className="bg-ui-element-bg/90 backdrop-blur-md rounded-lg border border-ui-border p-2 flex space-x-1">
          <button
            onClick={() => setLayoutMode('traditional')}
            className={clsx(
              'p-2 rounded-md transition-all duration-200',
              layoutMode === 'traditional' 
                ? 'bg-brand-primary text-white' 
                : 'text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover'
            )}
            title="Traditional Layout"
          >
            <StackIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setLayoutMode('panes')}
            className={clsx(
              'p-2 rounded-md transition-all duration-200',
              layoutMode === 'panes' 
                ? 'bg-brand-primary text-white' 
                : 'text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover'
            )}
            title="Sliding Panes"
          >
            <LayersIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setLayoutMode('widgets')}
            className={clsx(
              'p-2 rounded-md transition-all duration-200',
              layoutMode === 'widgets' 
                ? 'bg-brand-primary text-white' 
                : 'text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover'
            )}
            title="Widget Dashboard"
          >
            <GridIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setLayoutMode('hybrid')}
            className={clsx(
              'p-2 rounded-md transition-all duration-200',
              layoutMode === 'hybrid' 
                ? 'bg-brand-primary text-white' 
                : 'text-text-muted hover:text-text-primary hover:bg-ui-interactive-bg-hover'
            )}
            title="Hybrid Layout"
          >
            <MixIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Layout Content */}
      {layoutMode === 'traditional' && renderTraditionalLayout()}
      {layoutMode === 'panes' && renderPaneLayout()}
      {layoutMode === 'widgets' && renderWidgetLayout()}
      {layoutMode === 'hybrid' && renderHybridLayout()}
    </div>
  );
}; 