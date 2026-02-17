import React, { useState } from 'react';
import clsx from 'clsx';
import { getCompleteInteractiveClasses, type InteractiveElementProps } from '@/utils/focusStates';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

const DesignSystemPage: React.FC = () => {
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [focusedCard, setFocusedCard] = useState<string | null>(null);

  // Component State Examples
  const ComponentStateExample: React.FC<{
    title: string;
    description: string;
    children: React.ReactNode;
  }> = ({ title, description, children }) => (
    <div className="mb-8">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-text-primary mb-1">{title}</h3>
        <p className="text-sm text-text-secondary">{description}</p>
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );

  // Task Card Component States - Now using global focus system
  const TaskCard: React.FC<{
    title: string;
    status: 'active' | 'completed' | 'deleted';
    priority: 'high' | 'medium' | 'low' | null;
    selected?: boolean;
    focused?: boolean;
    isParent?: boolean;
    isChild?: boolean;
    onClick?: () => void;
  }> = ({ title, status, priority, selected, focused, isParent, isChild, onClick }) => {
    const getStatusSpecificStyles = () => {
      if (status === 'completed') {
        return 'opacity-70 bg-ui-element-bg/60 text-text-muted line-through';
      }

      if (status === 'deleted') {
        return 'opacity-40 bg-red-50 border-red-200 text-red-400 line-through';
      }

      return '';
    };

    const getHierarchyStyles = () => {
      let styles = '';

      if (isParent) {
        styles += ' shadow-lg border-brand-primary/30';
      }

      if (isChild) {
        styles += ' ml-6 border-l-4 border-l-brand-primary/50 bg-ui-element-bg/80';
      }

      return styles;
    };

    const interactiveProps: InteractiveElementProps = {
      variant: 'card',
      focusState: focused ? 'focused' : selected ? 'selected' : 'default',
      interactionState: status === 'deleted' ? 'disabled' : 'default',
    };

    const getPriorityIndicator = () => {
      if (!priority || status === 'completed' || status === 'deleted') {
        return status === 'completed' ? <div className="w-3 h-3 rounded-full bg-gray-400 opacity-50" /> : null;
      }

      const colors = {
        high: 'bg-red-500 shadow-lg shadow-red-500/50',
        medium: 'bg-amber-500 shadow-lg shadow-amber-500/50',
        low: 'bg-blue-500 shadow-lg shadow-blue-500/50',
      };

      return <div className={clsx('w-3 h-3 rounded-full', colors[priority])} />;
    };

    return (
      <div
        className={clsx(
          'p-4',
          getCompleteInteractiveClasses(interactiveProps),
          getStatusSpecificStyles(),
          getHierarchyStyles(),
        )}
        onClick={onClick}
        tabIndex={0} // Make focusable with keyboard
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getPriorityIndicator()}
            <span className="text-sm font-medium">{title}</span>
            {isParent && (
              <span className="text-xs bg-brand-primary/20 text-brand-primary px-2 py-1 rounded">Parent</span>
            )}
            {isChild && <span className="text-xs bg-ui-border text-text-muted px-2 py-1 rounded">Child</span>}
          </div>
          <div className="text-xs text-text-muted capitalize">{status}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-ui-bg">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-text-primary mb-4">Design System</h1>
          <p className="text-text-secondary text-lg max-w-3xl mx-auto">
            Our unified visual design language with consistent focus states across all interactive elements. All
            components use the same focus ring system for accessibility and consistency.
          </p>
          <div className="mt-4 p-4 bg-ui-element-bg rounded-lg border border-ui-border">
            <p className="text-sm text-text-muted">
              <strong>Focus System:</strong> Blue ring for keyboard focus, brand color ring for selection, red ring for
              errors. Try tabbing through elements or clicking to see consistent focus behavior.
            </p>
          </div>
        </div>

        {/* Global Focus System Demo */}
        <ComponentStateExample
          title="Global Focus System"
          description="Consistent focus rings across all interactive elements - cards, buttons, and inputs all use the same system"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-text-primary">Task Cards</h4>
              <TaskCard title="Focusable Card" status="active" priority="medium" />
              <TaskCard title="Selected Card" status="active" priority="medium" selected />
              <TaskCard title="Focused Card" status="active" priority="medium" focused />
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-medium text-text-primary">Buttons</h4>
              <Button variant="solid">Solid Button</Button>
              <Button variant="soft">Soft Button</Button>
              <Button variant="outline">Outline Button</Button>
              <Button variant="ghost">Ghost Button</Button>
              <Button variant="solid" color="red">
                Danger Button
              </Button>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-medium text-text-primary">Inputs</h4>
              <Input placeholder="Default input..." />
              <Input placeholder="Error input..." error />
              <Input placeholder="Disabled input..." disabled />
              <Input placeholder="Large input..." size="3" />
              <Input placeholder="Soft variant..." variant="soft" />
              <Input placeholder="Classic variant..." variant="classic" />
              <Input placeholder="Blue color..." color="blue" variant="soft" />
            </div>
          </div>
        </ComponentStateExample>

        {/* Component Hierarchy */}
        <ComponentStateExample
          title="Component Hierarchy"
          description="Visual distinction between parent and child components, with proper nesting and relationship indicators"
        >
          <div className="space-y-3">
            <TaskCard title="Parent Task - Project Planning" status="active" priority="high" isParent />
            <TaskCard title="Child Task - Research competitors" status="active" priority="medium" isChild />
            <TaskCard title="Child Task - Define requirements" status="completed" priority="medium" isChild />
            <TaskCard title="Child Task - Create wireframes" status="active" priority="low" isChild />
          </div>
        </ComponentStateExample>

        {/* Task States */}
        <ComponentStateExample
          title="Task States"
          description="Different states a task can be in, with appropriate visual feedback"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <TaskCard title="Active Task" status="active" priority="medium" />
            <TaskCard title="Completed Task" status="completed" priority="medium" />
            <TaskCard title="Deleted Task" status="deleted" priority="medium" />
          </div>
        </ComponentStateExample>

        {/* Priority Levels */}
        <ComponentStateExample
          title="Priority Levels"
          description="Visual priority indicators with appropriate colors and emphasis"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <TaskCard title="High Priority Task" status="active" priority="high" />
            <TaskCard title="Medium Priority Task" status="active" priority="medium" />
            <TaskCard title="Low Priority Task" status="active" priority="low" />
          </div>
        </ComponentStateExample>

        {/* Interactive States */}
        <ComponentStateExample
          title="Interactive States"
          description="Selection and focus states for keyboard and mouse interaction - all using the same focus ring system"
        >
          <div className="space-y-3">
            <TaskCard title="Default Task (try tabbing to focus)" status="active" priority="medium" />
            <TaskCard title="Selected Task" status="active" priority="medium" selected />
            <TaskCard title="Focused Task (Keyboard Navigation)" status="active" priority="medium" focused />
            <TaskCard title="Selected + Focused Task" status="active" priority="medium" selected focused />
          </div>
        </ComponentStateExample>

        {/* Surface Elevation */}
        <ComponentStateExample
          title="Surface Elevation"
          description="Different elevation levels for layering and depth"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 bg-ui-element-bg border border-ui-border rounded-xl">
              <h4 className="font-medium text-text-primary mb-2">Base Surface</h4>
              <p className="text-sm text-text-secondary">Standard component background</p>
            </div>
            <div className="p-6 bg-ui-element-bg-elevated border border-ui-border rounded-xl shadow-elevated">
              <h4 className="font-medium text-text-primary mb-2">Elevated Surface</h4>
              <p className="text-sm text-text-secondary">Cards, modals, dropdowns</p>
            </div>
            <div className="p-6 bg-ui-element-bg border border-ui-border-glow rounded-xl shadow-glow">
              <h4 className="font-medium text-text-primary mb-2">Glow Surface</h4>
              <p className="text-sm text-text-secondary">Highlighted or active elements</p>
            </div>
          </div>
        </ComponentStateExample>

        {/* Typography Hierarchy */}
        <ComponentStateExample
          title="Typography Hierarchy"
          description="Text styling for different content levels and states"
        >
          <div className="space-y-4">
            <h1 className="text-3xl font-bold text-text-primary">Heading 1 - Page Title</h1>
            <h2 className="text-2xl font-semibold text-text-primary">Heading 2 - Section Title</h2>
            <h3 className="text-lg font-medium text-text-primary">Heading 3 - Subsection</h3>
            <p className="text-base text-text-primary">Body text - Primary content with good readability</p>
            <p className="text-sm text-text-secondary">Secondary text - Supporting information</p>
            <p className="text-xs text-text-muted">Muted text - Metadata, timestamps, hints</p>
            <p className="text-sm text-text-accent font-medium">Accent text - Links, highlights, calls to action</p>
            <p className="text-sm text-text-destructive">Destructive text - Errors, warnings, delete actions</p>
            <p className="text-sm text-text-disabled">Disabled text - Inactive or unavailable content</p>
          </div>
        </ComponentStateExample>

        {/* Design Principles */}
        <div className="mt-16 p-6 rounded-lg bg-ui-element-bg border border-ui-border">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Design Principles</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-text-primary mb-2">Global Focus System</h4>
              <ul className="text-sm text-text-secondary space-y-1">
                <li>
                  • <strong>Blue ring:</strong> Keyboard focus (always consistent)
                </li>
                <li>
                  • <strong>Brand ring:</strong> Selection state
                </li>
                <li>
                  • <strong>Red ring:</strong> Error state
                </li>
                <li>
                  • <strong>No transforms:</strong> Focus rings stay flat for clean appearance
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-text-primary mb-2">States</h4>
              <ul className="text-sm text-text-secondary space-y-1">
                <li>• Active: Full opacity, clear borders, interactive</li>
                <li>• Completed: Reduced opacity, muted colors, strikethrough</li>
                <li>• Deleted: Very low opacity, red tint, strikethrough</li>
                <li>• Disabled: Reduced opacity, no interaction</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-text-primary mb-2">Hierarchy</h4>
              <ul className="text-sm text-text-secondary space-y-1">
                <li>• Parent components have stronger borders and shadows</li>
                <li>• Child components are indented and have subtle left borders</li>
                <li>• Priority is indicated by colored dots with appropriate shadows</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-text-primary mb-2">Consistency</h4>
              <ul className="text-sm text-text-secondary space-y-1">
                <li>• All interactive elements use the same focus system</li>
                <li>• Predictable color usage for similar states</li>
                <li>• Smooth transitions for all interactive elements</li>
                <li>• Accessible keyboard navigation with clear focus indicators</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DesignSystemPage;
