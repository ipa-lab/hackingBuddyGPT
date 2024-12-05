# GitHub Codespaces support

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

**References**
* https://docs.github.com/en/codespaces
* https://docs.github.com/en/codespaces/getting-started/quickstart
* https://docs.github.com/en/codespaces/reference/using-the-vs-code-command-palette-in-codespaces
* https://openai.com/api/pricing/
* https://platform.openai.com/docs/quickstart
* https://platform.openai.com/api-keys
