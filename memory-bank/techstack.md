# Tech Stack

This document summarizes the key technologies and tools selected for the Local LLM Terminal Environment project, based on the Product Requirements Document.

## 1. Core Technologies

* **Programming Language:** Python 3.x
* **LLM Interaction Framework:** LangChain
* **Initial LLM Provider:** Google Cloud (for Gemini Pro API)

## 2. Libraries & Dependencies

* **LLM API Client:** Handled by LangChain (will require configuring with Google Cloud credentials).
* **Command Line Interface (CLI):** Click
* **Structured Data Handling:** PyYAML (for reading/writing YAML)
* **Configuration Management:** PyYAML (for config files), `python-dotenv` or similar (for environment variables)
* **File Parsing (Markdown):** Standard Python file I/O, potentially `markdown` library if detailed parsing is needed later.
* **Google Calendar Integration (Step 2):** Google API Client Library for Python, handling OAuth 2.0.

## 3. File Formats

* **Notes & Free Text:** Markdown (.md)
* **Structured Data (Tasks, Calendar, Config):** YAML (.yaml, .yml) - Primary user-edited format.
* **Structured Data (Potential API Ingest):** JSON (Support to be considered later for reading).

## 4. Development Tools & Environment

* **Operating System:** Ubuntu 24.04 LTS
* **Python Environment Management:** venv (Python's built-in virtual environments)
* **Dependency Management:** pip and requirements.txt
* **Version Control:** Git
* **Code Editor:** Cursor (or any preferred Python-friendly editor/IDE)
* **Terminal:** Standard Ubuntu terminal

## 5. Project Structure

The project will follow a modular structure with clear separation of concerns:

* `data/`: User-managed context files.
* `src/`: Python source code (core, managers, cli, utils).
* `config/`: Application configuration files.
* `scripts/`: Utility scripts.
* `tests/`: Project tests.

---# Tech Stack

This document summarizes the key technologies and tools selected for the Local LLM Terminal Environment project, based on the Product Requirements Document.

## 1. Core Technologies

* **Programming Language:** Python 3.x
* **LLM Interaction Framework:** LangChain
* **Initial LLM Provider:** Google Cloud (for Gemini Pro API)

## 2. Libraries & Dependencies

* **LLM API Client:** Handled by LangChain (will require configuring with Google Cloud credentials).
* **Command Line Interface (CLI):** Click
* **Structured Data Handling:** PyYAML (for reading/writing YAML)
* **Configuration Management:** PyYAML (for config files), `python-dotenv` or similar (for environment variables)
* **File Parsing (Markdown):** Standard Python file I/O, potentially `markdown` library if detailed parsing is needed later.
* **Google Calendar Integration (Step 2):** Google API Client Library for Python, handling OAuth 2.0.

## 3. File Formats

* **Notes & Free Text:** Markdown (.md)
* **Structured Data (Tasks, Calendar, Config):** YAML (.yaml, .yml) - Primary user-edited format.
* **Structured Data (Potential API Ingest):** JSON (Support to be considered later for reading).

## 4. Development Tools & Environment

* **Operating System:** Ubuntu 24.04 LTS
* **Python Environment Management:** venv (Python's built-in virtual environments)
* **Dependency Management:** pip and requirements.txt
* **Version Control:** Git
* **Code Editor:** Cursor (or any preferred Python-friendly editor/IDE)
* **Terminal:** Standard Ubuntu terminal

## 5. Project Structure

The project will follow a modular structure with clear separation of concerns:

* `data/`: User-managed context files.
* `src/`: Python source code (core, managers, cli, utils).
* `config/`: Application configuration files.
* `scripts/`: Utility scripts.
* `tests/`: Project tests.

---