#!/usr/bin/env bash
# Project tool aliases — source this or set BASH_ENV to this file.
# Ensures pytest/ruff resolve to the project venv regardless of PATH.

VENV_DIR="/home/tim/github/llm-agent/.venv"

alias pytest="$VENV_DIR/bin/python -m pytest"
alias ruff="$VENV_DIR/bin/ruff"

# Also add venv bin to PATH as fallback
export PATH="$VENV_DIR/bin:$PATH"
