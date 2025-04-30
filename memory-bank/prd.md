# Product Requirements Document: Local LLM Terminal Environment

## 1. Introduction

This document outlines the requirements for building a local, terminal-based environment for interacting with Large Language Models (LLMs), initially focusing on Gemini Pro via API. The environment will leverage local file-based storage (Markdown, YAML) for project contexts, calendar information, and general user preferences to provide structured and predictable interactions with the LLM. A key goal is to assist with project and calendar management, particularly for individuals managing multiple tasks and potentially facing challenges with traditional organizational methods (e.g., due to ADHD). The project will be developed in Python, utilizing the LangChain framework for LLM interaction to ensure future flexibility across different models.

## 2. Goals

* **Primary Goal:** Create a functional terminal application in Python that can interact with an LLM (starting with Gemini Pro via API) by providing context loaded from local files.
* **Improve LLM Interaction:** Develop structured methods for providing context (project notes, calendar entries, personal preferences) to the LLM to achieve more predictable, relevant, and accurate responses compared to manual context provision in web interfaces.
* **Enable File-Based Context Management:** Allow users to define and manage different contexts (per project, global) using simple, human-readable local files (Markdown for free text, YAML for structured data).
* **Support Project Management Aids:** Utilize the LLM and file-based context to assist with basic project management tasks (e.g., summarizing project notes, understanding project status based on files).
* **Support Calendar/Time Management Aids:** Utilize the LLM and file-based context to assist with calendar and time management, providing capabilities relevant to challenges like time blindness or task prioritization (e.g., summarizing upcoming events, structuring daily tasks based on calendar and project needs).
* **Learn and Apply AI-Assisted Development:** Use the process of building this tool as a practical way to learn and apply best practices for developing software with the assistance of AI models.
* **Establish a Flexible Architecture:** Implement the LLM interaction layer using LangChain to facilitate potential integration with other LLMs (local or remote) in the future without significant code refactoring.
* **Prioritize Learning & Speed:** Balance the desire for robust architecture with rapid development and learning throughout the process.

## 3. Non-Goals

* Building a graphical user interface (GUI). The focus is purely terminal-based interaction, though the structure created should allow for the easy creation of a GUI in the future.
* Creating a full-fledged, feature-rich project management or calendar application with complex data models and relationships (like dependencies, resource allocation, etc.). The goal is LLM-assisted interaction based on user-managed text/YAML files.
* Real-time, continuous synchronization with external services like Google Calendar (initially). Calendar integration will be "on request" as a subsequent development step (Step 2).
* Achieving perfect or guaranteed predictable LLM output (acknowledging the inherent variability in LLMs), but rather *improving* predictability and reliability through structured context.

## 4. User Stories / Features (Initial Ideas)

* As a user, I want to define different configuration and agent contexts by creating directories and files (Markdown notes, YAML tasks) within a `config/` folder. Contents of this folder should be read only to agents.
* As a user, I want agents I create to be able to read and write to files within a `data/` folder. This is so that they can update their own context as needed.
* As a user, I want to define global context (e.g., personal bio, communication style, personal limitations) in files within a `data/global_context/` folder, such as `personal_bio.md` and `personal_limitations.md`.
* As a user, I want to interact with a global assistant able to understand and interact with different project contexts depending on the task.
* As a user, I want to ask the LLM questions or give instructions via the terminal, and have the system automatically load the relevant project context based on the current working directory by default, with the option to specify a different project context via a command-line argument. Global context should always be loaded.
* As a user, I want the LLM to be able to read and understand the content of my project notes (Markdown) and structured task lists (YAML) when I interact with it about a specific project.
* As a user, I want the LLM to be able to update project files on request.
* As a user, leveraging the `personal_limitations.md` context, I want the LLM to understand potential challenges I face (like time blindness) and proactively suggest tasks or considerations that might be incomplete or overlooked.
* As a user, I want the application to retrieve calendar data from Google Calendar on request (as a Step 2 feature) and store it locally in a structured format (preferably YAML) that the LLM can ingest.
* As a user, I want to be able to ask the LLM to help me structure my day or week based on my calendar events and project tasks defined in the files.
* As a user, I want to be able to ask the LLM to summarize the key points from a specific Markdown notes file.
* As a user, I want to easily switch between different project contexts in the terminal to interact with the LLM about that specific project.
* As a user, I want to be able to pipe the output of one LLM interaction as input or additional context for a subsequent interaction, enabling chaining of commands or "assistant" capabilities.
* As a user, I want my API key for the LLM to be stored securely using environment variables.

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

  data:
    base_dir: data/
    global_context_dir: data/global_context/
    projects_dir: data/projects/
    calendar_dir: data/calendar/

  cli:
    default_command: ask

  logging:
    level: INFO
    file: logs/app.log
  ```

- **Context Management:**
  - Internally, context is handled as structured objects (dicts), but always rendered as a single string with explicit Markdown section headings (e.g., `## Personal Limitations:`) when sent to the LLM.
  - If a project context file is missing (e.g., no `tasks.yaml`), the context manager should warn (stderr and log), but not error.
- **LLM Prompt Engineering:**
  - Prompts sent to the LLM must always include explicit section headings.
  - Each CLI command/agent can define its own prompt template as needed.
- **File Writing/Editing:**
  - Always ask for confirmation before writing changes to files.
  - Show a diff in the terminal if the change is small (<50 lines); for larger changes, write the diff to a file for review.
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
├── data/                  # User-managed context files (Markdown, YAML)
│   ├── projects/
│   │   ├── project_a/
│   │   │   ├── notes.md
│   │   │   └── tasks.yaml
│   │   └── project_b/
│   │       ├── notes.md
│   │       └── readme.md
│   ├── calendar/
│   │   ├── events_YYYY.yaml # Local storage for calendar events
│   │   └── schedule_instructions.md # How you like your schedule managed
│   └── global_context/      # Files applicable across projects/tasks
│       ├── personal_bio.md    # Info about you for the LLM
│       ├── communication_style.md # How you want the AI to respond
│       ├── default_instructions.md # General rules/guidelines
│       └── personal_limitations.md # Context about personal challenges (e.g., ADHD)
├── src/                   # Python source code
│   ├── core/              # Core functionalities (LangChain interface, file parsing, context management)
│   │   ├── llm_interface.py # Handles communication with LLM APIs via LangChain
│   │   ├── file_parser.py   # Reads/writes different file types (Markdown, YAML, potentially JSON)
│   │   └── context_manager.py # Gathers and formats context from data/
│   ├── managers/          # Modules for specific domains (project, calendar)
│   │   ├── project_manager.py # Logic for interacting with project files
│   │   └── calendar_manager.py # Logic for interacting with calendar files, including Google Calendar integration (Step 2)
│   ├── cli/               # Command Line Interface handling
│   │   └── main.py          # Entry point for the CLI
│   └── utils/             # Helper functions
│       ├── config_loader.py # Handles loading configuration
│       └── google_auth.py   # Handles Google API authentication (Step 2)
├── config/                # Configuration files
│   └── settings.yaml
├── scripts/               # Utility scripts (e.g., setup, data migration, calendar sync trigger)
├── tests/                 # Your tests
├── .gitignore             # Specifies intentionally untracked files
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
└── LICENSE              # Project license


## 7. Success Metrics (Initial)

* The application can successfully load context from specified Markdown and YAML files.
* The application can successfully send prompts and loaded context to the LLM via LangChain and receive a response.
* Users can define different project contexts in the `data/projects/` directory and switch between them based on the working directory or a specified command-line argument.
* Basic features like summarizing a notes file or listing tasks from a YAML file via LLM interaction are functional, taking into account global and project-specific context.
* The application structure supports piping output from one interaction as input for the next.
* The code is organized according to the modular structure, making it reasonably easy to understand and extend for future features like Calendar integration (Step 2).
* Effective use of AI assistance throughout the development process is achieved, speeding up implementation and helping navigate unfamiliar patterns.