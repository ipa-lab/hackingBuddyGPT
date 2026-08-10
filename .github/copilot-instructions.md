# Copilot Instructions for hackingBuddyGPT

## Project Summary

hackingBuddyGPT is a research-driven Python framework that helps security researchers and penetration testers use Large Language Models (LLMs) to automate and experiment with security testing, especially privilege escalation and web/API pentesting. It supports both local shell and SSH connections to targets, and is designed for rapid prototyping of new agent-based use cases. **Warning:** This tool executes real commands on live systems—use only in safe, isolated environments.

## Tech Stack
- **Language:** Python 3.10+
- **Core dependencies:** See `pyproject.toml` (notable: `fabric`, `requests`, `pydantic`, `pytest`)
- **CLI Entrypoint:** `wintermute` (see `src/hackingBuddyGPT/cli/wintermute.py`)
- **Web viewer:** Optional, for log viewing (`wintermute Viewer`)
- **RAG/Knowledge base:** Markdown files in `rag/`
- **Container/VM orchestration:** Bash scripts in `scripts/`, Ansible playbooks (`tasks.yaml`)

## Project Structure
- `src/hackingBuddyGPT/` — Main Python package
  - `cli/` — CLI entrypoint (`wintermute.py`)
  - `capabilities/` — Modular agent actions (e.g., SSH, HTTP, note-taking)
  - `usecases/` — Agent logic for each use case (Linux privesc, web, API, etc.)
  - `utils/` — Shared helpers (LLM, logging, config, prompt generation)
- `tests/` — Pytest-based unit and integration tests
- `scripts/` — Setup, orchestration, and run scripts for Mac, Codespaces, and containers
- `rag/` — Markdown knowledge base for RAG (GTFOBins, HackTricks)
- `docs/` — Minimal, see https://docs.hackingbuddy.ai for full docs

## Setup & Usage
- **Python:** Use 3.10+ (see `pyproject.toml`).
- **Install:**
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install -e .
  ```
- **Run:**
  - List use cases: `python src/hackingBuddyGPT/cli/wintermute.py`
  - Example: `python src/hackingBuddyGPT/cli/wintermute.py LinuxPrivesc --llm.api_key=... --conn=ssh ...`
  - See `README.md`, `MAC.md`, `CODESPACES.md` for platform-specific instructions.
- **Testing:** `pip install '.[testing]' && pytest`
- **Linting:** `ruff` (config in `pyproject.toml`)
- **Container/VM setup:** Use scripts in `scripts/` (see comments in each script for prerequisites and usage).

## Coding Guidelines
- Follow PEP8 and use `ruff` for linting (see `[tool.ruff]` in `pyproject.toml`).
- Use type hints and docstrings for all public functions/classes.
- Place new agent logic in `usecases/`, new capabilities in `capabilities/`.
- Prefer composition (capabilities, helpers) over inheritance.
- Use the logging utilities in `utils/logging.py`.
- Document all new scripts and major changes in the `README.md` or relevant `.md` files.
- Mark all workarounds or hacks with `HACK`, `TODO`, or `FIXME`.

## Existing Tools & Resources
- **Documentation:** https://docs.hackingbuddy.ai
- **Community/Support:** Discord link in `README.md`
- **Security Policy:** See `SECURITY.md`
- **Code of Conduct:** See `CODE_OF_CONDUCT.md`
- **Contribution Guide:** See `CONTRIBUTING.md`
- **Citations:** See `CITATION.cff`
- **Benchmarks:** https://github.com/ipa-lab/benchmark-privesc-linux

## Tips to Minimize Bash/Build Failures
- Always use the provided scripts for environment/container setup; do not run ad-hoc commands unless necessary.
- Ensure Bash version 4+ (Mac: install via Homebrew).
- Use virtual environments for Python dependencies.
- For Codespaces/Mac, follow the step-by-step guides in `CODESPACES.md` and `MAC.md`.
- Never expose the web viewer to the public internet.
- Always set API keys and credentials in `.env` or as prompted by scripts.
- For RAG, add new markdown files to the appropriate `rag/` subfolder.

---
For further details, see the `README.md` and https://docs.hackingbuddy.ai. When in doubt, prefer existing patterns and scripts over inventing new ones.
