import React from 'react';
import { CodeIcon, FileTextIcon } from '@radix-ui/react-icons';
import { IconButton } from '@/components/ui/IconButton';

interface SourceToggleProps {
  sourceMode: boolean;
  onToggle: () => void;
}

export const SourceToggle: React.FC<SourceToggleProps> = ({ sourceMode, onToggle }) => (
  <IconButton
    variant="ghost"
    size="2"
    aria-label={sourceMode ? 'View rendered' : 'View source'}
    title={sourceMode ? 'View rendered' : 'View source'}
    onClick={onToggle}
  >
    {sourceMode ? <FileTextIcon /> : <CodeIcon />}
  </IconButton>
);

export default SourceToggle;
