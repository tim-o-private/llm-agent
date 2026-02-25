import React, { useEffect, useState } from 'react';
import clsx from 'clsx';

interface ColorInfo {
  name: string;
  className: string;
  cssVariable: string;
  description?: string;
  hexValue?: string;
}

type ColorSwatchProps = ColorInfo;

const ColorSwatch: React.FC<ColorSwatchProps> = ({ name, className, cssVariable, description, hexValue }) => {
  const handleCopy = async () => {
    const copyText = `${className} | ${cssVariable} | ${hexValue || 'N/A'}`;
    try {
      await navigator.clipboard.writeText(copyText);
      // You could add a toast notification here if you have one
      console.log('Copied to clipboard:', copyText);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Check if this is a status-based style that should show text content
  const isStatusStyle = className.includes('min-h-[80px]') || className.includes('flex items-center justify-center');
  const isPriorityIndicator = className.includes('w-8 h-8 rounded-full');

  return (
    <div
      className="flex flex-col items-center space-y-2 p-3 rounded-lg border border-ui-border bg-ui-element-bg hover:bg-ui-element-bg-hover transition-colors cursor-pointer"
      onClick={handleCopy}
      title="Click to copy color information"
    >
      <div
        className={clsx(
          !isStatusStyle && !isPriorityIndicator && 'w-16 h-16 rounded-lg border border-ui-border shadow-sm',
          className,
        )}
      >
        {isStatusStyle && (
          <span className="text-xs font-medium">
            {name.includes('Task')
              ? 'Sample Task'
              : name.includes('Button')
                ? 'Button'
                : name.includes('Text')
                  ? 'Text Style'
                  : name.includes('Glow')
                    ? 'Priority'
                    : 'Interactive'}
          </span>
        )}
      </div>
      <div className="text-center">
        <div className="text-sm font-medium text-text-primary">{name}</div>
        {description && <div className="text-xs text-text-muted mt-1">{description}</div>}
        <div className="text-xs text-text-muted font-mono mt-1">{className}</div>
        <div className="text-xs text-accent font-mono mt-1">{cssVariable}</div>
        {hexValue && (
          <div className="text-xs text-text-secondary font-mono mt-1 bg-ui-bg px-2 py-1 rounded border">{hexValue}</div>
        )}
      </div>
    </div>
  );
};

// Special component for effects that need better context
const EffectSwatch: React.FC<ColorSwatchProps> = ({ name, className, cssVariable, description, hexValue }) => {
  const handleCopy = async () => {
    const copyText = `${className} | ${cssVariable} | ${hexValue || 'N/A'}`;
    try {
      await navigator.clipboard.writeText(copyText);
      console.log('Copied to clipboard:', copyText);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const isBackdropBlur = name.includes('Backdrop Blur');

  return (
    <div
      className="flex flex-col items-center space-y-2 p-3 rounded-lg border border-ui-border bg-ui-element-bg hover:bg-ui-element-bg-hover transition-colors cursor-pointer"
      onClick={handleCopy}
      title="Click to copy effect information"
    >
      {/* Effect demonstration area with better context */}
      <div className="relative w-20 h-20 flex items-center justify-center">
        {isBackdropBlur ? (
          // For backdrop blur, create a colorful background to blur against
          <div className="absolute inset-0 bg-gradient-to-br from-brand-primary via-accent-electric to-accent-glow rounded-lg">
            <div
              className={clsx(
                'absolute inset-2 rounded-lg flex items-center justify-center text-xs font-bold text-white',
                className,
              )}
            >
              BLUR
            </div>
          </div>
        ) : (
          // For shadows, use a darker background to make shadows more visible
          <div className="relative bg-gray-800 w-20 h-20 rounded-lg p-3 flex items-center justify-center">
            <div className={clsx('w-12 h-12 rounded-lg', className)} />
          </div>
        )}
      </div>

      <div className="text-center">
        <div className="text-sm font-medium text-text-primary">{name}</div>
        {description && <div className="text-xs text-text-muted mt-1">{description}</div>}
        <div className="text-xs text-text-muted font-mono mt-1 max-w-[200px] break-all">{className}</div>
        <div className="text-xs text-accent font-mono mt-1">{cssVariable}</div>
        {hexValue && (
          <div className="text-xs text-text-secondary font-mono mt-1 bg-ui-bg px-2 py-1 rounded border">{hexValue}</div>
        )}
      </div>
    </div>
  );
};

interface ColorSectionProps {
  title: string;
  description?: string;
  colors: ColorInfo[];
}

const ColorSection: React.FC<ColorSectionProps> = ({ title, description, colors }) => {
  const [colorsWithHex, setColorsWithHex] = useState<ColorInfo[]>(colors);

  useEffect(() => {
    // Get computed hex values for all colors in this section
    const getComputedHexValues = () => {
      const updatedColors = colors.map((color) => {
        try {
          // Create a temporary element to get computed styles
          const tempElement = document.createElement('div');
          tempElement.className = color.className;
          tempElement.style.position = 'absolute';
          tempElement.style.visibility = 'hidden';
          document.body.appendChild(tempElement);

          const computedStyle = window.getComputedStyle(tempElement);
          let hexValue = '';

          // Try to get background-color first, then border-color, then color
          if (color.className.includes('bg-')) {
            hexValue = computedStyle.backgroundColor;
          } else if (color.className.includes('border-')) {
            hexValue = computedStyle.borderColor;
          } else if (color.className.includes('text-')) {
            hexValue = computedStyle.color;
          }

          // Convert rgb/rgba to hex if possible
          if (hexValue && hexValue.startsWith('rgb')) {
            const rgbMatch = hexValue.match(/\d+/g);
            if (rgbMatch && rgbMatch.length >= 3) {
              const r = parseInt(rgbMatch[0]);
              const g = parseInt(rgbMatch[1]);
              const b = parseInt(rgbMatch[2]);
              hexValue = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
            }
          }

          document.body.removeChild(tempElement);

          return {
            ...color,
            hexValue: hexValue || 'N/A',
          };
        } catch {
          return {
            ...color,
            hexValue: 'Error',
          };
        }
      });

      setColorsWithHex(updatedColors);
    };

    // Small delay to ensure styles are loaded
    const timer = setTimeout(getComputedHexValues, 100);
    return () => clearTimeout(timer);
  }, [colors]);

  return (
    <div className="mb-12">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-text-primary mb-2">{title}</h2>
        {description && <p className="text-text-secondary">{description}</p>}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {colorsWithHex.map((color, index) => (
          <ColorSwatch key={index} {...color} />
        ))}
      </div>
    </div>
  );
};

const ColorSwatchPage: React.FC = () => {
  const brandColors: ColorInfo[] = [
    { name: 'Primary', className: 'bg-brand-primary', cssVariable: 'var(--accent-9)', description: 'Main brand color' },
    {
      name: 'Primary Hover',
      className: 'bg-brand-primary-hover',
      cssVariable: 'var(--accent-10)',
      description: 'Hover state',
    },
    {
      name: 'Primary Text',
      className: 'bg-brand-primary-text',
      cssVariable: 'var(--accent-contrast)',
      description: 'Text on primary',
    },
    {
      name: 'Accent Subtle',
      className: 'bg-accent-subtle',
      cssVariable: 'var(--accent-3)',
      description: 'Subtle accent',
    },
    {
      name: 'Accent Strong',
      className: 'bg-text-accent-strong',
      cssVariable: 'var(--accent-11)',
      description: 'Strong accent text',
    },
  ];

  const accentColors: ColorInfo[] = [
    {
      name: 'Electric',
      className: 'bg-accent-electric',
      cssVariable: 'var(--violet-11)',
      description: 'Electric violet',
    },
    { name: 'Neon', className: 'bg-accent-neon', cssVariable: 'var(--blue-11)', description: 'Neon blue' },
    { name: 'Glow', className: 'bg-accent-glow', cssVariable: 'var(--purple-9)', description: 'Purple glow' },
    {
      name: 'Surface',
      className: 'bg-accent-surface',
      cssVariable: 'var(--accent-surface)',
      description: 'Accent surface',
    },
    {
      name: 'Indicator',
      className: 'bg-accent-indicator',
      cssVariable: 'var(--accent-indicator)',
      description: 'Accent indicator',
    },
    { name: 'Track', className: 'bg-accent-track', cssVariable: 'var(--accent-track)', description: 'Accent track' },
  ];

  const destructiveColors: ColorInfo[] = [
    { name: 'Danger BG', className: 'bg-danger-bg', cssVariable: 'var(--red-9)', description: 'Danger background' },
    {
      name: 'Danger Hover',
      className: 'bg-danger-bg-hover',
      cssVariable: 'var(--red-10)',
      description: 'Danger hover',
    },
    { name: 'Danger Glow', className: 'bg-danger-glow', cssVariable: 'var(--red-11)', description: 'Danger glow' },
    {
      name: 'Destructive',
      className: 'bg-destructive',
      cssVariable: 'var(--red-11)',
      description: 'Destructive color',
    },
    {
      name: 'Destructive Subtle',
      className: 'bg-bg-destructive-subtle',
      cssVariable: 'var(--red-3)',
      description: 'Subtle destructive',
    },
  ];

  const statusColors: ColorInfo[] = [
    // Info Colors
    {
      name: 'Info Subtle',
      className: 'bg-bg-info-subtle',
      cssVariable: 'var(--blue-3)',
      description: 'Info background',
    },
    {
      name: 'Info Indicator',
      className: 'bg-bg-info-indicator',
      cssVariable: 'var(--blue-9)',
      description: 'Info indicator',
    },
    {
      name: 'Info Electric',
      className: 'bg-info-electric',
      cssVariable: 'var(--cyan-11)',
      description: 'Electric info',
    },

    // Warning Colors
    {
      name: 'Warning Subtle',
      className: 'bg-bg-warning-subtle',
      cssVariable: 'var(--amber-3)',
      description: 'Warning background',
    },
    {
      name: 'Warning Indicator',
      className: 'bg-bg-warning-indicator',
      cssVariable: 'var(--amber-9)',
      description: 'Warning indicator',
    },
    {
      name: 'Warning Strong',
      className: 'bg-warning-strong',
      cssVariable: 'var(--amber-11)',
      description: 'Strong warning',
    },
    {
      name: 'Warning Glow',
      className: 'bg-warning-glow',
      cssVariable: 'var(--yellow-11)',
      description: 'Warning glow',
    },

    // Success Colors
    {
      name: 'Success Subtle',
      className: 'bg-bg-success-subtle',
      cssVariable: 'var(--green-3)',
      description: 'Success background',
    },
    {
      name: 'Success Indicator',
      className: 'bg-bg-success-indicator',
      cssVariable: 'var(--green-9)',
      description: 'Success indicator',
    },
    {
      name: 'Success Strong',
      className: 'bg-success-strong',
      cssVariable: 'var(--green-11)',
      description: 'Strong success',
    },
    {
      name: 'Success Electric',
      className: 'bg-success-electric',
      cssVariable: 'var(--mint-11)',
      description: 'Electric success',
    },
  ];

  const neutralColors: ColorInfo[] = [
    {
      name: 'Neutral Subtle',
      className: 'bg-bg-neutral-subtle',
      cssVariable: 'var(--gray-3)',
      description: 'Neutral background',
    },
    {
      name: 'Neutral Indicator',
      className: 'bg-bg-neutral-indicator',
      cssVariable: 'var(--gray-9)',
      description: 'Neutral indicator',
    },
  ];

  const uiBackgrounds: ColorInfo[] = [
    { name: 'UI BG', className: 'bg-ui-bg', cssVariable: 'var(--color-background)', description: 'Main background' },
    {
      name: 'UI BG Alt',
      className: 'bg-ui-bg-alt',
      cssVariable: 'var(--gray-2)',
      description: 'Alternative background',
    },
    { name: 'UI BG Hover', className: 'bg-ui-bg-hover', cssVariable: 'var(--gray-3)', description: 'Hover background' },
    { name: 'UI BG Glow', className: 'bg-ui-bg-glow', cssVariable: 'var(--violet-2)', description: 'Glow background' },
    {
      name: 'Element BG',
      className: 'bg-ui-element-bg',
      cssVariable: 'var(--color-panel-solid)',
      description: 'Element background',
    },
    {
      name: 'Element Hover',
      className: 'bg-ui-element-bg-hover',
      cssVariable: 'var(--gray-4)',
      description: 'Element hover',
    },
    {
      name: 'Element Elevated',
      className: 'bg-ui-element-bg-elevated',
      cssVariable: 'var(--gray-1)',
      description: 'Elevated element',
    },
    {
      name: 'Modal BG',
      className: 'bg-ui-modal-bg',
      cssVariable: 'var(--color-panel-solid)',
      description: 'Modal background',
    },
  ];

  const uiInteractive: ColorInfo[] = [
    {
      name: 'Interactive BG',
      className: 'bg-ui-interactive-bg',
      cssVariable: 'var(--gray-3)',
      description: 'Interactive background',
    },
    {
      name: 'Interactive Hover',
      className: 'bg-ui-interactive-bg-hover',
      cssVariable: 'var(--gray-4)',
      description: 'Interactive hover',
    },
    {
      name: 'Interactive Active',
      className: 'bg-ui-interactive-bg-active',
      cssVariable: 'var(--accent-3)',
      description: 'Interactive active',
    },
    {
      name: 'Interactive Glow',
      className: 'bg-ui-interactive-bg-glow',
      cssVariable: 'var(--violet-4)',
      description: 'Interactive glow',
    },
  ];

  const uiSurfaces: ColorInfo[] = [
    {
      name: 'Surface',
      className: 'bg-ui-surface',
      cssVariable: 'var(--color-surface)',
      description: 'Surface background',
    },
    {
      name: 'Surface Elevated',
      className: 'bg-ui-surface-elevated',
      cssVariable: 'var(--gray-1)',
      description: 'Elevated surface',
    },
    {
      name: 'Surface Glow',
      className: 'bg-ui-surface-glow',
      cssVariable: 'var(--violet-1)',
      description: 'Glowing surface',
    },
  ];

  const borderColors: ColorInfo[] = [
    {
      name: 'Border',
      className: 'border-4 border-ui-border bg-ui-bg',
      cssVariable: 'var(--gray-6)',
      description: 'Default border',
    },
    {
      name: 'Border Hover',
      className: 'border-4 border-ui-border-hover bg-ui-bg',
      cssVariable: 'var(--gray-7)',
      description: 'Hover border',
    },
    {
      name: 'Border Focus',
      className: 'border-4 border-ui-border-focus bg-ui-bg',
      cssVariable: 'var(--accent-9)',
      description: 'Focus border',
    },
    {
      name: 'Border Glow',
      className: 'border-4 border-ui-border-glow bg-ui-bg',
      cssVariable: 'var(--violet-7)',
      description: 'Glow border',
    },
    {
      name: 'Border Electric',
      className: 'border-4 border-ui-border-electric bg-ui-bg',
      cssVariable: 'var(--blue-8)',
      description: 'Electric border',
    },
    {
      name: 'Border Destructive',
      className: 'border-4 border-border-destructive bg-ui-bg',
      cssVariable: 'var(--red-7)',
      description: 'Destructive border',
    },
  ];

  const textColors: ColorInfo[] = [
    {
      name: 'Primary',
      className: 'bg-text-primary text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--gray-12)',
      description: 'Primary text',
    },
    {
      name: 'Secondary',
      className: 'bg-text-secondary text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--gray-11)',
      description: 'Secondary text',
    },
    {
      name: 'Muted',
      className: 'bg-text-muted text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--gray-9)',
      description: 'Muted text',
    },
    {
      name: 'Disabled',
      className: 'bg-text-disabled text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--gray-8)',
      description: 'Disabled text',
    },
    {
      name: 'Accent',
      className: 'bg-text-accent text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--accent-11)',
      description: 'Accent text',
    },
    {
      name: 'Electric',
      className: 'bg-text-electric text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--violet-12)',
      description: 'Electric text',
    },
    {
      name: 'Glow',
      className: 'bg-text-glow text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--blue-12)',
      description: 'Glow text',
    },
    {
      name: 'Destructive',
      className: 'bg-text-destructive text-ui-bg flex items-center justify-center text-xs font-bold',
      cssVariable: 'var(--red-11)',
      description: 'Destructive text',
    },
  ];

  const specialEffects: ColorInfo[] = [
    {
      name: 'Glow Shadow',
      className: 'bg-brand-primary w-16 h-16 rounded-lg shadow-glow',
      cssVariable: 'rgba(139, 92, 246, 0.3)',
      description: 'Glow shadow effect',
    },
    {
      name: 'Glow Large',
      className: 'bg-accent-electric w-16 h-16 rounded-lg shadow-glow-lg',
      cssVariable: 'rgba(139, 92, 246, 0.4)',
      description: 'Large glow shadow',
    },
    {
      name: 'Electric Shadow',
      className: 'bg-accent-neon w-16 h-16 rounded-lg shadow-electric',
      cssVariable: 'rgba(59, 130, 246, 0.5)',
      description: 'Electric shadow',
    },
    {
      name: 'Neon Shadow',
      className: 'bg-accent-glow w-16 h-16 rounded-lg shadow-neon',
      cssVariable: 'rgba(168, 85, 247, 0.6)',
      description: 'Neon shadow',
    },
    {
      name: 'Elevated Shadow',
      className: 'bg-ui-element-bg w-16 h-16 rounded-lg shadow-elevated border border-ui-border',
      cssVariable: 'rgba(0, 0, 0, 0.1)',
      description: 'Elevated shadow',
    },
    {
      name: 'Backdrop Blur',
      className: 'bg-ui-element-bg/70 w-16 h-16 rounded-lg backdrop-blur-glass border border-ui-border relative',
      cssVariable: 'blur(12px)',
      description: 'Glass blur effect',
    },
  ];

  // Status-based styling examples
  const statusBasedStyles: ColorInfo[] = [
    // Task Status Examples - using proper task-like content
    {
      name: 'Pending Task',
      className:
        'border-2 border-ui-border bg-ui-element-bg/80 hover:border-ui-border-hover rounded-xl p-4 min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'Status: pending',
      description: 'Default pending task style',
    },
    {
      name: 'In Progress Task',
      className:
        'border-2 border-brand-primary bg-ui-element-bg/80 rounded-xl p-4 min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'Status: in_progress',
      description: 'Active task in progress',
    },
    {
      name: 'Completed Task',
      className:
        'opacity-70 border-2 border-ui-border bg-ui-element-bg/60 rounded-xl p-4 min-h-[80px] flex items-center justify-center text-sm text-text-muted line-through',
      cssVariable: 'Status: completed',
      description: 'Completed task (muted)',
    },
    {
      name: 'Planning Task',
      className:
        'border-2 border-brand-primary bg-ui-element-bg/80 rounded-xl p-4 min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'Status: planning',
      description: 'Task in planning phase',
    },

    // Priority Indicators - make them more visible
    {
      name: 'High Priority',
      className: 'bg-red-500 w-8 h-8 rounded-full shadow-lg shadow-red-500/50',
      cssVariable: 'Priority: 3',
      description: 'High priority indicator',
    },
    {
      name: 'Medium Priority',
      className: 'bg-amber-500 w-8 h-8 rounded-full shadow-lg shadow-amber-500/50',
      cssVariable: 'Priority: 2',
      description: 'Medium priority indicator',
    },
    {
      name: 'Low Priority',
      className: 'bg-blue-500 w-8 h-8 rounded-full shadow-lg shadow-blue-500/50',
      cssVariable: 'Priority: 1',
      description: 'Low priority indicator',
    },
    {
      name: 'Completed Priority',
      className: 'bg-gray-400 opacity-50 w-8 h-8 rounded-full',
      cssVariable: 'Priority: completed',
      description: 'Muted priority for completed',
    },

    // Priority Glows - make the glow more visible
    {
      name: 'High Priority Glow',
      className:
        'bg-ui-element-bg border-2 border-red-500/50 rounded-xl p-4 shadow-lg shadow-red-500/30 min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'shadow-danger/30',
      description: 'High priority glow effect',
    },
    {
      name: 'Medium Priority Glow',
      className:
        'bg-ui-element-bg border-2 border-amber-500/50 rounded-xl p-4 shadow-md shadow-amber-500/20 min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'shadow-warning/20',
      description: 'Medium priority glow effect',
    },
    {
      name: 'Low Priority Glow',
      className:
        'bg-ui-element-bg border-2 border-ui-border rounded-xl p-4 shadow-sm min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'shadow-sm',
      description: 'Low priority subtle shadow',
    },

    // Interactive States - make them more dramatic
    {
      name: 'Focused Task',
      className:
        'ring-4 ring-blue-500/50 shadow-xl transform -translate-y-1 scale-[1.02] border-2 border-blue-500 bg-ui-element-bg rounded-xl p-4 min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'Focus ring + transform',
      description: 'Keyboard focused task',
    },
    {
      name: 'Selected Active',
      className:
        'ring-2 ring-brand-primary/50 border-2 border-brand-primary bg-ui-element-bg rounded-xl p-4 min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'ring-brand-primary/50',
      description: 'Selected active task',
    },
    {
      name: 'Selected Completed',
      className:
        'ring-2 ring-ui-border/50 opacity-70 border-2 border-ui-border bg-ui-element-bg/60 rounded-xl p-4 min-h-[80px] flex items-center justify-center text-sm text-text-muted',
      cssVariable: 'ring-ui-border/50',
      description: 'Selected completed task',
    },

    // Text States - make them show actual text styling
    {
      name: 'Active Text',
      className:
        'bg-ui-element-bg text-text-primary flex items-center justify-center text-sm font-medium rounded-lg p-4 border border-ui-border min-h-[80px]',
      cssVariable: 'text-text-primary',
      description: 'Active task text',
    },
    {
      name: 'Hover Text',
      className:
        'bg-ui-element-bg text-brand-primary flex items-center justify-center text-sm font-medium rounded-lg p-4 border border-brand-primary min-h-[80px]',
      cssVariable: 'text-brand-primary',
      description: 'Hovered task text',
    },
    {
      name: 'Completed Text',
      className:
        'bg-ui-element-bg text-text-muted flex items-center justify-center text-sm font-medium rounded-lg p-4 border border-ui-border line-through opacity-70 min-h-[80px]',
      cssVariable: 'text-text-muted + line-through',
      description: 'Completed task text',
    },

    // Button States - make them look like actual buttons
    {
      name: 'Active Button',
      className:
        'p-4 rounded-lg hover:bg-ui-interactive-bg-hover backdrop-blur-sm hover:shadow-lg bg-ui-element-bg border border-ui-border transition-all duration-200 cursor-pointer min-h-[80px] flex items-center justify-center text-sm text-text-primary',
      cssVariable: 'Interactive button',
      description: 'Active task button',
    },
    {
      name: 'Completed Button',
      className:
        'p-4 rounded-lg hover:bg-ui-interactive-bg-hover/60 backdrop-blur-sm bg-ui-element-bg/60 border border-ui-border opacity-70 transition-all duration-200 cursor-pointer min-h-[80px] flex items-center justify-center text-sm text-text-muted',
      cssVariable: 'Muted button',
      description: 'Completed task button',
    },
  ];

  return (
    <div className="min-h-screen bg-ui-bg">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-text-primary mb-4">Color Palette</h1>
          <p className="text-text-secondary text-lg max-w-2xl mx-auto">
            Complete color system from our Tailwind configuration. These colors are designed to work together
            harmoniously across light and dark themes with enhanced vibrancy and modern effects.
          </p>
          <div className="mt-4 p-4 bg-ui-element-bg rounded-lg border border-ui-border">
            <p className="text-sm text-text-muted">
              <strong>Legend:</strong> Each swatch shows the Tailwind class, CSS variable, and computed hex value. Hex
              values are dynamically calculated from your current theme.
            </p>
          </div>
        </div>

        {/* Color Sections */}
        <ColorSection
          title="Brand & Primary Colors"
          description="Core brand colors and primary accent variations"
          colors={brandColors}
        />

        <ColorSection
          title="Accent Variations"
          description="Enhanced accent colors with electric, neon, and glow effects"
          colors={accentColors}
        />

        <ColorSection
          title="Destructive & Danger Colors"
          description="Error states, warnings, and destructive actions"
          colors={destructiveColors}
        />

        <ColorSection
          title="Status Colors"
          description="Info, warning, and success state colors with enhanced vibrancy"
          colors={statusColors}
        />

        <ColorSection title="Neutral Colors" description="Neutral and muted color variations" colors={neutralColors} />

        <ColorSection
          title="UI Backgrounds"
          description="Background colors for different UI elements and states"
          colors={uiBackgrounds}
        />

        <ColorSection
          title="Interactive Elements"
          description="Colors for interactive components and their states"
          colors={uiInteractive}
        />

        <ColorSection
          title="Surface Colors"
          description="Surface backgrounds with elevation and glow effects"
          colors={uiSurfaces}
        />

        <ColorSection
          title="Border Colors"
          description="Border colors for different states and effects"
          colors={borderColors}
        />

        <ColorSection
          title="Text Colors"
          description="Text colors for different hierarchy levels and states"
          colors={textColors}
        />

        {/* Special Effects Section - Custom implementation for better effect demonstration */}
        <div className="mb-12">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-text-primary mb-2">Special Effects</h2>
            <p className="text-text-secondary">Shadow effects, glows, and backdrop blur demonstrations</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {specialEffects.map((effect, index) => (
              <EffectSwatch key={index} {...effect} />
            ))}
          </div>
        </div>

        <ColorSection
          title="Status-Based Styles"
          description="Task status styling system with priority indicators, interactive states, and text variations"
          colors={statusBasedStyles}
        />

        {/* Animation Demos */}
        <div className="mb-12">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-text-primary mb-2">Animation Effects</h2>
            <p className="text-text-secondary">Custom animations and keyframe effects</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div className="flex flex-col items-center space-y-2 p-3 rounded-lg border border-ui-border bg-ui-element-bg">
              <div className="w-16 h-16 rounded-lg bg-brand-primary animate-glow-pulse" />
              <div className="text-center">
                <div className="text-sm font-medium text-text-primary">Glow Pulse</div>
                <div className="text-xs text-text-muted font-mono">animate-glow-pulse</div>
              </div>
            </div>
            <div className="flex flex-col items-center space-y-2 p-3 rounded-lg border border-ui-border bg-ui-element-bg">
              <div className="w-16 h-16 rounded-lg bg-gradient-to-r from-brand-primary to-accent-electric animate-gradient-shift bg-[length:200%_200%]" />
              <div className="text-center">
                <div className="text-sm font-medium text-text-primary">Gradient Shift</div>
                <div className="text-xs text-text-muted font-mono">animate-gradient-shift</div>
              </div>
            </div>
            <div className="flex flex-col items-center space-y-2 p-3 rounded-lg border border-ui-border bg-ui-element-bg">
              <div className="w-16 h-16 rounded-lg bg-accent-glow animate-float" />
              <div className="text-center">
                <div className="text-sm font-medium text-text-primary">Float</div>
                <div className="text-xs text-text-muted font-mono">animate-float</div>
              </div>
            </div>
            <div className="flex flex-col items-center space-y-2 p-3 rounded-lg border border-ui-border bg-ui-element-bg">
              <div className="w-16 h-16 rounded-lg bg-gradient-to-r from-transparent via-brand-primary to-transparent animate-shimmer bg-[length:200%_100%]" />
              <div className="text-center">
                <div className="text-sm font-medium text-text-primary">Shimmer</div>
                <div className="text-xs text-text-muted font-mono">animate-shimmer</div>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Notes */}
        <div className="mt-16 p-6 rounded-lg bg-ui-element-bg border border-ui-border">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Usage Notes</h3>
          <div className="space-y-2 text-text-secondary">
            <p>• All colors are CSS custom properties that automatically adapt to light/dark themes</p>
            <p>• Glow and electric variants are designed for accent and highlight usage</p>
            <p>• Interactive colors provide smooth hover and active state transitions</p>
            <p>• Shadow effects can be combined with colors for enhanced depth</p>
            <p>• Backdrop blur effects work best with semi-transparent backgrounds</p>
            <p>• Hex values are computed dynamically and may vary between light/dark themes</p>
          </div>
        </div>

        {/* Copy Helper */}
        <div className="mt-8 p-4 bg-ui-element-bg rounded-lg border border-ui-border">
          <h4 className="text-md font-semibold text-text-primary mb-2">Quick Copy</h4>
          <p className="text-sm text-text-muted mb-3">Click any color swatch to copy its information to clipboard</p>
          <div className="text-xs text-text-muted">
            Format: <code className="bg-ui-bg px-2 py-1 rounded">className | cssVariable | hexValue</code>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColorSwatchPage;
