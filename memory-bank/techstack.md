# Tech Stack

This document summarizes the key technologies and tools selected for the Local LLM Terminal Environment project and its web interface (Clarity).

## 1. Core Technologies

### CLI Application
* **Programming Language:** Python 3.x
* **LLM Interaction Framework:** LangChain
* **Initial LLM Provider:** Google Cloud (for Gemini Pro API)

### Web Application (Clarity)
* **Frontend Framework:** React 18+
* **Styling:** TailwindCSS
* **State Management:** React Query + Zustand
* **Backend Services:** Supabase
* **API Layer:** Serverless Functions (Vercel/Cloudflare)
* **LLM Integration:** OpenRouter-compatible API layer

## 2. Libraries & Dependencies

### CLI Application
* **LLM API Client:** Handled by LangChain
* **Command Line Interface (CLI):** Click
* **Structured Data Handling:** PyYAML
* **Configuration Management:** PyYAML, python-dotenv
* **File Parsing:** Standard Python I/O, markdown library

### Web Application
* **UI Components:** 
  - Headless UI (accessibility)
  - Radix UI (primitives)
  - Framer Motion (animations)
* **Data Management:**
  - React Query (server state)
  - Zustand (client state)
  - Supabase Client
* **Form Handling:** React Hook Form + Zod
* **Date/Time:** date-fns
* **Notifications:** react-hot-toast
* **Icons:** Lucide Icons
* **Calendar Integration:** Google Calendar API
* **Document Integration:** Google Docs API

## 3. File Formats

* **Notes & Free Text:** Markdown (.md)
* **Structured Data:** 
  - YAML (.yaml, .yml) - Primary config format
  - JSON - API and state management
* **Environment:** .env files for local development

## 4. Development Tools & Environment

* **Operating System:** Ubuntu 24.04 LTS
* **Version Control:** Git
* **Package Management:**
  - Python: pip + requirements.txt
  - Node: pnpm + pnpm-workspace.yaml
* **Code Editor:** Cursor
* **Development Server:** Vite
* **Testing:**
  - Python: pytest
  - Frontend: Vitest + Testing Library
* **Linting/Formatting:**
  - Python: black, flake8
  - Frontend: ESLint, Prettier
* **CI/CD:** GitHub Actions

## 5. Project Structure

```
/
├── cli/                    # CLI Application
│   ├── config/            # Static configuration
│   ├── data/              # Dynamic runtime data
│   ├── src/               # Python source code
│   └── tests/             # CLI tests
│
├── web/                    # Web Application
│   ├── apps/
│   │   ├── web/          # Main web application
│   │   └── api/          # Serverless API functions
│   ├── packages/          # Shared packages
│   │   ├── ui/           # Shared UI components
│   │   ├── config/       # Shared configuration
│   │   └── types/        # Shared TypeScript types
│   └── tests/            # Frontend tests
│
└── docs/                   # Project documentation
```

## 6. Infrastructure & Services

### Development
* **Local Development:**
  - Docker Compose for local services
  - Vite dev server with HMR
  - Supabase local development

### Production
* **Hosting:**
  - Frontend: Vercel/Cloudflare Pages
  - API: Vercel/Cloudflare Workers
  - Database: Supabase
* **Authentication:** Supabase Auth
* **Storage:** Supabase Storage
* **Monitoring:** Sentry
* **Analytics:** PostHog (opt-in)

## 7. Security & Privacy

* **Authentication:** OAuth 2.0 (Google, Apple)
* **Data Encryption:** 
  - At rest: Supabase encryption
  - In transit: TLS
* **Access Control:** Row-level security in Supabase
* **Privacy:** 
  - User data export
  - Data deletion
  - Analytics opt-in