export interface AppError {
  message: string;
  code?: string; // Optional: for specific error codes
  details?: unknown; // For additional error information, type unknown is safer than any
} 