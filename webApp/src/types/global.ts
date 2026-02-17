// Global type extensions for window object
declare global {
  interface Window {
    __taskViewStoreListenerAttached?: boolean;
  }
}

export {}; // This makes the file a module
