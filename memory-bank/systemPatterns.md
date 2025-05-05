# System Patterns

This document outlines the system architecture, key technical decisions, design patterns, component relationships, and critical implementation paths of the Local LLM Terminal Environment.

## System Architecture

The system follows a modular architecture with clear separation of concerns:

```mermaid
graph TD
    CLI[CLI Layer] --> Core[Core Layer]
    CLI --> Utils[Utilities Layer]
    Core --> Utils
    
    subgraph "CLI Layer (src/cli/)"
        main.py[main.py - Entry Point]
    end
    
    subgraph "Core Layer (src/core/)"
        context_manager[ContextManager]
        llm_interface[LLMInterface]
        file_parser[File Parser]
        agent_loader[Agent Loader]
    end
    
    subgraph "Utilities Layer (src/utils/)"
        config_loader[ConfigLoader]
        chat_helpers[Chat Helpers]
        path_helpers[Path Helpers]
    end
```

### Directory Structure

```
/
├── config/                  # Static configuration
│   ├── settings.yaml        # Global settings
│   └── agents/              # Agent-specific configurations
│       └── <agent_name>/    # Per-agent configuration
│           ├── agent_config.yaml  # Agent configuration
│           └── system_prompt.md   # Agent system prompt
├── data/                    # Dynamic runtime data
│   ├── global_context/      # Global context files
│   └── agents/              # Agent-specific data
│       └── <agent_name>/    # Per-agent data
│           ├── memory/      # Conversation memory
│           └── output/      # Agent output files
├── src/                     # Source code
│   ├── cli/                 # Command-line interface
│   ├── core/                # Core functionality
│   └── utils/               # Utility functions
└── tests/                   # Test files
```

## Key Technical Decisions

1. **Modular Code Organization**
   - Clear separation between CLI, core functionality, and utilities
   - Each module has a single responsibility
   - Path construction logic centralized in path_helpers.py
   - Agent loading logic centralized in agent_loader.py
   - Chat helper functions centralized in chat_helpers.py

2. **Configuration Management**
   - YAML-based configuration with environment variable overrides
   - Separation of static configuration (config/) from dynamic data (data/)
   - ConfigLoader class provides a unified interface for accessing configuration
   - Configuration passed via context rather than global variables

3. **LLM Integration**
   - LangChain framework for LLM interaction
   - Google Gemini as the initial LLM provider
   - LLMInterface class encapsulates LLM communication
   - AgentExecutor pattern for tool-enabled interactions

4. **Memory Management**
   - Per-agent conversation memory
   - JSON-based persistence of conversation history
   - Memory loaded on agent initialization and saved on exit/switch
   - Session summaries generated and saved for context continuity

5. **Tool Integration**
   - LangChain's FileManagementToolkit for file operations
   - Sandboxed file access (agents can only access their own directories)
   - Read-only access to configuration files
   - Read-write access to agent data directories

## Design Patterns

1. **Dependency Injection**
   - ConfigLoader passed to components that need it
   - No global variables for better testability and maintainability
   - Click context used to pass configuration through CLI commands

2. **Factory Pattern**
   - `load_agent_executor` function creates and configures AgentExecutor instances
   - `load_tools` function creates tool instances based on configuration

3. **Strategy Pattern**
   - Different agents can be loaded with different configurations
   - Tools are loaded based on agent configuration

4. **Command Pattern**
   - CLI commands implemented using Click
   - Each command is a separate function with its own options

5. **Repository Pattern**
   - ContextManager acts as a repository for context data
   - Abstracts the details of where and how context is stored

6. **Facade Pattern**
   - LLMInterface provides a simplified interface to the LangChain framework
   - Hides the complexity of LLM communication

## Component Relationships

```mermaid
graph TD
    CLI[CLI] --> AgentLoader[Agent Loader]
    CLI --> ChatHelpers[Chat Helpers]
    AgentLoader --> ContextManager[Context Manager]
    AgentLoader --> PathHelpers[Path Helpers]
    ChatHelpers --> PathHelpers
    ContextManager --> FileParser[File Parser]
    ContextManager --> ConfigLoader[Config Loader]
    PathHelpers --> ConfigLoader
```

### Key Component Responsibilities

1. **ConfigLoader**
   - Loads configuration from YAML files and environment variables
   - Provides access to configuration values via dot notation

2. **ContextManager**
   - Loads and formats context from global context directory
   - Formats context data into structured strings for LLM consumption

3. **LLMInterface**
   - Initializes and configures the LLM
   - Provides methods for generating text responses
   - **Note:** This might be simplified or integrated directly into `AgentLoader` / LangChain's `AgentExecutor` setup depending on final implementation. The primary LLM setup now happens within `load_agent_executor`.

4. **AgentLoader**
   - Loads agent configuration (`agent_config.yaml`), including the detailed `tools_config` structure.
   - Creates and configures AgentExecutor instances.
   - Loads tools based on the `tools_config`, instantiating required toolkits (e.g., `FileManagementToolkit`) with specified scopes (resolved via `PathHelpers`) and applying configured tool names and descriptions. Handles efficient toolkit instantiation.

5. **ChatHelpers**
   - Manages conversation memory
   - Processes user commands
   - Generates and saves session summaries

6. **PathHelpers**
   - Provides standardized path construction functions
   - Ensures consistent directory structure access

7. **FileParser**
   - Reads and parses Markdown and YAML files
   - Handles file-related errors

## Critical Implementation Paths

### 1. CLI Initialization

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant ConfigLoader
    
    User->>CLI: Run command
    CLI->>ConfigLoader: Create instance
    ConfigLoader->>ConfigLoader: Load settings.yaml
    ConfigLoader->>ConfigLoader: Load .env
    CLI->>CLI: Set log level
    CLI->>CLI: Store ConfigLoader in context
```

### 2. Agent Loading

```mermaid
sequenceDiagram
    participant CLI
    participant AgentLoader
    participant ConfigLoader
    participant ContextManager
    participant LLM
    participant PathHelpers
    participant FileManagementToolkit # Example Toolkit
    
    CLI->>AgentLoader: load_agent_executor(agent_name, config_loader, memory)
    AgentLoader->>PathHelpers: Get agent config path
    AgentLoader->>AgentLoader: Load agent_config.yaml (including tools_config)
    AgentLoader->>AgentLoader: Configure LLM (e.g., ChatGoogleGenerativeAI)
    AgentLoader->>AgentLoader: load_tools(tools_config, agent_name)
        AgentLoader->>AgentLoader: Group tools_config by (ToolkitClass, ScopeSymbol)
        loop For each unique (ToolkitClass, ScopeSymbol)
            AgentLoader->>PathHelpers: Resolve ScopeSymbol to scope_path (e.g., get_memory_bank_dir)
            AgentLoader->>FileManagementToolkit: Instantiate toolkit(root_dir=scope_path, selected_tools=needed_original_names)
            FileManagementToolkit-->>AgentLoader: Return base tool instances
        end
        AgentLoader->>AgentLoader: Map base tools by (Toolkit, Scope, OriginalName)
        loop For each tool in original tools_config
            AgentLoader->>AgentLoader: Find base tool
            AgentLoader->>AgentLoader: Apply final name and description override
            AgentLoader->>AgentLoader: Add configured tool to list
        end
    AgentLoader-->>AgentLoader: Return list of configured tools
    AgentLoader->>ContextManager: get_context(None) # Global context
    ContextManager->>ContextManager: Load global context files
    ContextManager-->>AgentLoader: Return formatted global context
    AgentLoader->>AgentLoader: Format relevant agent config keys as context
    AgentLoader->>AgentLoader: Get system prompt (inline or from file)
    AgentLoader->>AgentLoader: Combine contexts into full system prompt
    AgentLoader->>AgentLoader: Create prompt template (ChatPromptTemplate)
    AgentLoader->>AgentLoader: Create tool-calling agent (create_tool_calling_agent)
    AgentLoader->>AgentLoader: Create AgentExecutor(agent, tools, memory)
    AgentLoader-->>CLI: Return AgentExecutor
```

### 3. Chat Session Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant ChatHelpers
    participant AgentExecutor
    participant Memory
    
    User->>CLI: Start chat
    CLI->>ChatHelpers: get_or_create_memory(agent_name)
    ChatHelpers->>ChatHelpers: Check if memory exists in memory dict
    ChatHelpers->>ChatHelpers: If not, load from file or create new
    ChatHelpers-->>CLI: Return memory
    CLI->>AgentLoader: load_agent_executor(agent_name)
    AgentLoader-->>CLI: Return executor
    
    loop Chat Loop
        User->>CLI: Enter input
        CLI->>ChatHelpers: process_user_command(input, agent, memory)
        alt Command: /exit
            ChatHelpers-->>CLI: Signal exit
        else Command: /agent
            ChatHelpers->>ChatHelpers: Save current memory
            ChatHelpers->>ChatHelpers: Load new memory
            ChatHelpers->>AgentLoader: Load new agent
            ChatHelpers-->>CLI: Return new agent and memory
        else Command: /summarize
            ChatHelpers->>AgentExecutor: Generate summary
            ChatHelpers->>ChatHelpers: Save summary to file
            ChatHelpers-->>CLI: Return summary
        else Regular input
            ChatHelpers->>Memory: Load memory variables
            ChatHelpers->>AgentExecutor: Invoke with input and history
            AgentExecutor-->>ChatHelpers: Return response
            ChatHelpers->>Memory: Save context
            ChatHelpers-->>CLI: Display output
        end
    end
    
    CLI->>ChatHelpers: generate_and_save_summary()
    CLI->>ChatHelpers: save_agent_memory() for all agents
```

### 4. Tool Usage Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant AgentExecutor
    participant SpecificTool # e.g., read_project_file
    participant FileManagementToolkit # Underlying Toolkit instance
    participant FileSystem
    
    User->>CLI: Enter input requiring tool
    CLI->>AgentExecutor: Invoke with input
    AgentExecutor->>AgentExecutor: Parse input, history, prompt
    AgentExecutor->>LLM: Predict next action (tool call)
    LLM-->>AgentExecutor: Decide to use tool (e.g., read_project_file) with args
    AgentExecutor->>SpecificTool: Call tool.invoke(args) # Matches configured tool name
    
    # Internal Tool Logic (Example: File Management)
    SpecificTool->>FileManagementToolkit: Execute underlying method (e.g., read_file)
    FileManagementToolkit->>FileSystem: Perform action in SCOPED directory (e.g., read from project root)
    FileSystem-->>FileManagementToolkit: Return result/status
    FileManagementToolkit-->>SpecificTool: Return result
    
    SpecificTool-->>AgentExecutor: Return tool result
    AgentExecutor->>LLM: Provide tool result for next step
    LLM-->>AgentExecutor: Generate final response based on tool result
    AgentExecutor-->>CLI: Return final response
    CLI->>User: Display response
```

## Implementation Notes

1. **Memory Persistence**
   - Conversation history is saved as JSON files
   - Each agent has its own memory file
   - Memory is loaded on agent initialization
   - Memory is saved on agent switch and application exit

2. **Context Loading**
   - Global context is loaded from data/global_context/
   - Agent configuration is loaded from config/agents/<agent_name>/
   - System prompt is loaded from config/agents/<agent_name>/system_prompt.md
   - Agent-specific data is stored in data/agents/<agent_name>/

3. **Tool Sandboxing**
   - Tool file system access is defined declaratively in `agent_config.yaml` via the `tools_config` section.
   - Each tool is configured with a `scope` (e.g., `PROJECT_ROOT`, `MEMORY_BANK`, `AGENT_DATA`, `AGENT_CONFIG`, `TASK_LIST`) which resolves to a specific directory path.
   - The underlying toolkit (e.g., `FileManagementToolkit`) is instantiated with this specific `root_dir`, inherently limiting its operations to that path and its subdirectories.
   - This configuration-driven approach defines the sandbox for each tool explicitly.

4. **Error Handling**
   - Comprehensive error handling for file operations
   - Graceful degradation when files are missing
   - Detailed logging for debugging

5. **Configuration Flexibility**
   - Configuration can be overridden via environment variables
   - Default values are provided for missing configuration
   - Agent-specific configuration can override global settings
