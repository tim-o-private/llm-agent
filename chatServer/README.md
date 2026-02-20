# Clarity Chat Server (`chatServer/`)

This directory contains the FastAPI Python backend server responsible for handling chat interactions and agent-based logic for the Clarity application.

## 1. Purpose

The Chat Server:
-   Provides API endpoints for the `webApp` frontend to send chat messages.
-   Manages and interacts with Langchain agents.
-   Loads agent configurations and integrates with the core agent logic from the project's `src/` directory.
-   (Future) Will handle agent-initiated actions and Supabase interactions.

## 2. Setup and Running

### Prerequisites

-   Python 3.10+
-   A Python virtual environment (e.g., `.venv` at the project root) is recommended.
-   Project root `.env` file configured with `LLM_AGENT_SRC_PATH=src` (and any other API keys your agents might need, e.g., `OPENAI_API_KEY`).

### Installation

1.  Ensure your Python virtual environment is activated.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Server (for Local Development)

1.  Ensure your Python virtual environment is activated.
2.  Ensure the project root `.env` file is correctly set up.
3.  From the **project root directory** (`llm-agent/`), run:
    ```bash
    python -m chatServer.main
    ```
4.  The server will start on `http://localhost:3001` by default.

Alternatively, if you have the root `package.json` set up with the `concurrently` script, you can run `pnpm dev` from the project root (after activating your Python environment) to start both the `chatServer` and `webApp`.

## 3. API Endpoints

### Current Endpoints

-   **`POST /api/chat`**
    -   **Purpose:** Handles incoming chat messages from a user to a specific agent.
    -   **Request Body (JSON):**
        ```json
        {
          "user_id": "string",    // Unique identifier for the user
          "agent_id": "string",   // Identifier for the agent to interact with
          "message": "string"     // The user's message
        }
        ```
    -   **Response Body (JSON):**
        ```json
        {
          "reply": "string"       // The agent's reply
        }
        ```
    -   **Description:** This endpoint loads or retrieves a cached agent executor for the given `user_id` and `agent_id`. It then passes the user's message to the agent and returns the agent's textual reply. It manages conversation memory for each user/agent pair.

### Future Endpoints (Planned under Phase 0.6, Step 3 - Currently On Hold)

-   `/api/agent/process-notes`
-   `/api/agent/create-tasks-from-chat`
-   Endpoints for agent-initiated UI updates (potentially via WebSockets or Server-Sent Events).

## 4. Key Technologies

-   Python
-   FastAPI
-   Uvicorn (ASGI server)
-   Langchain (for agent creation and management)
-   `python-dotenv` (for environment variable management)

## 5. Project Structure (`chatServer/`)

-   `main.py`: Main FastAPI application file, defines endpoints, loads agents.
-   `requirements.txt`: Python dependencies.
-   (No `src/` directory within `chatServer/` currently; core agent logic is in project root `src/` and accessed via `LLM_AGENT_SRC_PATH`).

## 6. Configuration

-   Primary configuration for agent paths is via `LLM_AGENT_SRC_PATH` in the project root `.env` file.
-   Agent configurations themselves (prompts, models, tools) are loaded via `ConfigLoader` from the main project's `config/` directory (typically `config/agents/<agent_id>/`). 