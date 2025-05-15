import React, { useState } from 'react';
import { Input } from '../Input'; 
import { Button } from '../Button'; 

// A simple Send Icon component (can be replaced with a more sophisticated one or an SVG library)
const SendIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    viewBox="0 0 20 20" 
    fill="currentColor" 
    className="w-5 h-5" 
    {...props}
  >
    <path d="M3.105 3.105a.5.5 0 01.815-.093l12 8a.5.5 0 010 .874l-12 8a.5.5 0 01-.815-.781L14.39 10 3.105 3.886a.5.5 0 010-.781z" />
  </svg>
);

export interface MessageInputProps {
  onSendMessage: (message: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  placeholder = "Type your message...",
  disabled = false,
}) => {
  const [inputValue, setInputValue] = useState('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const message = inputValue.trim();
    if (message) {
      onSendMessage(message);
      setInputValue(''); // Clear input after sending
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center p-2 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
      <Input
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        placeholder={placeholder}
        className="flex-grow mr-2 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded-lg focus:ring-blue-500 focus:border-blue-500"
        disabled={disabled}
        aria-label="Chat message input"
      />
      <Button 
        type="submit" 
        variant="primary" 
        className="px-3 py-2 rounded-lg" // Ensure padding for icon button
        disabled={disabled || inputValue.trim() === ''}
        aria-label="Send message"
      >
        <SendIcon />
      </Button>
    </form>
  );
}; 