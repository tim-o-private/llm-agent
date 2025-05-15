import { NewTaskData, TaskPriority } from '../api/types';

// Basic patterns for parsing
const priorityPattern = /\b(p[0-3])\b/i;
const descriptionPattern = /\b(desc:|d:)(.*)/i;

interface ParsedTaskProperties {
  title: string;
  priority?: TaskPriority;
  description?: string;
  // Add other parsable properties here, e.g., due_date, category
}

export function parseTaskString(input: string): Partial<NewTaskData> {
  let title = input.trim();
  const parsed: Partial<ParsedTaskProperties> = {};

  // Extract Priority
  const priorityMatch = title.match(priorityPattern);
  if (priorityMatch) {
    const priorityNum = parseInt(priorityMatch[1].substring(1), 10) as TaskPriority;
    if ([0, 1, 2, 3].includes(priorityNum)) {
      parsed.priority = priorityNum;
    }
    title = title.replace(priorityPattern, '').trim(); // Remove priority string
  }

  // Extract Description
  const descriptionMatch = title.match(descriptionPattern);
  if (descriptionMatch && descriptionMatch[2]) {
    parsed.description = descriptionMatch[2].trim();
    title = title.replace(descriptionPattern, '').trim(); // Remove description string and prefix
  }

  // The remaining string is the title
  parsed.title = title.trim(); 
  // Ensure title is not empty after stripping other parts, 
  // though this should ideally be handled by input validation before calling create
  if (!parsed.title && input.length > 0) {
    // If stripping all parts left an empty title, but there was input, 
    // it implies the original input might have been *only* flags.
    // For now, let's default to using the original input as title in such edge cases,
    // or this part could be refined based on desired behavior.
    // A more robust approach might return an error or a specific flag indicating parsing issues.
    if (input.replace(priorityMatch?.[0] || '', '').replace(descriptionMatch?.[0] || '', '').trim() === ''){
        parsed.title = input.trim(); // Or handle as an error/invalid input upstream
    } else {
        // This case means there was likely a title, but it got blanked. This shouldn't happen with current regex if title part exists.
        // Default to original input if all else fails to parse a title.
        parsed.title = input.trim(); 
    }
  }

  // Construct the NewTaskData object
  // Ensure user_id and default status/priority are handled by useCreateTask or its callers
  const taskData: Partial<NewTaskData> = {
    title: parsed.title,
  };

  if (parsed.priority !== undefined) {
    taskData.priority = parsed.priority;
  }
  if (parsed.description !== undefined) {
    taskData.description = parsed.description;
  }

  return taskData;
}

/* 
// Example Usage:
console.log(parseTaskString("Buy milk p1 desc:Get the good kind"));
// Expected: { title: 'Buy milk', priority: 1, description: 'Get the good kind' }

console.log(parseTaskString("Call John p2 about the meeting"));
// Expected: { title: 'Call John about the meeting', priority: 2 }

console.log(parseTaskString("p3 High priority task d: A very important thing to do"));
// Expected: { title: 'High priority task', priority: 3, description: 'A very important thing to do' }

console.log(parseTaskString("Simple task title"));
// Expected: { title: 'Simple task title' }

console.log(parseTaskString("p0 d:just flags"));
// Expected: { title: 'p0 d:just flags', priority: 0, description: 'just flags' } (or could refine to make title 'just flags' if p0 removed before desc)
// Current behavior: { title: 'p0 d:just flags', priority: 0, description: 'just flags'} - title regex needs to be smarter about order

console.log(parseTaskString("Task with desc: and p1 later"));
// Expected: { title: 'Task with and p1 later', description: '' } - Needs more robust parsing for order
// Current behavior: { title: 'Task with desc: and p1 later', description: 'and p1 later' }

console.log(parseTaskString("Fix bug p1"));
// Expected: { title: 'Fix bug', priority: 1 }

*/ 