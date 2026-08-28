# Copilot Instructions for hackingBuddyGPT

## Project Summary

hackingBuddyGPT is a research-driven Python framework that helps security researchers and penetration testers use Large Language Models (LLMs) to automate and experiment with security testing, especially privilege escalation and web/API pentesting. It supports both local shell and SSH connections to targets, and is designed for rapid prototyping of new agent-based use cases. **Warning:** This tool executes real commands on live systems—use only in safe, isolated environments.

## Tech Stack
- **Language:** Python 3.10+
- **Core dependencies:** See `pyproject.toml` (notable: `fabric`, `requests`, `pydantic`, `pytest`)
- **CLI Entrypoint:** `wintermute` (see `src/hackingBuddyGPT/cli/wintermute.py`)
- **Web viewer:** Optional, for log viewing (`wintermute Viewer`)
- **RAG/Knowledge base:** Markdown files in `rag/`

## Project Structure
- `src/hackingBuddyGPT/` — Main Python package
  - `cli/` — CLI entrypoint (`wintermute.py`)
  - `capabilities/` — Modular agent actions (e.g., SSH, HTTP, note-taking)
  - `usecases/` — Agent logic for each use case (Linux privesc, web, API, etc.)
  - `utils/` — Shared helpers (LLM, logging, config, prompt generation)
- `tests/` — Pytest-based unit and integration tests
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
  - Example: `python src/hackingBuddyGPT/cli/wintermute.py PrivEscLinux --llm.api_key=... --conn=ssh ...`
  - See `README.md` for setup and usage instructions.
- **Testing:** `pip install '.[testing]' && pytest`
- **Linting:** `ruff` (config in `pyproject.toml`)
- **Benchmark:** `uv run benchmark_privesc.py --help` runs privesc use-cases against local `privesc_*` Docker containers.

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
- Use virtual environments for Python dependencies.
- Never expose the web viewer to the public internet.
- Always set API keys and credentials in `.env` or as prompted by scripts.
- For RAG, add new markdown files to the appropriate `rag/` subfolder.

---
For further details, see the `README.md` and https://docs.hackingbuddy.ai. When in doubt, prefer existing patterns over inventing new ones.
