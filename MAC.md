## Use Case: Mac, Docker Desktop and Gemini-OpenAI-Proxy

**Docker Desktop runs containers in a virtual machine on Mac.**

**Run hackingBuddyGPT on Mac as follows:**

Target a localhost container ansible-ready-ubuntu

via Docker Desktop https://docs.docker.com/desktop/setup/install/mac-install/

and Gemini-OpenAI-Proxy https://github.com/zhu327/gemini-openai-proxy

There are bugs in Docker Desktop on Mac that prevent creation of a custom Docker network 192.168.65.0/24

Therefore, localhost TCP port 49152 (or higher) dynamic port number is used for an ansible-ready-ubuntu container

http://localhost:8080 is gemini-openai-proxy

gpt-4 maps to gemini-1.5-flash-latest

Hence use gpt-4 below in --llm.model=gpt-4

Gemini free tier has a limit of 15 requests per minute, and 1500 requests per day

Hence --max_turns 999999999 will exceed the daily limit

For example:

```zsh
export GEMINI_API_KEY=

export PORT=49152

wintermute LinuxPrivesc --llm.api_key=$GEMINI_API_KEY --llm.model=gpt-4 --llm.context_size=1000000 --conn.host=localhost --conn.port $PORT --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1 --llm.api_url=http://localhost:8080 --llm.api_backoff=60 --max_turns 999999999
```

The above example is consolidated into shell scripts with prerequisites as follows:

**Preqrequisite: Install Homebrew and Bash version 5:**

```zsh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Install Bash version 5 via Homebrew:**

```zsh
brew install bash
```

Bash version 4 or higher is needed for `scripts/mac_create_and_start_containers.sh`

Homebrew provides GNU Bash version 5 via license GPLv3+

Whereas Mac provides Bash version 3 via license GPLv2

**Create and start containers:**

```zsh
./scripts/mac_create_and_start_containers.sh
```

**Start hackingBuddyGPT against a container:**

```zsh
export GEMINI_API_KEY=
```

```zsh
./scripts/mac_start_hackingbuddygpt_against_a_container.sh
```

**Troubleshooting:**

**Docker Desktop: Internal Server Error**

```zsh
Server:
ERROR: request returned Internal Server Error for API route and version http://%2FUsers%2Fusername%2F.docker%2Frun%2Fdocker.sock/v1.47/info, check if the server supports the requested API version
errors pretty printing info
```

You may need to uninstall Docker Desktop https://docs.docker.com/desktop/uninstall/ and reinstall it from https://docs.docker.com/desktop/setup/install/mac-install/ and try again.

Alternatively, restart Docker Desktop and try again.

**There are known issues with Docker Desktop on Mac, such as:**

* Bug: Docker CLI Hangs for all commands
https://github.com/docker/for-mac/issues/6940

* Regression: Docker does not recover from resource saver mode
https://github.com/docker/for-mac/issues/6933

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
