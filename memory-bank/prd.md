# Product Requirements Document: Local LLM Terminal Environment

## Introduction

This document outlines the requirements for building a local, terminal-based environment for interacting with Large Language Models (LLMs), initially focusing on Gemini Pro via API. The environment will leverage local file-based storage (Markdown, YAML) for project contexts, calendar information, and general user preferences to provide structured and predictable interactions with the LLM. A key goal is to assist with project and calendar management, particularly for individuals managing multiple tasks and potentially facing challenges with traditional organizational methods (e.g., due to ADHD). The project will be developed in Python, utilizing the LangChain framework for LLM interaction to ensure future flexibility across different models.

## 1.1 Phase 1 [Complete] 

### 1.2 Goals

* **Primary Goal:** Create a functional terminal application in Python that can interact with an LLM (starting with Gemini Pro via API) by providing context loaded from local files.
* **Improve LLM Interaction:** Develop structured methods for providing context (project notes, calendar entries, personal preferences) to the LLM to achieve more predictable, relevant, and accurate responses compared to manual context provision in web interfaces.
* **Enable File-Based Context Management:** Allow users to define and manage different contexts (per project, global) using simple, human-readable local files (Markdown for free text, YAML for structured data).
* **Support Project Management Aids:** Utilize the LLM and file-based context to assist with basic project management tasks (e.g., summarizing project notes, understanding project status based on files).
* **Support Calendar/Time Management Aids:** Utilize the LLM and file-based context to assist with calendar and time management, providing capabilities relevant to challenges like time blindness or task prioritization (e.g., summarizing upcoming events, structuring daily tasks based on calendar and project needs).
* **Learn and Apply AI-Assisted Development:** Use the process of building this tool as a practical way to learn and apply best practices for developing software with the assistance of AI models.
* **Establish a Flexible Architecture:** Implement the LLM interaction layer using LangChain to facilitate potential integration with other LLMs (local or remote) in the future without significant code refactoring.
* **Prioritize Learning & Speed:** Balance the desire for robust architecture with rapid development and learning throughout the process.

## 1.3 Non-Goals

* Building a graphical user interface (GUI). The focus is purely terminal-based interaction, though the structure created should allow for the easy creation of a GUI in the future.
* Creating a full-fledged, feature-rich project management or calendar application with complex data models and relationships (like dependencies, resource allocation, etc.). The goal is LLM-assisted interaction based on user-managed text/YAML files.
* Real-time, continuous synchronization with external services like Google Calendar (initially). Calendar integration will be "on request" as a subsequent development step (Step 2).
* Achieving perfect or guaranteed predictable LLM output (acknowledging the inherent variability in LLMs), but rather *improving* predictability and reliability through structured context.

## 1.4 User Stories / Features (Initial Ideas)

* As a user, I want to define different agent configurations (prompts, tools, specific LLM params) and base context by creating directories and files within a `/config/agents/<agent_name>/` folder. Tool capabilities and their scopes (e.g., read project files, write to memory bank) should be declaratively defined in the agent's YAML using a `tools_config` structure.
* As a user, I want agents I interact with (via the `chat` command) to be able to read and write files based on the scopes defined in their `tools_config`. For example, an 'assistant' agent might only write to `/data/agents/assistant/output/`, while an 'architect' agent might read the whole project but only write to `/memory-bank/`.
* As a user, I want to define global context (e.g., personal bio, communication style, personal limitations) in files within a `data/global_context/` folder, such as `personal_bio.md` and `personal_limitations.md`. Global context should always be loaded for the active agent.
* As a user, I want to interact with different configured agents via a REPL interface (`chat` command).
* As a user, I want to ask the LLM questions or give instructions via the terminal REPL, and have the system automatically load the relevant agent context (global + agent-specific config/prompt). I want to be able to switch between agents using a command like `/agent <name>`.
* As a user, I want the LLM agent to be able to read and understand the content of its configuration files (e.g., system prompt) and potentially read files from other directories (like its data directory or the project root) using specifically configured and named tools (e.g., `read_agent_configuration_file`, `read_project_file`).
* As a user, I want to ask the LLM to help me structure my day or week based on my calendar events and project tasks defined in the files.
* As a user, I want to be able to ask the LLM to summarize the key points from a specific Markdown notes file.
* As a user, I want to easily switch between different configured agents in the terminal REPL using a command.
* As a user, I want to be able to pipe the output of one LLM interaction as input or additional context for a subsequent interaction, enabling chaining of commands or "assistant" capabilities.
* As a user, I want my API key for the LLM to be stored securely using environment variables.
* As a developer/user, I want a dedicated 'Architect' agent that can assist me in defining, refining, and grooming project backlog items, ensuring alignment with the project's established architecture, goals, and documentation standards.
*   As a developer, I want to refactor the project structure for proper Python packaging and module imports to eliminate import hacks and improve maintainability.
*   As a developer, I want to investigate and fix the failing Pytest suite to ensure code quality and enable confident refactoring.
*   As a project maintainer, I want to prepare the project for public release by scrubbing all sensitive data (like `memory-bank/` contents and chat logs) to protect privacy.
*   As a developer, I want to implement a CI/CD pipeline using GitHub Actions to automatically run Pytests on Pull Requests and block merges if tests fail, ensuring code stability.

## 5. Technical Considerations

* **Operating System:** Development and target environment is Ubuntu 24.04.
* **Programming Language:** Python 3.x.
* **LLM Interaction Framework:** LangChain will be used to interface with LLMs.
* **Initial LLM:** Gemini Pro via Google Cloud API.
* **File Formats:** Markdown (`.md`) for free text/notes. YAML (`.yaml` or `.yml`) is the preferred format for user-edited structured data (tasks, calendar events, configuration) due to readability. Support for reading JSON may be added later, particularly for ingesting data from external APIs.
* **Configuration:** Application settings will be managed via a configuration file (YAML). Sensitive information like API keys will be managed via environment variables.
* **Dependencies:** Managed via `pip` and `requirements.txt`, using a Python virtual environment (`venv`).
* **Command Line Interface:** Will be built using a Python library like `Click`.
* **Project Structure:** Modular, following the proposed structure, with clear separation of data, source code, and configuration.
* **Version Control:** Git will be used for source code management.
* **Authentication:** Google Calendar API integration (Step 2) will require implementing OAuth 2.0.

## 5a. Project Conventions and Implementation Decisions

- **Secrets:** All secrets (API keys, tokens) must be stored in `.env` only. `config/settings.yaml` is committed to version control and must not contain sensitive data.
- **Sample settings.yaml structure:**

  ```yaml
  app:
    name: Local LLM Terminal Environment
    version: 0.1.0

  llm:
    provider: gemini
    model: gemini-pro
    temperature: 0.7
    max_tokens: 2048

  config: # Renamed from 'data' to reflect static nature
    base_dir: config/
    agents_dir: config/agents/

  data: # For dynamic/runtime data
    base_dir: data/
    global_context_dir: data/global_context/
    agents_dir: data/agents/ # Agent-specific runtime data (memory, output)

  cli:
    default_command: chat # Updated default

  logging:
    level: INFO
    file: logs/app.log
  ```

- **Context Management:**
  - Global context (`data/global_context/`) is automatically loaded.
  - Agent-specific static context (system prompt, config details) is loaded from `/config/agents/<agent_name>/`.
  - Context is rendered as a structured string with Markdown headings for the LLM prompt.
  - Agents can access other files (e.g., in their `/data/agents/<agent_name>/` directory) via tools if instructed.
  - If global context files are missing, the context manager should warn but not error.
- **LLM Prompt Engineering:**
  - Prompts sent to the LLM must always include explicit section headings.
  - Each CLI command/agent can define its own prompt template as needed.
- **File Writing/Editing & Tool Sandboxing:**
  - Agents use tools (like LangChain's `FileManagementToolkit`) to interact with files.
  - Tool usage (read/write/list permissions and target directories) is defined declaratively per-tool within the agent's `tools_config` in its YAML file.
  - Each configured tool is explicitly associated with a `scope` (e.g., `AGENT_DATA`, `MEMORY_BANK`, `PROJECT_ROOT`) which determines the directory the underlying toolkit operates on, providing clear sandboxing.
  - Tool descriptions in the config should clearly state the scope and intended use (e.g., "Writes ONLY to the memory bank directory ({scope_path})").
- **Google Calendar Integration:**
  - Calendar sync will overwrite the local YAML after user confirmation.
  - No fixed YAML schema for events yet; to be defined during implementation.
- **Testing:**
  - Tests should mirror the `src/` directory structure under `tests/`.
  - `pytest` is recommended for its simplicity and popularity.
- **Piping/Chaining:**
  - All CLI commands should support stdin piping.
  - If both an argument and stdin are provided, the argument takes precedence, with a warning.
- **Error Handling and Logging:**
  - Errors should be logged to a file and printed to stderr.
  - Use Python's built-in `logging` module with a format like:
    `[%(asctime)s] %(levelname)s in %(module)s: %(message)s`

## 6. Proposed Project Structure (Conceptual)
your_llm_env/
├── config/                # Static configuration files
│   ├── settings.yaml      # Application settings
│   └── agents/            # Agent configurations
│       └── <agent_name>/
│           ├── agent_config.yaml # Agent behavior, tools
│           └── system_prompt.md  # Base instructions
├── data/                  # Dynamic/runtime data
│   ├── global_context/    # Global context files (e.g., personal_bio.md)
│   └── agents/            # Agent-specific runtime data
│       └── <agent_name>/
│           ├── memory/      # Conversation history (e.g., chat_history.json)
│           ├── output/      # Files written by agent tools
│           └── session_summary.md # Summary of last session
├── src/                   # Python source code
│   ├── core/              # Core functionalities
│   │   ├── agent_loader.py # Loads agent config (including tools_config) and constructs AgentExecutor
│   │   ├── llm_interface.py # Handles base communication with LLM APIs (Potentially refactored/simplified)
│   │   ├── file_parser.py   # Reads/writes different file types
│   │   └── context_manager.py # Gathers global context
│   ├── cli/               # Command Line Interface handling
│   │   └── main.py          # Entry point for the CLI (`chat` command)
│   └── utils/             # Helper functions
│       ├── config_loader.py # Handles loading configuration
│       ├── path_helpers.py  # Standardizes path construction
│       └── chat_helpers.py  # REPL loop helpers (memory, commands, summary)
├── scripts/               # Utility scripts (potentially build scripts)
├── tests/                 # Your tests
├── .gitignore             # Specifies intentionally untracked files
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
└── LICENSE              # Project license


## 7. Success Metrics (Initial)

* The application can successfully load context from specified Markdown and YAML files. [COMPLETE]
* The application can successfully send prompts and loaded context to the LLM via LangChain and receive a response. [COMPLETE]
* Users can define different agent configurations in the `/config/agents/` directory and switch between them in the `chat` REPL using the `/agent <name>` command. [COMPLETE]
* Basic interactions within the `chat` REPL are functional, taking into account global context and the loaded agent's specific configuration/prompt. [COMPLETE]
* The application structure supports piping output from one interaction as input for the next. [INCOMPLETE]
* The code is organized according to the modular structure, making it reasonably easy to understand and extend for future features like Calendar integration (Step 2). [COMPLETE]
* Effective use of AI assistance throughout the development process is achieved, speeding up implementation and helping navigate unfamiliar patterns. [COMPLETE]