#!/bin/bash
# Post-task review reminder — fires when Claude stops responding

jq -n '{
  "additionalContext": "Before ending: verify your changes match the original plan/spec. If tests exist for modified code, confirm they pass. If this task is complete, commit the changes."
}'
