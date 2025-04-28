Implementation Plan: Local LLM Terminal Environment

**AI Assistant Development Guidelines:**
- **Dependencies:** When adding new functionality that requires external libraries, update `requirements.txt` with the necessary packages and minimum versions (e.g., `some-library>=1.2.0`).
- **Testing:**
    - For every new module/class/function in `src/`, create a corresponding test file in `tests/` mirroring the directory structure (e.g., `src/core/foo.py` -> `tests/core/test_foo.py`).
    - Write comprehensive tests using `pytest` and `unittest.mock` (for mocking dependencies/API calls).
    - Ensure necessary `__init__.py` files exist in both `src` and `tests` subdirectories to make them packages.
    - **Import Hack:** Until a better solution (like `pyproject.toml`) is implemented, start test files with the `sys.path.insert(...)` boilerplate to ensure `src` is importable:
      ```python
      import sys
      import os
      sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
      # ... rest of imports ...
      ```
    - Use relative imports within tests (e.g., `from core.llm_interface import LLMInterface`).
- **Installation Reminder:** After updating `requirements.txt`, remind the user to run `pip install -r requirements.txt`.

---

This document provides a step-by-step implementation plan for building the Local LLM Terminal Environment, based on the requirements outlined in the PRD.md, the technologies defined in techstack.md, and the project structure (aligned with project-structure.md principles). This plan is designed to be used as a guide for development, particularly when working with an AI coding assistant like Cursor.

The plan is broken down into phases, starting with core components and building towards the full feature set.
Phase 1: Core Foundation (Configuration, LLM Interface, File Parsing, Context)

Goal: Establish the fundamental capabilities for loading settings, interacting with the LLM, reading local files, and preparing context.

Step 1.1: Configuration Loading

    Goal: Create a utility to load application settings from config/settings.yaml and environment variables.
    File(s): src/utils/config_loader.py, config/settings.yaml, .env
    Key Functionality:
        Load .env file using python-dotenv.
        Load config/settings.yaml using PyYAML.
        Provide access to configuration values, prioritizing environment variables for sensitive data (like API keys).
    Tech Stack: Python, PyYAML, python-dotenv.
    AI Assistance: Ask Cursor to draft a ConfigLoader class with methods to load YAML and environment variables, handle potential file not found errors, and provide a way to get settings by key.
    Testing: Write simple tests for config_loader.py to ensure settings are loaded correctly from both sources.

Step 1.2: LLM Interface (LangChain + Gemini)

    Goal: Create a module to interact with the LLM via LangChain.
    File(s): src/core/llm_interface.py
    Key Functionality:
        Initialize the LangChain Google Gemini model, using the API key loaded from configuration/environment variables.
        Create a function or method to send a prompt (and potentially additional context) to the LLM and receive the response.
        Implement basic error handling for API calls.
    Tech Stack: Python, langchain, google-generativeai.
    AI Assistance: Ask Cursor to draft an LLMInterface class. Include a method generate_text(prompt: str, context: str = "") -> str that uses LangChain's Google Gemini integration to send the prompt and context and return the response text. Ensure it uses the API key loaded via environment variables.
    Testing: Write tests (potentially using mocking to avoid real API calls during unit tests) for llm_interface.py to ensure it calls the LangChain model correctly and handles responses.

Step 1.3: File Parsing (Markdown & YAML)

    Goal: Create utilities to read content from Markdown and YAML files.
    File(s): src/core/file_parser.py
    Key Functionality:
        Function read_markdown(filepath: str) -> str: Reads a Markdown file and returns its content as a string. Handle file not found errors.
        Function read_yaml(filepath: str) -> Dict[str, Any]: Reads a YAML file, parses it, and returns a Python dictionary. Handle file not found and parsing errors.
    Tech Stack: Python, PyYAML. (Markdown parsing can initially be simple file reading).
    AI Assistance: Ask Cursor to write the read_markdown and read_yaml functions. Include docstrings and type hints.
    Testing: Write unit tests for file_parser.py using sample Markdown and YAML files. Test both successful reads and error cases (file not found, invalid YAML).

Step 1.4: Context Management

    Goal: Create a module to gather and format context from different files (data/global_context/, data/projects/).
    File(s): src/core/context_manager.py
    Key Functionality:
        A class or functions to locate context files based on a specified project path (or current working directory) and the global context path.
        Read relevant Markdown and YAML files using the file_parser.
        Combine the content of multiple files into a single, structured string or object that can be passed to the LLM (consider using clear headings/separators like ## Project Notes: or ## Tasks:).
        Handle the case where project-specific context is not found.
    Tech Stack: Python, uses file_parser.py.
    AI Assistance: Ask Cursor to design a ContextManager class. It should have a method like get_context(project_path: str | None = None) -> str that reads global context and optional project context and formats it.
    Testing: Write tests for context_manager.py. Create a test data/ structure with sample files and assert that the context manager correctly finds, reads, and combines the content.

Phase 2: Command Line Interface (CLI)

Goal: Build the command-line entry point using Click, allowing users to trigger LLM interactions with context.

Step 2.1: Basic CLI Structure

    Goal: Set up the main CLI command and options using Click.
    File(s): src/cli/main.py
    Key Functionality:
        Define the main command group.
        Add a command (e.g., ask) that takes a user query as an argument.
        Include an option to specify the project path (e.g., --project /path/to/project).
        Integrate the ConfigLoader to load settings at the start of the command execution.
        Integrate the ContextManager to load context based on the specified project or current directory.
        Integrate the LLMInterface to send the user query and loaded context to the LLM.
        Print the LLM's response to the terminal.
    Tech Stack: Python, Click, uses config_loader.py, context_manager.py, llm_interface.py.
    AI Assistance: Ask Cursor to draft the main.py structure using Click. Define the cli group and the ask command. Implement the logic to load config, context, call the LLM interface, and print the result.
    Testing: Write integration tests for main.py (can be basic tests that check if the command runs and calls the core components, possibly with mocking).

Step 2.2: Implement Context Switching Logic

    Goal: Refine the CLI and ContextManager to correctly handle the default (current directory) and explicit (--project flag) project context loading.
    File(s): src/cli/main.py, src/core/context_manager.py
    Key Functionality:
        In main.py, get the current working directory if --project is not provided.
        Pass the determined project path to the ContextManager.
        Ensure ContextManager correctly looks for context files in the specified project directory relative to the base data/projects path.
    Tech Stack: Python, Click, os.
    AI Assistance: Ask Cursor to refine the ask command in main.py to implement the working directory default for the project path. Update the ContextManager as needed based on how you decide to pass and handle paths.
    Testing: Add tests to context_manager.py to specifically cover loading context from different project paths and the handling of None or empty paths (for the default case).

Phase 3: Incorporating Specific Features

Goal: Add functionality to support specific user stories like summarizing files and leveraging the personal_limitations.md.

Step 3.1: Implement File Summarization Command

    Goal: Add a CLI command to summarize a specific file using the LLM.
    File(s): src/cli/main.py
    Key Functionality:
        Add a new Click command (e.g., summarize) that takes a file path as an argument.
        Read the content of the specified file using file_parser.
        Load global context (and potentially project context if the file is project-specific).
        Formulate a prompt for the LLM asking it to summarize the provided file content, incorporating the relevant context (e.g., "Using the following project context and my personal preferences, summarize the content below: [context] [file content]").
        Send the prompt to the LLM via llm_interface.
        Print the summary.
    Tech Stack: Python, Click, uses file_parser.py, context_manager.py, llm_interface.py.
    AI Assistance: Ask Cursor to add a summarize command to main.py. Implement the logic to read the file, get context, formulate the prompt, call the LLM, and print the output.
    Testing: Write tests for the summarize command, potentially mocking the llm_interface to control the LLM's "response" and verify the correct prompt is constructed.

Step 3.2: Leverage personal_limitations.md Context

    Goal: Ensure the personal_limitations.md content is consistently included in the context provided to the LLM, enabling it to offer proactive suggestions.
    File(s): src/core/context_manager.py
    Key Functionality:
        Modify ContextManager to explicitly look for and include the data/global_context/personal_limitations.md file content in the combined context string.
        Ensure this context is formatted clearly (e.g., ## Personal Limitations: [content]) so the LLM can easily identify it.
    Tech Stack: Python, uses file_parser.py.
    AI Assistance: Ask Cursor to update the ContextManager's context gathering logic to include the content of personal_limitations.md if the file exists.
    Testing: Add tests to context_manager.py to verify that the personal_limitations.md content is included in the output when the file is present.

Step 3.3: Implement Basic Task/Calendar Overview

    Goal: Create a command to get an overview of tasks and calendar events based on the loaded context.
    File(s): src/cli/main.py, src/managers/project_manager.py, src/managers/calendar_manager.py (initial structure).
    Key Functionality:
        Add a new Click command (e.g., overview or agenda).
        This command will likely load both project context (tasks from YAML) and potentially calendar context (from YAML, manually created for now).
        Create initial placeholder Manager classes (ProjectManager, CalendarManager) in src/managers. These classes will initially just contain methods to read their respective data files using file_parser.
        Formulate a prompt for the LLM asking for an overview or agenda based on the provided task and calendar data.
        Send the prompt and context to the LLM.
        Print the LLM's response.
    Tech Stack: Python, Click, uses file_parser.py, context_manager.py, llm_interface.py, initial project_manager.py, calendar_manager.py.
    AI Assistance: Ask Cursor to add an overview command to main.py. Draft the initial ProjectManager and CalendarManager classes with methods to read data files. Implement the logic in main.py to load this data, form the prompt, call the LLM, and print the result.
    Testing: Write tests for the new command and manager methods (initially focusing on reading data files correctly).

Phase 4: Advanced Features & Refinements (Step 2 Features)

Goal: Implement more complex features like Google Calendar integration and potentially file updates.

Step 4.1: Google Calendar Integration (Fetch)

    Goal: Implement the functionality to fetch calendar events from Google Calendar and save them locally.
    File(s): src/managers/calendar_manager.py, src/utils/google_auth.py, src/cli/main.py (new command), potentially scripts/ (for setup flow).
    Key Functionality:
        Implement OAuth 2.0 flow for Google Calendar API authentication in src/utils/google_auth.py. This is a multi-step process involving getting credentials, user consent via browser, and storing tokens.
        Add a method to CalendarManager to fetch events from the Google Calendar API using the obtained credentials.
        Add a method to CalendarManager to save fetched events to a local YAML file (data/calendar/events_YYYY.yaml).
        Add a new Click command (e.g., calendar-sync) to main.py that triggers the authentication flow and event fetching/saving.
    Tech Stack: Python, Google API Client Library, PyYAML, Click, uses google_auth.py.
    AI Assistance: This is a more complex step involving external API interaction and authentication flows. Ask Cursor for guidance on implementing the Google Calendar API OAuth flow in Python. Ask for code drafts for fetching events and saving them to YAML. Draft the calendar-sync command in main.py.
    Testing: Test the authentication flow, fetching events (possibly with mocked API responses initially), and saving to YAML.

Step 4.2: Implement LLM Ability to Update Files

    Goal: Allow the LLM to propose changes to local files (e.g., updating a task list).
    File(s): src/core/llm_interface.py, src/core/file_parser.py (add write functionality), src/cli/main.py (modify command).
    Key Functionality:
        Modify the LLM interaction flow to request the LLM output changes in a structured format (e.g., diff format, or returning the entire modified file content). This requires careful prompt engineering.
        Add write_markdown(filepath: str, content: str) and write_yaml(filepath: str, data: Dict[str, Any]) methods to file_parser.py.
        Add logic to the CLI command (ask or a new edit command) to parse the LLM's suggested changes and apply them to the local file using the write methods in file_parser. Consider adding a confirmation step before saving changes.
    Tech Stack: Python, uses llm_interface.py, file_parser.py. Requires advanced prompt engineering.
    AI Assistance: Ask Cursor for help with prompt engineering to get structured output from the LLM for file updates. Ask for code drafts for the write file methods and the logic to apply changes in the CLI.
    Testing: Test the file writing functions. Test the LLM interaction flow (potentially with mocked LLM responses) to ensure proposed changes are correctly parsed and applied.

Step 4.3: Implement Piping Output

    Goal: Allow the output of one command to be used as input for another.
    File(s): src/cli/main.py
    Key Functionality:
        Design the CLI commands to print their primary output to standard output (stdout).
        Design commands that can accept input from standard input (stdin), which is how piping works in the terminal.
        Modify commands (like ask) to allow receiving the initial prompt or additional context via stdin if no direct argument is provided.
    Tech Stack: Python, Click, standard input/output handling.
    AI Assistance: Ask Cursor how to read from stdin in a Click application. Modify existing commands (ask, summarize, overview) to handle input from stdin.
    Testing: Test commands by piping output from one command to another in the terminal.

Phase 5: Refinement, Testing, and Documentation

Goal: Ensure the application is robust, well-tested, and clearly documented.

Step 5.1: Comprehensive Testing

    Goal: Increase test coverage for all modules and features.
    File(s): tests/ directory
    Key Functionality:
        Write unit tests for individual functions and methods in src/core/ and src/utils/.
        Write integration tests to ensure modules work together correctly (e.g., ContextManager with file_parser).
        Write tests for the CLI commands, potentially using Click's testing utilities.
        Use mocking where necessary (especially for LLM API calls and external services like Google Calendar) to make tests fast and reliable.
    Tech Stack: Python, unittest or pytest (choose one), unittest.mock or pytest-mock.
    AI Assistance: Ask Cursor to help write tests for specific functions or modules. Provide the code you want to test and ask for unit test cases or drafts using your chosen testing framework.

Step 5.2: Documentation

    Goal: Create a README.md file that explains how to install, configure, and use the application.
    File(s): README.md
    Key Functionality:
        Project title and description.
        Installation instructions (including virtual environment setup and dependencies).
        Configuration instructions (API key, settings.yaml, data directory structure).
        How to use the CLI commands with examples (ask, summarize, etc.).
        Explanation of context files and how to structure data/.
        Details on Step 2 features like Calendar integration once implemented.
    Tech Stack: Markdown.
    AI Assistance: Ask Cursor to draft sections of the README.md based on the PRD and the implemented features.

Step 5.3: Code Review and Refinement

    Goal: Review the code for style, clarity, efficiency, and adherence to best practices (potentially incorporating your project-structure.md rules more formally here).
    File(s): All .py files in src/
    Key Functionality:
        Ensure consistent code style (e.g., using a linter like Flake8 or Black).
        Add or improve docstrings and type hints.
        Refactor code for better readability and maintainability.
        Handle edge cases and errors gracefully.
    Tech Stack: Python, linters/formatters.
    AI Assistance: Ask Cursor to review specific functions or files for style, clarity, potential bugs, and to add docstrings/type hints.

This plan provides a detailed roadmap. Remember that development is often iterative. You might find yourself revisiting earlier steps as you learn more. Use Cursor frequently for drafting code snippets, explaining concepts, suggesting alternatives, writing tests, and debugging.

Good luck, and let me know when you're ready to start coding the first step (Configuration Loading in src/utils/config_loader.py)!