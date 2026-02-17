# 🎨 CREATIVE PHASE: Architecture Design - Agent Execution Logic & Prompt Customization

**Date:** {datetime.now().isoformat()}
**Associated Task in `tasks.md`:** BRAINPLN-001 / PLAN-STEP-3: "Initiate CREATIVE phase for Agent Execution Logic & Prompt Customization Architecture."

## 1. Component Description

This component focuses on refactoring and enhancing the core agent execution logic. It needs to define how an agent's lifecycle is managed, how it integrates memory (from CPC1 - Agent Memory Solution), utilizes tools (based on `agent_tool_architecture_v1.md`), and critically, how an agent can adapt or customize parts of its prompt/instructions based on user feedback or learned preferences. The goal is a more modular, observable, and adaptable agent core.

## 2. Requirements & Constraints

*   **Functional Requirements:**
    *   **FR1: Modular Agent Core:** The agent execution flow (initialization, thought process, tool use, response generation) should be broken down into discernible, potentially overridable stages.
    *   **FR2: Memory Integration:** Seamlessly integrate the chosen memory solution (CPC1) for context retrieval and history updates.
    *   **FR3: Tool Integration:** Utilize the "Registry-Based Pluggable Tool Architecture" for dynamic tool loading and execution.
    *   **FR4: Prompt Customization Mechanism:**
        *   Allow agents (or a meta-agent/process) to modify specific, designated sections of their core prompt or add contextual instructions based on user feedback or interaction history.
        *   This customization should persist for a user/agent pairing.
    *   **FR5: State Management:** Manage agent state effectively during a turn (e.g., current thoughts, tool calls, intermediate steps).
    *   **FR6: Observability:** Provide mechanisms for better logging and tracing of an agent's internal decision-making process.
*   **Non-Functional Requirements:**
    *   **NFR1: Extensibility:** The architecture should make it easier to add new agent capabilities or modify existing ones.
    *   **NFR2: Maintainability:** Code should be well-structured, documented, and testable.
    *   **NFR3: Performance:** Refactoring should not introduce significant performance degradation.
    *   **NFR4: Security:** Prompt modifications should be handled securely to prevent injection vulnerabilities if user input directly influences core prompts.
*   **Constraints:**
    *   **C1: LangChain Foundation:** Continue to build upon LangChain's agent concepts (AgentExecutor, BaseSingleActionAgent, etc.) where appropriate, but don't be limited by them if a more modular approach is beneficial.
    *   **C2: Existing `agent_loader.py`:** The refactor should address the complexities in `agent_loader.py` and its surrounding logic.
    *   **C3: Supabase for Persistence:** User-specific prompt customizations or learned preferences should be persisted in Supabase.

## 3. Options Analysis

**Option 1: Enhanced LangChain AgentExecutor with Custom Callbacks & Prompt Templating**

*   **Description:**
    *   Continue using LangChain's `AgentExecutor` as the primary execution loop.
    *   Leverage LangChain Callbacks (`BaseCallbackHandler`) extensively.
    *   For Prompt Customization: Define specific sections within the agent's system prompt template populated at runtime from Supabase. Agent tool requests changes to these sections.
*   **Pros:** Leverages LangChain, callbacks for extensibility, simpler prompt customization via templating.
*   **Cons:** `AgentExecutor` as black box, limited agent agency in prompt modification, potential callback hell.

**Option 2: Custom Agent Orchestration Loop with Pluggable Stages**

*   **Description:**
    *   Develop a custom loop with explicit stages (ContextAssembly, ThoughtGeneration, etc.).
    *   Prompt Customization: `ContextAssemblyStage` layers customizations from Supabase. Agent meta-tool directly manages customizable prompt sections via API.
*   **Pros:** High modularity/control, improved testability, direct prompt agency (potentially), clear extensibility.
*   **Cons:** More development effort, reinventing parts of `AgentExecutor`, potential pipeline complexity.

**Option 3: Hybrid Approach - Modified `AgentExecutor` with Custom Agent Class**

*   **Description:**
    *   Create a custom LangChain Agent class (e.g., inheriting `BaseSingleActionAgent`).
    *   This class handles prompt construction (including dynamic customizations from Supabase) and response parsing.
    *   Use `AgentExecutor` with this custom agent.
    *   Prompt Customization: Custom agent fetches customizations. Dedicated tool calls API to update persisted customizations.
*   **Pros:** Balances LangChain usage & control, clear locus for prompting logic, good for observability.
*   **Cons:** Still tied to `AgentExecutor` structure, custom agent class could become complex.

## 4. Recommended Approach & Justification

**Chosen Option: Option 3 - Hybrid Approach: Modified `AgentExecutor` with Custom Agent Class**

**Justification:**

This hybrid approach offers the most pragmatic path forward, balancing LangChain's `AgentExecutor` with the need for deep control over prompt construction and customization.

*   **Leverages Strengths:** Uses `AgentExecutor` for its robust loop, reducing custom plumbing.
*   **Targeted Customization:** A custom Agent class (`CustomizableAgent`) provides precise control over prompt assembly (fetching base template, memory, tools, and dynamic user-customizations from Supabase) and output parsing.
*   **Clear Path for Prompt Customization (FR4):** `CustomizableAgent` uses a `PromptManagerService` (backed by `chatServer` API & Supabase) to fetch customizations. An `update_self_instructions_tool` allows the agent to request changes to its persisted instructions via the API.
*   **Maintainability & Extensibility:** More maintainable than a fully custom loop, building on familiar LangChain concepts. Extensible by modifying `CustomizableAgent` or adding new prompt management tools.
*   **Integration with CPC1 & Tool Architecture:** Easily integrates Supabase-backed memory and tools from the Registry-Based Architecture.

## 5. Implementation Guidelines

1.  **`PromptManagerService` (`chatServer` and/or `src.core.prompting`):**
    *   **API (`chatServer`):** Endpoints like `/api/agent/prompt_customizations/{user_id}/{agent_name}` (GET/PUT).
    *   **Persistence (Supabase):** Table `user_agent_prompt_customizations` (`user_id`, `agent_name`, `customization_type`, `content`).
    *   **Service Logic (`src.core.prompting`):** Python client for `chatServer` API or direct Supabase interaction.
2.  **`CustomizableAgent(BaseSingleActionAgent)` (`src.core.agents`):**
    *   **`__init__`:** Takes LLM, tools, `user_id`, `agent_name`.
    *   **Prompt Formatting Logic:** Fetches base prompt, calls `PromptManagerService` for customizations, integrates them, formats tools/memory.
    *   **Input Keys:** Define expected inputs.
    *   **Output Parser:** Standard LangChain output parser.
3.  **Tool: `update_self_instructions_tool`:**
    *   `BaseTool` taking `instruction_change_proposal: str`, `customization_type: str`.
    *   `_run` method calls `chatServer` API to save the proposal.
4.  **Refactor `agent_loader.py` (or successor):**
    *   Instantiate `CustomizableAgent` if specified in config.
    *   Pass `user_id` to agent instantiation.
5.  **Agent Configuration (`agent.yaml`):**
    *   Flag like `agent_class: CustomizableAgent`.
    *   Base prompt template path.
6.  **Observability (FR6):**
    *   Detailed logging in `CustomizableAgent` and `PromptManagerService`.
    *   Consider LangSmith/tracing tool.

## 6. Verification Checkpoint

*   [X] **Addresses FR1-FR6:** Yes, through custom agent class, `AgentExecutor`, prompt management service, and new tool.
*   [X] **Addresses NFR1-NFR4:** Yes, balances extensibility, maintainability, performance, and security.
*   [X] **Adheres to C1-C3:** Yes, builds on LangChain, refactors `agent_loader.py` implicitly, uses Supabase for persistence.

---
🎨🎨🎨 **EXITING CREATIVE PHASE: Architecture Design - Agent Execution Logic & Prompt Customization** 🎨🎨🎨 