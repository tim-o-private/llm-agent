# Deployment Strategy for Clarity Application

This document outlines the deployment strategy for the Clarity application, encompassing the `webApp` (React frontend) and the `chatServer` (FastAPI Python backend).

## 1. Guiding Principles

*   **Single Platform Preference:** Aim to host both frontend and backend components on a single, cohesive platform where feasible to simplify management and potentially reduce costs.
*   **Cost-Effectiveness:** Prioritize platforms that offer low-cost options for small instances and clear pricing, allowing for predictable operational expenses.
*   **Avoid Serverless for Backend:** For the `chatServer` (FastAPI), prefer long-running containerized services over serverless functions (e.g., AWS Lambda, Google Cloud Functions) to ensure predictable performance and avoid potential runaway costs associated with per-request billing for an always-on or stateful service.
*   **Containerization:** Utilize Docker for packaging both applications to ensure consistency across development and production environments.
*   **Database:** Continue using Supabase for PostgreSQL database and authentication services. The deployment strategy will focus on connecting our hosted applications to Supabase.

## 2. Chosen Cloud Provider: Fly.io

**Rationale:**
*   Offers **cost-effective options for small instances** suitable for running both a React frontend and a Python FastAPI backend with minimal expense. While not offering a broad persistent free tier for applications, their pricing for small VMs is competitive and transparent.
*   Natively supports Docker container deployment.
*   Provides a good balance of control and simplicity for full-stack applications.
*   Well-suited for Python/FastAPI applications.
*   Applications run as persistent processes, aligning with the preference against a serverless model for the backend.
*   Provides a clear path for scaling if needed, and migration to other platforms is feasible if cost considerations change significantly.

## 3. Application Deployment Details

### 3.1. `webApp` (React Frontend)

*   **Packaging:** Docker container.
    *   **Dockerfile:** A multi-stage Dockerfile will be used.
        1.  Stage 1: Use a Node.js base image to build the React application (`npm run build` or `pnpm build`).
        2.  Stage 2: Use a lightweight web server image (e.g., Nginx or a minimal Node.js static server like `serve`) to serve the static files generated in `/dist` (or `/build`) from Stage 1.
*   **Hosting on Fly.io:**
    *   Deploy as a Fly app.
    *   Configure `fly.toml` to serve on HTTP/HTTPS (Fly handles SSL).
    *   Environment variables (e.g., `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_CHAT_SERVER_URL`) will be set as Fly secrets.
*   **Domain:** Use a `fly.dev` subdomain initially, or configure a custom domain later.

### 3.2. `chatServer` (FastAPI Python Backend)

*   **Packaging:** Docker container.
    *   **Dockerfile:**
        1.  Use a Python base image (e.g., `python:3.11-slim`).
        2.  Copy `requirements.txt` and install dependencies.
        3.  Copy the `chatServer` application code.
        4.  Expose the port Uvicorn will run on (e.g., 8000 or 3001).
        5.  Set the `CMD` to run Uvicorn (e.g., `uvicorn main:app --host 0.0.0.0 --port 8000`).
*   **Hosting on Fly.io:**
    *   Deploy as a separate Fly app from the `webApp`.
    *   Configure `fly.toml` for the Python application, including port mapping and health checks.
    *   Environment variables (e.g., `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `LLM_AGENT_SRC_PATH`, `OPENAI_API_KEY` if used by agent) will be set as Fly secrets.
*   **Communication:**
    *   The `webApp` will communicate with the `chatServer` via its public `fly.dev` URL.

## 4. Supabase Environment Management

*   **Development:** Use a local Supabase instance (via Supabase CLI `supabase start`) or a dedicated development project on Supabase Cloud.
*   **Staging (Optional but Recommended):** A separate Supabase Cloud project for staging.
*   **Production:** A dedicated Supabase Cloud project for production.
*   **API Keys & URLs:**
    *   Frontend (`webApp`) will use the public `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
    *   Backend (`chatServer`), if it needs to interact with Supabase directly, will use the `SUPABASE_URL` and a `SUPABASE_SERVICE_ROLE_KEY`. These will be configured as secrets in Fly.io.

## 5. CI/CD (Continuous Integration / Continuous Deployment) - Future Enhancement

*   **Initial Phase (Manual):** Deployments will initially be manual using the `flyctl deploy` command from a local machine after changes are pushed to the main Git branch.
*   **Future CI/CD:**
    *   Use GitHub Actions (or similar).
    *   **On push to `main` branch (or specific release branches):**
        1.  Build Docker images for `webApp` and `chatServer`.
        2.  Deploy to Fly.io using `flyctl deploy` with an API token.
    *   Automated tests should be run as part of the CI pipeline before deployment.

## 6. Environment Variables & Secrets Management

*   **Supabase Keys:** As described in section 4.
*   **Other API Keys:** Any other third-party API keys used by `chatServer` will be stored as Fly secrets.
*   **Frontend Configuration:** Public URLs (like the `chatServer` URL) can be passed to the `webApp` as build-time or run-time environment variables, managed as Fly secrets.

## 7. Monitoring & Logging (Basic)

*   **Fly.io Logs:** Utilize `flyctl logs` to monitor application logs.
*   **Supabase Logs:** Use the logging features within the Supabase dashboard.

## 8. Cost Management on Fly.io

*   **Machine Size:** Start with the smallest available machine types (e.g., `shared-cpu-1x` with 256MB or 512MB RAM) for both apps to minimize costs.
*   **Scaling:** Configure apps to run a single instance initially. Fly.io allows scaling, but monitor costs if scaling up. Some configurations might allow scaling to zero, which can further save costs if traffic is intermittent (check Fly.io docs for current capabilities).
*   **Volume Sizes:** Use the smallest persistent disk volumes if needed (e.g., 1GB).
*   **Bandwidth & Requests:** Be mindful of Fly.io's pricing for bandwidth and egress.
*   **Regular Review:** Periodically review the Fly.io dashboard for resource consumption and associated costs.

## Environment Variables and Secrets

### `chatServer`
*   `LLM_AGENT_SRC_PATH`: Points to the `src/` directory for core agent logic.
*   `RUNNING_IN_DOCKER`: Set to `"true"` in the Dockerfile to adjust `sys.path` and `.env` loading.
*   `SUPABASE_SERVICE_ROLE_KEY`: (If `chatServer` needs to interact with Supabase directly with admin privileges) - To be set as a Fly.io secret.
*   `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.: LLM provider API keys, set as Fly.io secrets.

### `webApp`
*   `VITE_SUPABASE_URL`: Public URL for your Supabase project.
*   `VITE_SUPABASE_ANON_KEY`: Public anon key for your Supabase project.
*   **`VITE_API_BASE_URL`**: The base URL for the `chatServer` API. This is crucial for production.
    *   In development, this is not strictly needed if API calls from `webApp` are consistently made to relative paths like `/api/...`, which are then handled by Vite's dev proxy.
    *   In production, this will be set to the deployed `chatServer` URL (e.g., `https://clarity-chatserver.fly.dev`).

These are passed as build arguments to `docker build` from Fly.io secrets:
```toml
# webApp/fly.toml
[build.args]
  VITE_SUPABASE_URL = "$VITE_SUPABASE_URL"
  VITE_SUPABASE_ANON_KEY = "$VITE_SUPABASE_ANON_KEY"
  VITE_API_BASE_URL = "$VITE_API_BASE_URL" # Ensure this secret is set in Fly.io
```

## Next Steps / Future Considerations
*   **CI/CD Pipeline:** Implement GitHub Actions for automated builds and deployments to Fly.io on pushes to `main` or specific tags.
*   **Staging Environment:** Set up a separate Fly.io app or organization for a staging/preview environment.
*   **Custom Domains:** Configure custom domains for both `clarity-webapp` and `clarity-chatserver`.
*   **Database Migrations:** Formalize a process for running Supabase database migrations, potentially integrated into the CI/CD pipeline or managed via `flyctl` proxy to Supabase.
*   **Monitoring and Logging:** Integrate more robust logging and monitoring solutions for both applications on Fly.io.

## Frontend API Configuration

The `webApp` (React/Vite frontend) needs to communicate with the `chatServer` (FastAPI backend) for API requests. This is handled differently in development and production environments:

### Development (`vite dev`)

*   **Vite Dev Server Proxy:** The `webApp/vite.config.ts` file is configured with a proxy for paths starting with `/api`.
    ```typescript
    // webApp/vite.config.ts excerpt
    server: {
      port: 3000, // webApp dev server port
      proxy: {
        '/api': {
          target: 'http://localhost:3001', // chatServer local dev URL
          changeOrigin: true,
          // rewrite: (path) => path.replace(/^\\/api/, ''), // Optional: if chatServer doesn't expect /api prefix
        },
      },
    },
    ```
*   **API Calls in Frontend Code:** Frontend code makes API calls to relative paths like `/api/chat` or `/api/agent/process-notes`. The Vite dev server automatically forwards these requests to `http://localhost:3001` (where `chatServer` is expected to be running locally).
*   **`VITE_API_BASE_URL` in Development:** While not strictly necessary for proxied calls, if direct absolute URLs are ever constructed in dev, `VITE_API_BASE_URL` could be set to `http://localhost:3001` in `webApp/.env` or `webApp/.env.development`. However, relying on the proxy for `/api/*` calls is typical.

### Production (Deployed on Fly.io)

*   **No Dev Proxy:** The Vite dev server and its proxy are not used in a production build. The `webApp` is served as static files (e.g., by Nginx).
*   **`VITE_API_BASE_URL` Environment Variable:** The `webApp` must be built with the `VITE_API_BASE_URL` environment variable set to the public URL of the deployed `chatServer`.
    *   Example: `VITE_API_BASE_URL="https://clarity-chatserver.fly.dev"`
*   **Passing at Build Time:** This variable is passed as a build argument during the Docker build process for `webApp`, sourced from Fly.io secrets.
    ```dockerfile
    # webApp/Dockerfile excerpt
    ARG VITE_API_BASE_URL
    ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
    # ... other ARGs and ENVs for Supabase keys ...
    RUN npm run build
    ```
    And configured in `webApp/fly.toml`:
    ```toml
    # webApp/fly.toml excerpt
    [build.args]
      VITE_SUPABASE_URL = "$VITE_SUPABASE_URL"
      VITE_SUPABASE_ANON_KEY = "$VITE_SUPABASE_ANON_KEY"
      VITE_API_BASE_URL = "$VITE_API_BASE_URL" # Secret must be set in Fly.io
    ```
*   **API Calls in Frontend Code:** Frontend JavaScript code must use this `VITE_API_BASE_URL` to construct the full URL for API requests.
    *   Example: `const apiUrl = \`\${import.meta.env.VITE_API_BASE_URL}/api/chat\`; fetch(apiUrl);`
    *   It's common to have a utility function or an Axios/fetch instance configured with this base URL.

This setup ensures that the `webApp` can seamlessly switch between targeting the local `chatServer` during development and the deployed `chatServer` in production. 