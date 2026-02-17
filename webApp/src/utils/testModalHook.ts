/**
 * Browser DevTools Testing Script for Modal Management Hook
 *
 * To use this in the browser:
 * 1. Open DevTools Console
 * 2. Navigate to a page that uses the hook (like TodayView)
 * 3. Copy and paste these functions
 * 4. Call testModalHook() to run tests
 */

// Test function you can run in browser console
export const testModalHook = () => {
  console.log('🧪 Testing Modal Management Hook...');

  // Check if we're on a page that uses the hook
  const todayViewElement =
    document.querySelector('[data-testid="today-view"]') ||
    document.querySelector('h1:contains("Today")') ||
    document.querySelector('h1');

  if (!todayViewElement) {
    console.warn('⚠️ Navigate to TodayView page first to test the hook');
    return;
  }

  console.log('✅ Found page element, testing modal interactions...');

  // Test keyboard shortcuts
  console.log('🎹 Testing keyboard shortcuts...');

  // Simulate pressing 'a' to focus fast input
  const aEvent = new KeyboardEvent('keydown', { key: 'a', code: 'KeyA' });
  document.dispatchEvent(aEvent);
  console.log('📝 Pressed "a" - should focus fast input');

  // Simulate pressing 'Escape' to clear
  setTimeout(() => {
    const escEvent = new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape' });
    document.dispatchEvent(escEvent);
    console.log('🚪 Pressed "Escape" - should clear focus');
  }, 1000);

  // Test task interactions
  setTimeout(() => {
    const taskCards = document.querySelectorAll('[data-task-id]');
    if (taskCards.length > 0) {
      console.log(`📋 Found ${taskCards.length} task cards`);

      // Simulate clicking first task
      const firstTask = taskCards[0] as HTMLElement;
      firstTask.click();
      console.log('🖱️ Clicked first task - should open detail modal');

      // Test pressing 'Enter' to open detail
      setTimeout(() => {
        const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter' });
        document.dispatchEvent(enterEvent);
        console.log('⏎ Pressed "Enter" - should open detail modal');
      }, 1000);
    } else {
      console.log('📋 No task cards found - create some tasks first');
    }
  }, 2000);

  console.log('🏁 Test sequence started - check console for results');
};

// Helper to check modal state
export const checkModalState = () => {
  const modals = document.querySelectorAll('[role="dialog"]');
  console.log(`🔍 Found ${modals.length} open modals`);

  modals.forEach((modal, index) => {
    const title = modal.querySelector('h1, h2, h3')?.textContent || 'Unknown';
    console.log(`  Modal ${index + 1}: ${title}`);
  });

  return modals.length;
};

// Helper to simulate keyboard events
export const simulateKey = (key: string, code?: string) => {
  const event = new KeyboardEvent('keydown', {
    key,
    code: code || `Key${key.toUpperCase()}`,
    bubbles: true,
  });
  document.dispatchEvent(event);
  console.log(`⌨️ Simulated key: ${key}`);
};

// Test modal opening/closing
export const testModalOperations = () => {
  console.log('🔄 Testing modal operations...');

  // Find task cards
  const taskCards = document.querySelectorAll('[data-task-id]');
  if (taskCards.length === 0) {
    console.log('❌ No tasks found - create some tasks first');
    return;
  }

  const firstTask = taskCards[0] as HTMLElement;
  const taskId = firstTask.getAttribute('data-task-id');

  console.log(`🎯 Testing with task: ${taskId}`);

  // Test sequence
  setTimeout(() => {
    firstTask.click();
    console.log('1️⃣ Opened detail modal');
    checkModalState();
  }, 500);

  setTimeout(() => {
    simulateKey('Escape');
    console.log('2️⃣ Closed modal with Escape');
    checkModalState();
  }, 1500);

  setTimeout(() => {
    simulateKey('Enter');
    console.log('3️⃣ Reopened with Enter');
    checkModalState();
  }, 2500);
};

// Make functions available globally for console testing
if (typeof window !== 'undefined') {
  (window as any).testModalHook = testModalHook;
  (window as any).checkModalState = checkModalState;
  (window as any).simulateKey = simulateKey;
  (window as any).testModalOperations = testModalOperations;
}
