# Use Case: GitHub Codespaces

**Backstory**

https://github.com/ipa-lab/hackingBuddyGPT/pull/85#issuecomment-2331166997

> Would it be possible to add codespace support to hackingbuddygpt in a way, that only spawns a single container (maybe with the suid/sudo use-case) and starts hackingBuddyGPT against that container? That might be the 'easiest' show-case/use-case for a new user.

**Steps**
1. Go to https://github.com/ipa-lab/hackingBuddyGPT
2. Click the "Code" button.
3. Click the "Codespaces" tab.
4. Click the "Create codespace on main" button.
5. Wait for Codespaces to start — This may take upwards of 10 minutes.

> Setting up remote connection: Building codespace...

6. After Codespaces started, you may need to restart a new Terminal via the Command Palette:

Press the key combination:

> `⇧⌘P` `Shift+Command+P` (Mac) / `Ctrl+Shift+P` (Windows/Linux)

In the Command Palette, type `>` and `Terminal: Create New Terminal` and press the return key.

7. You should see a new terminal similar to the following:

> 👋 Welcome to Codespaces! You are on our default image.
>
>    `-` It includes runtimes and tools for Python, Node.js, Docker, and more. See the full list here: https://aka.ms/ghcs-default-image
>
>    `-` Want to use a custom image instead? Learn more here: https://aka.ms/configure-codespace
>
> 🔍 To explore VS Code to its fullest, search using the Command Palette (Cmd/Ctrl + Shift + P or F1).
>
> 📝 Edit away, run your app as usual, and we'll automatically make it available for you to access.
>
> @github-username ➜ /workspaces/hackingBuddyGPT (main) $

Type the following to manually run:
```bash
./scripts/codespaces_start_hackingbuddygpt_against_a_container.sh
```
7. Eventually, you should see:

> Currently, May 2024, running hackingBuddyGPT with GPT-4-turbo against a benchmark containing 13 VMs (with maximum 20 tries per VM) cost around $5.
>
> Therefore, running hackingBuddyGPT with GPT-4-turbo against containing a container with maximum 10 tries would cost around $0.20.
>
> Enter your OpenAI API key and press the return key:

8. As requested, please enter your OpenAI API key and press the return key.

9. hackingBuddyGPT should start:

> Starting hackingBuddyGPT against a container...

10. If your OpenAI API key is *valid*, then you should see output similar to the following:

> [00:00:00] Starting turn 1 of 10
>
> Got command from LLM:
>
> …
>
> [00:01:00] Starting turn 10 of 10
>
> …
>
> Run finished
>
> maximum turn number reached

11. If your OpenAI API key is *invalid*, then you should see output similar to the following:

> [00:00:00] Starting turn 1 of 10
>
> Traceback (most recent call last):
>
> …
>
> Exception: Error from OpenAI Gateway (401

12. Alternatively, use Google Gemini instead of OpenAI

**Preqrequisites:**

```bash
python -m venv venv
```

```bash
source ./venv/bin/activate
```

```bash
pip install -e .
```

**Use gemini-openai-proxy and Gemini:**

http://localhost:8080 is gemini-openai-proxy

`gpt-4` maps to `gemini-1.5-flash-latest`

Hence use `gpt-4` below in `--llm.model=gpt-4`

Gemini free tier has a limit of 15 requests per minute, and 1500 requests per day

Hence `--max_turns 999999999` will exceed the daily limit

**Run gemini-openai-proxy**

```bash
docker run --restart=unless-stopped -it -d -p 8080:8080 --name gemini zhu327/gemini-openai-proxy:latest
```

**Manually enter your GEMINI_API_KEY value based on** https://aistudio.google.com/app/apikey

```bash
export GEMINI_API_KEY=
```

**Starting hackingBuddyGPT against a container...**

```bash
wintermute LinuxPrivesc --llm.api_key=$GEMINI_API_KEY --llm.model=gpt-4 --llm.context_size=1000000 --conn.host=192.168.122.151 --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1 --llm.api_url=http://localhost:8080 --llm.api_backoff=60 --max_turns 999999999
```

**Google AI Studio: Gemini free tier has a limit of 15 requests per minute, and 1500 requests per day:**

https://ai.google.dev/pricing#1_5flash

> Gemini 1.5 Flash
>
> The Gemini API “free tier” is offered through the API service with lower rate limits for testing purposes. Google AI Studio usage is completely free in all available countries.
>
> Rate Limits
>
> 15 RPM (requests per minute)
>
> 1 million TPM (tokens per minute)
>
> 1,500 RPD (requests per day)
>
> Used to improve Google's products
>
> Yes

https://ai.google.dev/gemini-api/terms#data-use-unpaid

> How Google Uses Your Data
>
> When you use Unpaid Services, including, for example, Google AI Studio and the unpaid quota on Gemini API, Google uses the content you submit to the Services and any generated responses to provide, improve, and develop Google products and services and machine learning technologies, including Google's enterprise features, products, and services, consistent with our Privacy Policy https://policies.google.com/privacy
>
> To help with quality and improve our products, human reviewers may read, annotate, and process your API input and output. Google takes steps to protect your privacy as part of this process. This includes disconnecting this data from your Google Account, API key, and Cloud project before reviewers see or annotate it. **Do not submit sensitive, confidential, or personal information to the Unpaid Services.**

**README.md and Disclaimers:**

https://github.com/ipa-lab/hackingBuddyGPT/blob/main/README.md

**Please refer to [README.md](https://github.com/ipa-lab/hackingBuddyGPT/blob/main/README.md) for all disclaimers.**

Please note and accept all of them.

**References:**
* https://docs.github.com/en/codespaces
* https://docs.github.com/en/codespaces/getting-started/quickstart
* https://docs.github.com/en/codespaces/reference/using-the-vs-code-command-palette-in-codespaces
* https://openai.com/api/pricing/
* https://platform.openai.com/docs/quickstart
* https://platform.openai.com/api-keys
* https://ai.google.dev/gemini-api/docs/ai-studio-quickstart
* https://aistudio.google.com/
* https://aistudio.google.com/app/apikey
* https://ai.google.dev/
* https://ai.google.dev/gemini-api/docs/api-key
* https://github.com/zhu327/gemini-openai-proxy
* https://hub.docker.com/r/zhu327/gemini-openai-proxy
