# Skills & Plugins

## Skills

Skills are `.claude/skills/*/SKILL.md` files that Claude invokes autonomously based on context. They're filesystem artifacts — no programmatic API.

### Loading requirements

1. `setting_sources` must include `"project"` (or `"user"` for `~/.claude/skills/`)
2. `"Skill"` must be in `allowed_tools`
3. `cwd` must point to a directory containing `.claude/skills/`

```python
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    setting_sources=["project"],
    allowed_tools=["Skill", "Read", "Write", "Bash"],
)
```

**The `claude_code` system prompt preset does NOT load skills.** You must set `setting_sources`.

### Skill locations

- **Project:** `.claude/skills/` — shared via git, loaded with `setting_sources=["project"]`
- **User:** `~/.claude/skills/` — personal, loaded with `setting_sources=["user"]`
- **Plugin:** bundled with installed plugins

### Skill in subagents

List skill names in `AgentDefinition.skills` to make them available:

```python
AgentDefinition(
    description="...",
    prompt="...",
    skills=["backend-patterns", "database-patterns"],
)
```

Subagents do NOT inherit parent's skills by default.

### Discovering available skills

```python
async for message in query(
    prompt="What Skills are available?",
    options=ClaudeAgentOptions(
        setting_sources=["project"],
        allowed_tools=["Skill"],
    ),
):
    print(message)
```

## Plugins

Plugins bundle skills, agents, hooks, and MCP servers as distributable packages.

### Loading

```python
options = ClaudeAgentOptions(
    plugins=[
        {"type": "local", "path": "./my-plugin"},
        {"type": "local", "path": "/absolute/path/to/plugin"},
    ],
)
```

Paths can be relative (to cwd) or absolute.

### Plugin structure

```
my-plugin/
  .claude-plugin/plugin.json   # Required manifest
  skills/my-skill/SKILL.md     # Agent skills
  agents/specialist.md         # Custom agents
  hooks/hooks.json             # Event handlers
  .mcp.json                    # MCP servers
```

### Namespacing

Plugin skills are namespaced: `/plugin-name:skill-name`.

### Verify loading

```python
if isinstance(message, SystemMessage) and message.subtype == "init":
    print("Plugins:", message.data.get("plugins"))
    print("Commands:", message.data.get("slash_commands"))
```
