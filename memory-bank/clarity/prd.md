## **Product Requirements Document (PRD)**

**Project Name:** _[TBD]_ (Placeholder: “Clarity”)  
**Version:** 0.1 MVP  
**Prepared by:** Tim O'Brien  
**Date:** [Today’s Date]

---

### **1. Overview**

**Purpose:**  
This product is a cross-platform planning and executive function assistant built for people with ADHD. The MVP will focus on daily task planning with AI-powered coaching and distraction management features. It is designed to reduce friction around task initiation, time blindness, and low motivation by combining evidence-based strategies with adaptive AI nudges.

**Target Users:**
- Adults with ADHD (college students + working professionals)    
- Primary needs: executive function support, emotional regulation, and adaptive task planning

---

### **2. Goals & Non-Goals**

**Goals:**
- Build an MVP with core planning and habit-forming functionality
- Implement contextual & conversational AI to support executive function
- Offer seamless, privacy-respecting integration with Google Calendar & Docs
- Design for simplicity, low friction, and personalization
- Prioritize web app for initial release, mobile-friendly where possible

**Non-Goals (MVP):**
- Native Android or iOS apps (deferred)
- Deep analytics or reporting
- Rich community/social features
- Third-party wearable integrations

---

### **3. Key Features (MVP)**

#### **A. Task Planning**
- Create/edit tasks with optional due date, time, and category
- Daily planning interface (“Today” view)
- Color-coded priority tagging or Eisenhower Matrix layout
- Pomodoro timer with visual countdown
- “Focus View” showing only the active task
#### **B. AI Coach (Hybrid Interface)**
- Daily conversational check-in (chat UI)
- Smart nudge system (e.g., “Want help starting your 10AM writing task?”)
- Personalized tone/feedback preferences (e.g., “cheerful,” “direct,” “gentle”)
- Contextual prompts based on user history and timing
#### **C. Motivation & Feedback**
- Streaks, badges, or light gamification for task initiation and completion
- Small, customizable in-app rewards or “treat yourself” triggers
- Immediate feedback via notifications, animations, or celebratory UI moments

#### **D. Distraction Management**
- Focus mode (optional website blocker, Do Not Disturb sync)
- Brain-dump pad (text or voice input) for intrusive thoughts
- Optional mindfulness check-ins (preloaded or external integrations)

#### **E. Integrations**
- **Google Calendar Sync** (read/write events)
- **Google Docs Integration** (attach/jump to docs per task)
- **OAuth sign-in** via Google and Apple

---

### **4. Architecture & Tech Stack (Proposed)**

**Frontend:**
- Web-first SPA using React (or Svelte if preferred simplicity)
- TailwindCSS for ADHD-friendly, clean UI
- Mobile-optimized design with eventual PWA support

**Backend:**
- Supabase (or Firebase) for auth, storage, real-time data
- Serverless or small Node/Python API layer (e.g., Vercel, Render, or Cloudflare Workers)
- AI model routing abstracted via API layer (OpenRouter-compatible)

**Data Model Principles:**
- All user data is encrypted and user-accessible
- Tasks, preferences, coaching interactions stored in user-owned cloud DB
- Logging and metrics opt-in and anonymized

---

### **5. Success Criteria (MVP)**

- Users can complete a daily planning session and receive coaching prompts
- AI successfully initiates nudges at the right time (based on schedule, activity)
- Feedback system (points, badges, etc.) is working and positively reinforcing
- Focus mode visibly reduces distractions during task sessions
- Google Calendar sync and Docs integration work reliably in both directions
- App loads quickly and works on desktop + mobile browsers

---

### **6. Risks & Considerations**

- **AI model drift or poor performance**: Include eval framework to test prompts across models
- **Scope creep**: Keep AI features shallow but useful at launch
- **Privacy**: Clear user control over data export and deletion
- **Accessibility**: Commit to WCAG 2.1 compliance where feasible
- **Retention**: Build meaningful onboarding and reward systems to encourage habit formation

---

### **7. Future Considerations**

- Full iOS native app (with push notifications)
- Integration with Apple Health, RescueTime, or wearable data
- Community coaching or accountability partner sharing
- Workspace AI agents (e.g. Slack plugin or Chrome extension)