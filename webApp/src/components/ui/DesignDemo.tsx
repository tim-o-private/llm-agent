import React, { useState } from 'react';
import clsx from 'clsx';

interface DemoTaskCardProps {
  title: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 0 | 1 | 2 | 3;
  isSelected?: boolean;
  isFocused?: boolean;
  isHovered?: boolean;
  onClick?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

const DemoTaskCard: React.FC<DemoTaskCardProps> = ({
  title,
  status,
  priority,
  isSelected,
  isFocused,
  isHovered,
  onClick,
  onMouseEnter,
  onMouseLeave,
}) => {
  // Status colors - muted for completed tasks
  const statusColors = {
    pending: 'border-gray-300 dark:border-gray-600',
    in_progress: 'border-blue-500 dark:border-blue-400',
    completed: 'border-gray-300 dark:border-gray-700', // Much more muted
  };

  // Priority ambient effects (very subtle, disabled for completed)
  const priorityEffects = {
    0: '',
    1: status === 'completed' ? '' : 'shadow-sm',
    2: status === 'completed' ? '' : 'shadow-md shadow-amber-200/20 dark:shadow-amber-500/10',
    3: status === 'completed' ? '' : 'shadow-lg shadow-red-200/30 dark:shadow-red-500/15',
  };

  return (
    <div
      className={clsx(
        // Base card styling with glassy effect
        'relative p-4 rounded-lg border-2 transition-all duration-300 ease-out cursor-pointer',
        'backdrop-blur-sm bg-white/80 dark:bg-gray-800/80',
        
        // Completed tasks are more muted
        status === 'completed' && 'opacity-70',
        
        // Status-based border colors
        statusColors[status],
        
        // Priority ambient effects (subtle, disabled for completed)
        priorityEffects[priority],
        
        // Interaction states - ELEVATION HIERARCHY
        {
          // Default state
          'shadow-sm': !isHovered && !isSelected && !isFocused,
          
          // Hover state - moderate elevation (reduced for completed)
          'shadow-lg transform -translate-y-1 scale-[1.02]': isHovered && !isSelected && !isFocused && status !== 'completed',
          'shadow-md transform -translate-y-0.5 scale-[1.01]': isHovered && !isSelected && !isFocused && status === 'completed',
          
          // Selected state - same elevation as hover (keyboard/mouse parity)
          'shadow-lg transform -translate-y-1 scale-[1.02] ring-2 ring-blue-500/50': isSelected && !isFocused && status !== 'completed',
          'shadow-md transform -translate-y-0.5 scale-[1.01] ring-2 ring-gray-400/50': isSelected && !isFocused && status === 'completed',
          
          // Focused state - MORE SUBTLE glow (less translate, slower animation)
          'shadow-xl transform -translate-y-1 scale-[1.02] ring-3 ring-blue-500/20': isFocused && status !== 'completed',
          'shadow-lg transform -translate-y-0.5 scale-[1.01] ring-2 ring-gray-400/30': isFocused && status === 'completed',
        },
        
        // In-progress glow (the ONE task being worked on) - more subtle pulse
        status === 'in_progress' && isFocused && 'shadow-blue-500/20 animate-pulse',
      )}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* Glassy overlay for extra depth */}
      <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-white/10 to-transparent pointer-events-none" />
      
      {/* Priority indicator - subtle visual weight, not color bars */}
      {priority > 0 && status !== 'completed' && (
        <div className={clsx(
          'absolute top-2 right-2 w-2 h-2 rounded-full',
          priority === 1 && 'bg-blue-400 dark:bg-blue-500',
          priority === 2 && 'bg-amber-400 dark:bg-amber-500',
          priority === 3 && 'bg-red-400 dark:bg-red-500',
        )} />
      )}
      
      {/* Muted priority indicator for completed tasks */}
      {priority > 0 && status === 'completed' && (
        <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-600 opacity-50" />
      )}
      
      <h3 className={clsx(
        'font-medium relative z-10',
        status === 'completed' 
          ? 'line-through text-gray-500 dark:text-gray-500' // More muted text
          : 'text-gray-900 dark:text-gray-100'
      )}>
        {title}
      </h3>
      
      <div className="mt-2 flex items-center justify-between relative z-10">
        <span className={clsx(
          'text-xs px-2 py-1 rounded-full font-medium backdrop-blur-sm',
          status === 'pending' && 'bg-gray-200/80 text-gray-700 dark:bg-gray-700/80 dark:text-gray-300',
          status === 'in_progress' && 'bg-blue-200/80 text-blue-800 dark:bg-blue-900/80 dark:text-blue-200',
          status === 'completed' && 'bg-gray-200/60 text-gray-600 dark:bg-gray-700/60 dark:text-gray-400', // More muted
        )}>
          {status.replace('_', ' ')}
        </span>
        
        {priority > 0 && (
          <span className={clsx(
            'text-xs',
            status === 'completed' 
              ? 'text-gray-400 dark:text-gray-500' // Muted priority text
              : 'text-gray-500 dark:text-gray-400'
          )}>
            P{priority}
          </span>
        )}
      </div>
    </div>
  );
};

export const DesignDemo: React.FC = () => {
  const [selectedCard, setSelectedCard] = useState<number | null>(null);
  const [focusedCard, setFocusedCard] = useState<number | null>(1); // Simulate one focused task
  const [hoveredCard, setHoveredCard] = useState<number | null>(null);

  const demoTasks = [
    { title: 'Review quarterly reports', status: 'completed' as const, priority: 1 as const },
    { title: 'Implement user authentication', status: 'in_progress' as const, priority: 3 as const },
    { title: 'Design new landing page', status: 'pending' as const, priority: 2 as const },
    { title: 'Update documentation', status: 'completed' as const, priority: 0 as const },
    { title: 'Fix responsive layout bug', status: 'pending' as const, priority: 2 as const },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50/30 to-purple-50/20 dark:from-gray-900 dark:via-blue-950/30 dark:to-purple-950/20 p-8">
      {/* Glassy container */}
      <div className="max-w-4xl mx-auto">
        <div className="backdrop-blur-lg bg-white/70 dark:bg-gray-900/70 rounded-2xl p-8 shadow-xl border border-white/20 dark:border-gray-700/20">
          <div className="space-y-6">
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Refined Animation & Visual Hierarchy Demo
              </h2>
              
              <div className="grid gap-4 max-w-2xl">
                <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1 backdrop-blur-sm bg-white/50 dark:bg-gray-800/50 p-4 rounded-lg border border-white/30 dark:border-gray-700/30">
                  <p><strong>Design Updates:</strong></p>
                  <p>• Completed tasks: Muted colors, reduced interactions, subtle priority indicators</p>
                  <p>• Focus state: More subtle (less translate, gentler ring, slower animation)</p>
                  <p>• Glassy effects: Backdrop blur, translucent backgrounds, gradient overlays</p>
                  <p>• Theme colors: Blue for in-progress, muted grays for completed</p>
                  <p>• Priority dots: Visible but not distracting, disabled for completed tasks</p>
                </div>
              </div>
            </div>

            <div className="grid gap-3 max-w-2xl">
              {demoTasks.map((task, index) => (
                <DemoTaskCard
                  key={index}
                  title={task.title}
                  status={task.status}
                  priority={task.priority}
                  isSelected={selectedCard === index}
                  isFocused={focusedCard === index}
                  isHovered={hoveredCard === index}
                  onClick={() => setSelectedCard(selectedCard === index ? null : index)}
                  onMouseEnter={() => setHoveredCard(index)}
                  onMouseLeave={() => setHoveredCard(null)}
                />
              ))}
            </div>

            <div className="mt-8 backdrop-blur-sm bg-white/60 dark:bg-gray-800/60 rounded-lg p-4 max-w-2xl border border-white/30 dark:border-gray-700/30">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Interactive Demo Controls:
              </h3>
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <p>• <strong>Click</strong> cards to select/deselect</p>
                <p>• <strong>Hover</strong> to see elevation effects</p>
                <p>• Card #2 is "focused" (the active work item)</p>
                <p>• Notice: Completed tasks are muted, focus is more subtle</p>
              </div>
              
              <div className="mt-4 space-x-4">
                <button
                  onClick={() => setFocusedCard(focusedCard === 1 ? null : 1)}
                  className="px-3 py-1 bg-blue-500/80 backdrop-blur-sm text-white rounded text-sm hover:bg-blue-600/80 transition-colors border border-blue-400/30"
                >
                  Toggle Focus on Task #2
                </button>
                <button
                  onClick={() => setSelectedCard(null)}
                  className="px-3 py-1 bg-gray-500/80 backdrop-blur-sm text-white rounded text-sm hover:bg-gray-600/80 transition-colors border border-gray-400/30"
                >
                  Clear Selection
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}; 