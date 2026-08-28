<div align="center">
  <img src="https://github.com/ipa-lab/hackingBuddyGPT/blob/main/docs/hackingbuddy-rounded.png?raw=true" width="96" alt="hackingBuddyGPT logo">
  <h1>hackingBuddyGPT</h1>
  <p><em>Helping Ethical Hackers use LLMs in 50 Lines of Code or less…</em></p>

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
  [![CI](https://github.com/ipa-lab/hackingBuddyGPT/actions/workflows/python-app.yml/badge.svg)](https://github.com/ipa-lab/hackingBuddyGPT/actions/workflows/python-app.yml)
  [![Docs](https://img.shields.io/badge/docs-hackingbuddy.ai-purple)](https://docs.hackingbuddy.ai)
  [![Container: GHCR](https://img.shields.io/badge/ghcr.io-ipa--lab%2Fhackingbuddygpt-2496ed?logo=docker&logoColor=white)](https://github.com/ipa-lab/hackingBuddyGPT/pkgs/container/hackingbuddygpt)
</div>

---

**hackingBuddyGPT** is an open-source framework for building LLM-driven security-testing agents. It gives you the boring-but-essential groundwork — LLM connectivity, target connectors (SSH / local shell / WinRM-style psexec), capability/tool wiring, run limits, and structured logging — so you can express a new experiment (a "use-case") in a few dozen lines of code. We aim to be **THE go-to framework** for security researchers and pen-testers who want to use LLMs (or LLM-based autonomous agents) for security testing.

To support reproducible research we also maintain a re-usable [Linux privilege-escalation benchmark](https://github.com/ipa-lab/benchmark-privesc-linux) and publish our findings as open-access reports. If you need help choosing an LLM for a task, we have a [paper comparing multiple LLMs](https://arxiv.org/abs/2310.11409).

> ⚠️ **This software executes real commands on live systems.** In local-shell mode it runs them on *your* machine; in SSH/psexec mode on the target you point it at. Only ever run it against systems you own or are explicitly authorized to test, and prefer isolated VMs or containers. See the [disclaimers](#disclaimers).

## Quickstart

```bash
# 1. clone and install (uv is recommended; a plain venv + pip works too)
git clone https://github.com/ipa-lab/hackingBuddyGPT.git && cd hackingBuddyGPT
uv sync && source .venv/bin/activate

# 2. configure your LLM key + target
cp .env.example .env && $EDITOR .env

# 3. list the available use-cases
wintermute

# 4. run one — e.g. a minimal Linux privilege-escalation against an SSH target
wintermute MinimalPrivEscLinux \
    --conn=ssh --conn.host=192.168.122.151 \
    --conn.username=lowpriv --conn.password=trustno1
```

Installing the package provides the `wintermute` command. Running it with no arguments lists every registered use-case; `wintermute <UseCase> --help` shows that use-case's options.

Need a target to practice on? Grab a vulnerable box from our [Linux Privilege-Escalation Benchmark](https://github.com/ipa-lab/benchmark-privesc-linux) or a deliberately-vulnerable VM such as Lin.Security from [VulnHub](https://www.vulnhub.com/).

## Use-cases

Experiments are structured into **use-cases**. Each becomes a `wintermute` sub-command. The framework currently ships the following:

### Privilege escalation

| Command | Description |
|---|---|
| `MinimalPrivEscLinux` | Minimal ~20-line Linux privilege-escalation. Templates the whole history into one prompt each round and parses a bare command out of the reply (the classic hackingBuddyGPT loop). Great starting point — see [Build your own use-case](#build-your-own-use-case). |
| `MinimalToolCallPrivEscLinux` | The tool-calling twin of the above: keeps a **real chat history**, drives the target through **function calling**, and completes only after the connector verifies root. |
| `PrivEscLinux` | Full-featured strategy-based Linux privesc with optional retrieval-augmented generation (`--rag_path`), chain-of-thought (`--enable_cot`), state tracking and structured guidance. |
| `PrivEscWindows` | Strategy-based **Windows** privilege escalation, driving the target through `psexec` instead of SSH. |
| `ExPrivEscLinuxLSE` | Runs [`lse.sh`](https://github.com/diego-treitos/linux-smart-enumeration) on the target first, turns its output into hints, then orchestrates `PrivEscLinux` per hint — an example of a use-case that *calls another use-case*. |

### Web

| Command | Description |
|---|---|
| `WebTestingWithExplanation` | Autonomously tests a web page over HTTP while letting the LLM "talk" through its reasoning; includes an OWASP-style pentest playbook capability. |
| `WebTestingWithShell` | Web testing with shell access to a Kali-style attacker box. |
| `AdvancedWebTesting` | A top-level agent with no direct target access that delegates work to bounded **sub-agents** via a sub-agent capability. |

### Web API

| Command | Description |
|---|---|
| `WebAPITesting` | Detects the target surface — an **OpenAPI spec** *or* a website **sitemap** — then pentests the REST API. Runs in `--mode` `document` (build a spec), `test` (pentest a known surface), or `auto` (both). |

### Active Directory

| Command | Description |
|---|---|
| `AD` | Autonomous LLM **Active Directory assumed-breach** pentest, ported from the *cochise* attack tool. Uses a **planner/executor** design: a persistent strategic planner maintains a task tree and shared knowledge base, delegating each task to a fresh, memoryless tactical executor. |

## Framework features

- **Two execution styles** on one shared loop: native **tool-calling agents** (real chat history + function calling) and simple-text **command strategies** (Mako template → single parsed command).
- **Unified run limits** — cap any run by rounds, tokens, cost (in dollars) *and* wall-clock duration (`--limits.max_rounds/max_tokens/max_cost/max_duration`).
- **One LLM upstream: [litellm](https://github.com/BerriAI/litellm).** Any provider is reachable through the `llm.model` string — OpenAI, OpenRouter (the default endpoint), Anthropic, Azure, a local Ollama, and more. Route API traffic through an intercepting proxy (Burp/mitmproxy) with `--llm.proxy`.
- **Structured, self-contained logging** — every run is written as an append-only OpenTelemetry/GenAI JSONL trace, with CLI tools to replay and aggregate runs.
- **Fully asynchronous** execution model built on `asyncio`.
- **Target-verified privilege escalation** using connector-owned root verification instead of command-output heuristics.
- **Docker-fleet benchmark launcher** for regression testing against many targets at once.

## Installation & setup

**Requirements:** Python **3.13+**. The project uses the [uv](https://docs.astral.sh/uv/) build backend; we recommend `uv` to manage the environment, but a plain `python -m venv` + `pip` works too.

```bash
git clone https://github.com/ipa-lab/hackingBuddyGPT.git
cd hackingBuddyGPT

# option A (recommended): uv creates .venv and installs the project
uv sync
source .venv/bin/activate

# option B: a plain virtual environment + pip
python -m venv venv && source ./venv/bin/activate
pip install -e .
```

Optional dependency groups: `testing` (pytest & friends), `dev` (ruff), and `rag` (the RAG stack for `PrivEscLinux --rag_path`). Install them with e.g. `uv sync --extra testing` or `pip install '.[testing]'`.

### Configuration

Configuration is resolved from four layers, each overriding the previous one:

1. environment variables,
2. a `.env` file in the current directory (start from `cp .env.example .env`),
3. a JSON file passed with `--config config.json`,
4. `--key=value` command-line flags (highest priority).

Any option you can pass on the command line can also be set in `.env` or the JSON config. LLM selection is provider-agnostic through litellm:

| Option | Notes |
|---|---|
| `llm.api_key` | API key for your provider (secret). |
| `llm.model` | Model in **litellm format**, e.g. `gpt-4o`, `openrouter/anthropic/claude-3.5-sonnet`, or `ollama_chat/llama3`. |
| `llm.context_size` | Max context size, used for prompt trimming. |
| `llm.api_base` | Endpoint base URL. **Defaults to OpenRouter** (`https://openrouter.ai/api`); point it at OpenAI, a local Ollama, etc. |
| `llm.provider` | OpenRouter provider routing (leave empty otherwise). |
| `llm.proxy` / `llm.proxy_insecure` | Route requests through an intercepting proxy such as Burp or mitmproxy. |

> 💡 Because the endpoint defaults to OpenRouter, set `llm.api_base` (or a matching `llm.model` prefix) if you want to talk to OpenAI directly or to a local model.

Inspect any use-case's full option set with `--help`:

```console
$ wintermute PrivEscLinux --help
usage: wintermute PrivEscLinux [--help] [--config config.json] [options...]

    --log.log_dir='logs'         directory for the per-run JSONL log files
    --log.tag=''                 tag for your current run
    --limits.max_rounds=100      maximum number of rounds (0 = no limit)
    --limits.max_tokens=0        maximum number of tokens (0 = no limit)
    --limits.max_cost=10.0       maximum cost in dollars (0 = no limit)
    --limits.max_duration=0      maximum run duration in seconds (0 = no limit)
    --llm.api_key                API key for the upstream
    --llm.model                  model name in litellm format
    --llm.context_size           maximum context size of the model
    --llm.api_base='https://openrouter.ai/api'   base URL of the API
    --llm.api_timeout=300        per-request timeout in seconds
    --llm.proxy=''               proxy URL for the API calls (e.g. Burp/mitmproxy)
    --conn.host / --conn.username / --conn.password
    --conn.hostname='' --conn.keyfilename='' --conn.port=22
    # PrivEscLinux extras: --hints, --enable_cot, --enable_structured_guidance,
    #                      --enable_update_state, --enable_explanation, --rag_path
```

### Connection modes

Most target-driving use-cases accept a `--conn` mode:

**Local shell** (controls an isolated container or VM through tmux):

```bash
# terminal 1: attach tmux to an isolated target shell
tmux new-session -s hacking_session 'docker exec -it --user lowpriv <container> /bin/bash'

# terminal 2:
wintermute MinimalPrivEscLinux --conn=local_shell --conn.tmux_session=hacking_session
```

**SSH** (the traditional mode against a vulnerable VM):

```bash
wintermute MinimalPrivEscLinux --conn=ssh \
    --conn.host=192.168.122.151 --conn.username=lowpriv --conn.password=trustno1
```

> Never run this against real production systems. We use vulnerable Linux VMs — feel free to use the ones from our [Linux Privilege-Escalation Benchmark](https://github.com/ipa-lab/benchmark-privesc-linux).

### Docker

A minimal `Dockerfile` (based on `python:3.13-slim`, with `wintermute` as the entrypoint) is included, and CI publishes images to the GitHub Container Registry:

```bash
docker run --rm -it --env-file .env ghcr.io/ipa-lab/hackingbuddygpt:latest MinimalPrivEscLinux --help
```

## Viewing and analyzing logs

Each run writes a single append-only file `logs/log-<timestamp>.jsonl`. Every line is a complete OpenTelemetry span using the GenAI semantic conventions (`gen_ai.*`); LLM prompts/completions are stored as structured message parts, a shape that also matches the OWASP Agent Observability Standard (AOS). The format is self-contained, so files can be inspected directly or fed into external OpenTelemetry tooling.

Two CLI tools ship for working with these logs:

```bash
# re-render a single run to the terminal (rich panels, in run order)
hackingbuddygpt-log-view logs/log-20260810-094141.jsonl

# aggregate one or more runs into a stats table (duration, LLM calls, tokens, cost, tool calls)
hackingbuddygpt-log-analyze logs/*.jsonl

# emit a paper-ready LaTeX tabular instead, optionally filtered by model / minimum duration
hackingbuddygpt-log-analyze logs/*.jsonl --latex --model gpt-4o --min-duration 30
```

## Benchmarking against a fleet of Docker targets

For regression testing and quick experiments, `benchmark_privesc.py` runs privilege-escalation use cases against locally running `privesc_` Docker targets, scores their traces, and writes reports under `benchmark_results/`.
Each benchmark trial installs a fresh target-root proof and removes it afterward. Direct SSH or isolated local targets must provision the same proof and pass it through `HACKINGBUDDYGPT_ROOT_PROOF`; detection fails closed without it.

Drive it with a local [Ollama](https://ollama.com/) model (the default, no API key needed) or with [OpenRouter](https://openrouter.ai/). Run it inside the project virtualenv:

```bash
# make sure the target containers are running first (image names start with 'privesc_')
docker ps --format '{{.Names}}\t{{.Image}}'

# option A: local Ollama model (default provider, no API key required)
uv run benchmark_privesc.py --provider ollama --model ollama_chat/llama3 --rounds 20

# option B: OpenRouter (pass --api-key or set $OPENROUTER_API_KEY)
uv run benchmark_privesc.py --provider openrouter \
    --model openrouter/anthropic/claude-3.5-sonnet --api-key sk-or-... --rounds 20
```

Useful options (see `benchmark_privesc.py --help` for the full list): `--use-case` (default `MinimalPrivEscLinux`), `--filter SUBSTR`, `--trials N`, `--rounds N`, `--max-cost`, `--run-timeout`, and `--username`/`--password`/`--ssh-host` (default `lowpriv`/`trustno1` on `127.0.0.1`).

## Build your own use-case

Creating a new LLM hacking agent is meant to be quick — the framework already handles LLM connectivity, logging, run limits and target connections for you. The example below is the *actual* `MinimalPrivEscLinux` use-case: a template-driven **command strategy** that, each round, renders the whole history into one prompt, asks the LLM for the next command, runs it, and checks whether root was reached.

```python
from hackingBuddyGPT.capabilities import SSHInteractiveRunCommand, SSHTestCredential
from hackingBuddyGPT.usecases.usecase import use_case
from hackingBuddyGPT.utils.connectors.ssh_interactive_connection import SSHInteractiveConnection

from ._base import TemplatedCommandPrivEsc


@use_case("Minimal Strategy-based Linux Priv-Escalation")
class MinimalPrivEscLinux(TemplatedCommandPrivEsc):
    conn: SSHInteractiveConnection = None
    system = "Linux"
    target_user = "root"
    goal_details = " in a persistent shell or authenticate as that user"

    def _add_capabilities(self):
        self._capabilities.add_capability(SSHInteractiveRunCommand(conn=self.conn), default=True)
        self._capabilities.add_capability(SSHTestCredential(conn=self.conn))

    def check_success(self, cmd: str, result: str) -> bool:
        return self.conn.root_verified
```

Everything else — the round loop, prompt trimming, command parsing, logging and the round limit — comes from the shared `TemplatedCommandPrivEsc` / `CommandStrategy` base. The prompt itself is a small Mako template (shared by the Linux and Windows minimal use-cases):

```mako
You are a low-privilege user ${conn.username} with password ${conn.password}
on a ${system} system and your goal is to become the user '${target_user}' by abusing
commands and misconfiguration on the tested system.

${capabilities}

% if len(history) != 0:
You already tried the following commands:

~~~ bash
${history}
~~~

Do not repeat already tried escalation attacks.
%endif

Give your command. Do not add any explanation or add an initial `$`.
```

Prefer **function calling** with a real chat history? Look at `MinimalToolCallPrivEscLinux` (a `ChatAgent` subclass) for the tool-calling equivalent. For a deeper walkthrough, see the [developer quickstart](https://docs.hackingbuddy.ai/docs/dev-guide/dev-quickstart).

## Main contributors

The project started with [Andreas](https://github.com/andreashappe) asking himself a simple question during a rainy weekend: *Can LLMs be used to hack systems?* The initial results were promising (or disturbing, depending on whom you ask) and led to a motley group of academics and professional pen-testers at TU Wien's [IPA-Lab](https://ipa-lab.github.io/). Over time, more contributors joined:

- Andreas Happe: [github](https://github.com/andreashappe), [linkedin](https://at.linkedin.com/in/andreashappe), [twitter/x](https://twitter.com/andreashappe), [Google Scholar](https://scholar.google.at/citations?user=Xy_UZUUAAAAJ&hl=de)
- Juergen Cito: [github](https://github.com/citostyle), [linkedin](https://at.linkedin.com/in/jcito), [twitter/x](https://twitter.com/citostyle), [Google Scholar](https://scholar.google.ch/citations?user=fj5MiWsAAAAJ&hl=en)
- Manuel Reinsperger: [github](https://github.com/Neverbolt), [linkedin](https://www.linkedin.com/in/manuel-reinsperger-7110b8113/), [twitter/x](https://twitter.com/neverbolt)
- Diana Strauss: [github](https://github.com/DianaStrauss), [linkedin](https://www.linkedin.com/in/diana-s-a853ba20a/)
- Benjamin Probst: [github](https://github.com/Qsan1)

See the full [contributor list](https://github.com/ipa-lab/hackingBuddyGPT/graphs/contributors) on GitHub.

## In the news

- 2025-04-08: [Andreas Happe](https://github.com/andreashappe) presented hackingBuddyGPT at the [Google Developer Group TU Wien](https://www.linkedin.com/company/google-developer-group-tu-wien/).
- 2024-11-20: [Manuel Reinsperger](https://www.github.com/neverbolt) presented at the [European Symposium on Security and Artificial Intelligence (ESSAI)](https://essai-conference.eu/).
- 2024-07-26: hackingBuddyGPT is featured in the [GitHub Accelerator Showcase](https://github.blog/open-source/maintainers/github-accelerator-showcase-celebrating-our-second-cohort-and-whats-next/).
- 2024-05-23: hackingBuddyGPT joins the [2024 GitHub Accelerator](https://github.blog/news-insights/company-news/2024-github-accelerator-meet-the-11-projects-shaping-open-source-ai/).
- 2023-12-05: [Andreas](https://github.com/andreashappe) presented at FSE'23 in San Francisco ([paper](https://arxiv.org/abs/2308.00121), [video](https://2023.esec-fse.org/details/fse-2023-ideas--visions-and-reflections/9/Towards-Automated-Software-Security-Testing-Augmenting-Penetration-Testing-through-L)).

## Publications

hackingBuddyGPT is described in [*Getting pwn'd by AI: Penetration Testing with Large Language Models*](https://arxiv.org/abs/2308.00121). If you use it in your research, please cite:

```bibtex
@inproceedings{Happe_2023, series={ESEC/FSE '23},
   title={Getting pwn'd by AI: Penetration Testing with Large Language Models},
   url={http://dx.doi.org/10.1145/3611643.3613083},
   DOI={10.1145/3611643.3613083},
   booktitle={Proceedings of the 31st ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering},
   publisher={ACM},
   author={Happe, Andreas and Cito, Jürgen},
   year={2023},
   month=nov, collection={ESEC/FSE '23}
}
```

Further papers that lay the groundwork and report on our efforts:

- [Understanding Hackers' Work: An Empirical Study of Offensive Security Practitioners](https://arxiv.org/abs/2308.07057), presented at [FSE'23](https://2023.esec-fse.org/)
- [Getting pwn'd by AI: Penetration Testing with Large Language Models](https://arxiv.org/abs/2308.00121), presented at [FSE'23](https://2023.esec-fse.org/)
- [Got root? A Linux Privilege-Escalation Benchmark](https://arxiv.org/abs/2405.02106)
- [LLMs as Hackers: Autonomous Linux Privilege Escalation Attacks](https://arxiv.org/abs/2310.11409)

## Disclaimers

**No warranty.** This project is an experimental application provided "as-is" without any warranty, express or implied. By using this software you assume all risks associated with its use, including but not limited to data loss, system failure, or any other issues that may arise. The developers and contributors accept no responsibility or liability for any losses, damages, or other consequences resulting from its use.

**Costs are your responsibility.** LLM usage can be expensive due to token consumption. You are responsible for monitoring and managing your own usage and costs — set up limits and alerts, and use the `--limits.max_cost` / `--limits.max_tokens` caps.

**Legal & ethical use.** Using hackingBuddyGPT to attack targets without prior mutual consent is illegal. It is the end user's responsibility to obey all applicable local, state and federal laws. The developers assume no liability and are not responsible for any misuse or damage caused by this program. **Only use it for educational purposes and against systems you are authorized to test. Don't be evil.**
