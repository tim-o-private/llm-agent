# Summary
The AI Coach supports planning, motivation, and reflection across the user’s daily flow.
#### Interaction Triggers
- Daily prioritization session (via chat)
- Post-task reflection prompts (after completion or skipped)
- Idle detection during execution (gentle nudge or encouragement)
- Review of scratch pad for task suggestions
- End-of-day journaling and feedback
#### Capabilities
- Reframe vague user input into actionable tasks
- Break down complex tasks into small steps (`task.breakdown`)
- Suggest re-scoping or rewards based on fatigue/frustration
- Maintain memory of completed tasks to enable streak tracking and reinforcement
- Adapt tone (cheerful, gentle, directive) based on user preference
#### State Requirements
- Must retain daily context (active task, scratch pad contents, focus sessions, user preferences)
- Must be time-aware (able to track when tasks or pomodoro sessions should be complete, or when user is getting toward the end of the day)
- Should gracefully degrade in low-connectivity or offline scenarios
