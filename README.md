# llm-agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive platform for developing and interacting with Large Language Models (LLMs). It features a web-based user interface (`webApp`) for task management and AI coaching, a FastAPI backend (`chatServer`) to manage agent interactions, and a core Python library with a command-line interface (`CLI`) for direct agent development and use. Agents are built using LangChain and can leverage Google's Gemini models.

## Project Overview

The project is structured into three main components:

*   **`webApp/`**: A React-based frontend application providing a rich user interface for task management, AI-driven coaching, and interaction with LLM agents. (See `webApp/README.md` for details)
*   **`chatServer/`**: A Python FastAPI backend that serves the `webApp`, manages chat sessions, orchestrates Langchain agent execution, and will handle agent-driven actions. (See `chatServer/README.md` for details)
*   **`src/`**: The core Python library containing the LLM agent logic, CLI tools, context management, and agent configuration loading. This is used by both the `chatServer` and the standalone CLI.

## Features

### Web Application (`webApp`)
*   **Task Management:** Create, view, and manage daily tasks.
*   **AI Coaching:** Interact with an AI coach via a chat interface.
*   **Centralized UI:** Modern interface built with React, Radix UI, and Tailwind CSS.
*   **Real-time Updates:** Leverages React Query for data synchronization.

### Core Agent & CLI (`src/` & command line)
*   **Configurable Agents:** Define different agent personalities, prompts, tools, and context sources via YAML and Markdown files in `config/agents/`.
*   **Context Integration:** Automatically loads context from global (`data/global_context/`) and agent-specific directories (`config/agents/<name>/`, `data/agents/<name>/`).
*   **Interactive Chat (REPL):** Engage in conversations with agents using the `chat` command, which supports command history.
*   **Persistent Memory:** Chat history for each agent is saved automatically (`data/agents/<name>/memory/chat_history.json`) and loaded when you restart a chat session with that agent.
*   **Agent Switching:** Switch between different configured agents within a chat session using the `/agent <name>` command.
*   **Tool Use:** Agents can be configured to use tools (e.g., file system access scoped to specific directories).
*   **Simple Single-Shot Queries:** Use the `ask` command for quick, non-conversational queries.
*   **Configurable Logging:** Control output verbosity with `--log-level` and `--verbose` flags.

## Quick Start (Web Application + Chat Server)

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd llm-agent
    ```
2.  **Setup Environment Variables:**
    *   **Root `.env`:** Create a `.env` file in the project root. This is used by `chatServer` and the Python CLI.
        ```dotenv
        # For chatServer and Python CLI
        LLM_AGENT_SRC_PATH=src
        # Add your Google API Key if agents need it (e.g., for Gemini)
        # GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY" 
        # Add any other API keys your agents might require
        # OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
        ```
    *   **`webApp/.env`:** Create a `.env` file in the `webApp/` directory. This is used by the React frontend.
        ```dotenv
        # For webApp (React frontend)
        VITE_SUPABASE_URL="YOUR_SUPABASE_URL"
        VITE_SUPABASE_ANON_KEY="YOUR_SUPABASE_ANON_KEY"
        ```
3.  **Install Dependencies & Run:**
    *   Ensure you have Python (3.10+) and Node.js (with pnpm) installed.
    *   Activate your Python virtual environment (e.g., `source .venv/bin/activate`).
    *   From the project root:
        ```bash
        pip install -r requirements.txt # Installs Python CLI dependencies
        pip install -r chatServer/requirements.txt # Installs chatServer dependencies
        pnpm install # Installs webApp dependencies and root workspace tools
        pnpm dev # Starts webApp and chatServer concurrently
        ```
    *   The `webApp` will be available at `http://localhost:5173` and the `chatServer` at `http://localhost:3001`.

## Setup (Detailed)

### 1. Python Environment & Core CLI

This setup is for the core Python library (`src/`) and its command-line interface.

1.  **Clone the repository (if not done):**
    ```bash
    git clone <repository_url>\n    cd llm-agent
    ```

2.  **Create a Python virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate 
    # On Windows use .venv\\Scripts\\activate
    ```

3.  **Install core Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install the project in editable mode (for `src`):**
    This step makes the `src` module importable.
    ```bash
    pip install -e .
    ```

5.  **Configure Root Environment Variables:**
    *   Create a `.env` file in the project root directory (if not done in Quick Start).
    *   Add `LLM_AGENT_SRC_PATH=src`.
    *   Add your Google API key if using Gemini models: `GOOGLE_API_KEY="YOUR_API_KEY_HERE"`.
    *   You can obtain a Google API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    *   Add any other API keys your agents might require.

### 2. Chat Server (`chatServer/`)

This setup is for the FastAPI backend.

1.  **Python Environment:** Ensure you have a Python environment activated (can be the same as for the CLI).
2.  **Install `chatServer` dependencies:**
    ```bash
    pip install -r chatServer/requirements.txt
    ```
3.  **Environment Variables:** Ensure the root `.env` file is configured as `chatServer` uses it (e.g., for `LLM_AGENT_SRC_PATH` and potentially agent API keys).

### 3. Web Application (`webApp/`)

This setup is for the React frontend.

1.  **Node.js and pnpm:** Ensure you have Node.js (LTS version recommended) and pnpm installed.
2.  **Install `webApp` dependencies:** From the project root:
    ```bash
    pnpm install 
    # This installs dependencies for webApp and any root workspace tools.
    # Alternatively, from the webApp/ directory: pnpm install
    ```
3.  **Configure `webApp` Environment Variables:**
    *   Create a `.env` file in the `webApp/` directory (if not done in Quick Start).
    *   Add your Supabase project URL and Anon key:
        ```dotenv
        VITE_SUPABASE_URL="YOUR_SUPABASE_URL"
        VITE_SUPABASE_ANON_KEY="YOUR_SUPABASE_ANON_KEY"
        ```

### 4. (Optional) Global Settings

*   Review and modify `config/settings.yaml` to change default model names, directory paths for the Python CLI, etc.

## Running the Applications

### 1. Full Stack (Recommended for Web UI)
From the project root, after completing all setup steps:
```bash
pnpm dev
```
This will start:
*   The `webApp` (React frontend) on `http://localhost:5173` (by default).
*   The `chatServer` (FastAPI backend) on `http://localhost:3001` (by default).

### 2. Running `chatServer` Standalone
From the project root (ensure Python environment is active and root `.env` is set):
```bash
python chatServer/main.py
```

### 3. Running `webApp` Standalone
From the `webApp/` directory (ensure `webApp/.env` is set):
```bash
pnpm dev
```
Note: The `webApp` expects the `chatServer` to be running (default on `http://localhost:3001/api`) for chat functionality.

### 4. Using the Python CLI 

The primary entry point is the `src.cli.main` module. This is for direct interaction with agents without the web UI.

#### Interactive Chat (`chat`)

This is the main way to interact with agents conversationally via the CLI.

```bash
python -m src.cli.main chat [OPTIONS]
```

**Options:**
*   `--agent <name>` or `-a <name>`: Specify the agent to start the chat with (defaults to `assistant` if not provided).
*   `--log-level <level>`: Set logging level (`debug`, `info`, `warning`, `error`, `critical`). Default is `error`.
*   `--verbose` or `-v`: Enable verbose logging (sets level to `debug`, overrides `--log-level`).

**Example:**
```bash
python -m src.cli.main chat -a test_agent --verbose 
```

**In-Chat Commands:**
*   `/exit`: Quit the chat session. Chat history will be saved.
*   `/agent <name>`: Switch to a different configured agent. The history of the previous agent will be saved before switching.

#### Single Question (`ask`)

For non-conversational queries where you provide context via an agent configuration.

```bash
python -m src.cli.main ask <QUERY> [OPTIONS]
```

**Arguments:**
*   `<QUERY>`: The question you want to ask the LLM (required).

**Options:**
*   `--agent <name>` or `-a <name>`: Specify the agent whose context should be loaded and provided to the LLM.
*   `--log-level <level>`: Set logging level.
*   `--verbose` or `-v`: Enable verbose logging.

**Example:**
```bash
python -m src.cli.main ask "What is the secret codeword mentioned in your context?" -a test_agent
```

## Agent Configuration

Agents are defined by creating a subdirectory under `config/agents/`. This configuration is used by both the `chatServer` (for the web UI) and the Python CLI.

*   **`config/agents/<agent_name>/`**: Contains configuration and static context files for an agent.
    *   `agent_meta.yaml`: Defines agent parameters (description, tools, model settings, system prompt file).
    *   `system_prompt.md`: The main instruction prompt for the agent.
    *   Other `.md` or `.yaml` files: Additional static context loaded automatically.
*   **`data/agents/<agent_name>/`**: Contains dynamic data generated by or for the agent.
    *   `agent_data_context.md`: A specific file automatically loaded into the agent\'s context.
    *   `memory/chat_history.json`: Saved conversation history (created automatically by CLI chat and `chatServer`).
    *   Other files/directories created by agent tools (e.g., via `file_management` tool).
*   **`data/global_context/`**: Files here are loaded as context for *all* agents.

See the `config/agents/test_agent/` directory for an example configuration.

## Development

The project consists of distinct parts with their own development considerations:

*   **`webApp/` (React Frontend):** Developed using TypeScript, React, Vite, Radix UI, and Tailwind CSS. See `webApp/README.md` for more details.
*   **`chatServer/` (FastAPI Backend):** Developed using Python and FastAPI. See `chatServer/README.md` for more details.
*   **`src/` (Core Python Library & CLI):** Standard Python development.
    *   Dependencies are managed in `requirements.txt` (for core/CLI) and `chatServer/requirements.txt` (for server).
    *   Testing: Uses `pytest`. Run tests with `pytest` from the project root for the core library.
*   **Contribution:** Please follow standard practices (fork, feature branch, pull request).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
