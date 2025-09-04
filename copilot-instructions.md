# hackingBuddyGPT

hackingBuddyGPT is a command-line tool that helps security researchers and
professional penetration-testers to use LLMs to perform security testing. It
is intended as a starting point for research and not for direct production use.
Initial use-cases were focused on linux and windows privilege escalation
attacks but recently more web-centric scenarios have been added.

## Tech stack in use

### Backend

- we try to keep dependencies as light as possible
- requests for HTTP requests

### User Interface

- Rich library for terminal output

### Testing

- Unittest for python

## Project and code guidelines

- Always use type hints in any language which supports them
- Unit tests are required, and are required to pass before PR
  - Unit tests should focus on core functionality
- Always follow good security practices
- Follow RESTful API design principles
- Use scripts to perform actions when available

## Project structure

- src/hackingBuddyGPT/ : Flask backend code
  - usecases/ : a use-case is typically a prototype for a specific scenario, e.g. linux priv-esc
  - capabilitites/ : are the capabilitites that can be called from within a use-case
  - utils/ : Utility functions and helpers
- tests/ : Unit tests for the backend code