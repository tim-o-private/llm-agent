# Cleanup Test Plan - Unused Files Removal

## 🎯 **OBJECTIVE**
Verify that removing 3 unused files and cleaning up references doesn't break any functionality.

## 📋 **FILES REMOVED**
1. `chatServer/routers/chat_router.py` (116 lines)
2. `webApp/src/components/tasks/TaskDetailTray.tsx` (111 lines)  
3. `webApp/src/pages/Dashboard.tsx` (20 lines)
4. **Routes**: Removed `/dashboard` route from App.tsx
5. **Cleanup**: Removed TaskDetailTray references from OverlayManager

## 🧪 **TEST CATEGORIES**

### 1. **Build & Compilation Tests** ⚡
**Priority**: Critical - Must pass before other tests

```bash
# Frontend build test
cd webApp && npm run build

# Backend startup test  
cd chatServer && python main.py

# TypeScript compilation
cd webApp && npx tsc --noEmit

# Linting
cd webApp && npm run lint
```

**Expected**: ✅ All builds succeed, no import errors, no TypeScript errors

---

### 2. **API Endpoint Tests** 🔌
**Priority**: High - Verify chat functionality works

#### Test 2.1: Chat Endpoint Functionality
```bash
# Start chatServer
cd chatServer && python main.py

# Test chat endpoint (replace with actual auth token)
curl -X POST http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "Hello", "agent_id": "assistant"}'
```

**Expected**: ✅ Chat endpoint responds correctly (not 404/500)

#### Test 2.2: Verify Old Router Gone
```bash
# This should NOT exist anymore
curl -X POST http://localhost:3001/api/chat/send_message
```

**Expected**: ✅ 404 Not Found (old router endpoint removed)

---

### 3. **Frontend Navigation Tests** 🧭
**Priority**: High - Verify routing works

#### Test 3.1: Route Accessibility
```bash
# Start webApp
cd webApp && npm run dev
```

**Manual Tests**:
- ✅ Navigate to `/` - Home page loads
- ✅ Navigate to `/login` - Login page loads  
- ✅ Navigate to `/today` - TodayView loads (after auth)
- ✅ Navigate to `/coach` - CoachPage loads (after auth)
- ❌ Navigate to `/dashboard` - Should show 404/redirect
- ✅ Navigate to `/coach-v2` - CoachPageV2 loads (testing route)

#### Test 3.2: Default Route Behavior
- ✅ Root `/` redirects appropriately
- ✅ Protected routes redirect to login when unauthenticated
- ✅ Default protected route shows TodayView

---

### 4. **Task Management Tests** ✅
**Priority**: High - Verify task functionality intact

#### Test 4.1: Quick Add Task Flow
1. ✅ Navigate to `/today`
2. ✅ Click FAB (Floating Action Button)
3. ✅ AddTaskTray opens correctly
4. ✅ Enter task title and submit
5. ✅ Task appears in task list
6. ✅ Tray closes after submission

#### Test 4.2: Task Detail Flow  
1. ✅ Click on existing task
2. ✅ Task detail overlay opens (should use AddTaskTray)
3. ✅ Can edit task details
4. ✅ Changes save correctly
5. ✅ Overlay closes properly

**Expected**: ✅ AddTaskTray handles both quick add and detail modes seamlessly

---

### 5. **Overlay System Tests** 🎭
**Priority**: Medium - Verify overlay management works

#### Test 5.1: Overlay Store Functionality
```typescript
// Test in browser console
useOverlayStore.getState().openOverlay('quickAddTray');
// Should open AddTaskTray

useOverlayStore.getState().openOverlay('taskDetailTray', { taskId: '123' });
// Should open AddTaskTray in detail mode

useOverlayStore.getState().closeOverlay();
// Should close any open overlay
```

#### Test 5.2: Multiple Overlay Types
- ✅ `quickAddTray` opens AddTaskTray
- ✅ `taskDetailTray` opens AddTaskTray  
- ✅ Only one overlay open at a time
- ✅ ESC key closes overlays
- ✅ Click outside closes overlays

---

### 6. **Error Handling Tests** ⚠️
**Priority**: Medium - Verify graceful degradation

#### Test 6.1: Import Error Detection
```bash
# Search for any remaining references
grep -r "TaskDetailTray" webApp/src/ --exclude-dir=node_modules
grep -r "Dashboard" webApp/src/ --exclude-dir=node_modules  
grep -r "chat_router" chatServer/ --exclude-dir=__pycache__
```

**Expected**: ✅ No references found (except in comments/docs)

#### Test 6.2: Console Error Check
- ✅ No console errors on page load
- ✅ No 404 errors for missing components
- ✅ No TypeScript compilation errors

---

### 7. **Performance Tests** 🚀
**Priority**: Low - Verify improvements

#### Test 7.1: Bundle Size Check
```bash
cd webApp && npm run build
# Check dist/ folder size before/after cleanup
```

#### Test 7.2: Load Time Verification
- ✅ Pages load without delay
- ✅ Lazy loading works for remaining components
- ✅ No unnecessary network requests

---

## 🔧 **AUTOMATED TEST COMMANDS**

### Quick Validation Script
```bash
#!/bin/bash
echo "🧪 Running Cleanup Validation Tests..."

# 1. Build tests
echo "📦 Testing builds..."
cd webApp && npm run build && echo "✅ Frontend build OK" || echo "❌ Frontend build FAILED"
cd ../chatServer && python -c "import main; print('✅ Backend import OK')" || echo "❌ Backend import FAILED"

# 2. Reference cleanup check  
echo "🔍 Checking for leftover references..."
grep -r "TaskDetailTray" webApp/src/ --exclude-dir=node_modules && echo "❌ TaskDetailTray refs found" || echo "✅ TaskDetailTray cleaned"
grep -r "chat_router" chatServer/ --exclude-dir=__pycache__ && echo "❌ chat_router refs found" || echo "✅ chat_router cleaned"

# 3. TypeScript check
echo "📝 TypeScript validation..."
cd webApp && npx tsc --noEmit && echo "✅ TypeScript OK" || echo "❌ TypeScript errors"

echo "🎉 Validation complete!"
```

### Memory Bank Validation
```bash
cd memory-bank/tools && node link-checker.js
```

---

## 📊 **SUCCESS CRITERIA**

### ✅ **MUST PASS**
- [ ] All builds succeed without errors
- [ ] Chat API endpoint works correctly  
- [ ] Task creation/editing flows work
- [ ] No broken imports or references
- [ ] No TypeScript compilation errors

### ✅ **SHOULD PASS**  
- [ ] All routes navigate correctly
- [ ] Overlay system functions properly
- [ ] No console errors during normal usage
- [ ] Performance maintained or improved

### ✅ **NICE TO HAVE**
- [ ] Bundle size reduced
- [ ] Faster load times
- [ ] Cleaner code structure

---

## 🚨 **ROLLBACK PLAN**

If critical issues found:

### Emergency Rollback
```bash
# Restore files from git
git checkout HEAD~1 -- chatServer/routers/chat_router.py
git checkout HEAD~1 -- webApp/src/components/tasks/TaskDetailTray.tsx  
git checkout HEAD~1 -- webApp/src/pages/Dashboard.tsx
git checkout HEAD~1 -- webApp/src/App.tsx
git checkout HEAD~1 -- webApp/src/components/overlays/OverlayManager.tsx

# Restart services
cd chatServer && python main.py &
cd webApp && npm run dev &
```

### Partial Rollback Options
- **API only**: Restore `chat_router.py` and update `main.py`
- **UI only**: Restore Dashboard/TaskDetailTray components
- **Routes only**: Restore Dashboard route in App.tsx

---

## 📝 **TEST EXECUTION LOG**

### Pre-Test Checklist
- [ ] Code committed to git (for rollback safety)
- [ ] Development environment ready
- [ ] Test data available
- [ ] Auth tokens configured

### Test Results
| Test Category | Status | Notes |
|---------------|--------|-------|
| Build & Compilation | ⏳ | |
| API Endpoints | ⏳ | |
| Frontend Navigation | ⏳ | |
| Task Management | ⏳ | |
| Overlay System | ⏳ | |
| Error Handling | ⏳ | |
| Performance | ⏳ | |

### Issues Found
| Issue | Severity | Status | Resolution |
|-------|----------|--------|------------|
| | | | |

---

## 🎯 **NEXT PHASE PREPARATION**

After successful testing, prepare for **Phase 2 cleanup**:
- [ ] Verify CoachPageV2 functionality complete
- [ ] Test ChatPanelV2 stability  
- [ ] Plan removal of ChatPanelV1 fallback
- [ ] Document migration completion 