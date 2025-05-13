import React from 'react';
import { FAB } from '@clarity/ui';

interface FABQuickAddProps {
  onClick?: () => void;
  // className could be added if more specific styling is needed from parent
}

const PlusIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5} // Adjusted stroke width for visual preference
    stroke="currentColor"
    className="w-7 h-7" // Default size, can be overridden by FAB's icon prop styling
    {...props}
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
);

const FABQuickAdd: React.FC<FABQuickAddProps> = ({ onClick }) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      console.log('FABQuickAdd clicked, no onClick handler provided.');
    }
  };

  return (
    <FAB 
      onClick={handleClick} 
      icon={<PlusIcon />} 
      aria-label="Add new task" 
      tooltip="Add Task" // Tooltip as per FAB.tsx capabilities
      position="bottom-right" // Explicitly set position
      // Position is handled by the parent placing this component, 
      // or FAB.tsx itself could have default positioning if that's its design.
      // The placeholder in TodayView already positions it. --> This comment is a bit misleading now, FAB itself handles its fixed position.
    />
  );
};

export default FABQuickAdd; 