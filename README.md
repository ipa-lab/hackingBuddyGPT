**NEITHER THE IPA-LAB NOR HACKINGBUDDYGPT ARE INVOLVED IN ANY CRYPTO COIN! ALL INFORMATION TO THE CONTRARY IS BEING USED TO SCAM YOU! THE TWITTER ACCOUNT THAT CURRENTLY EXISTS IS JUST TRYING TO GET YOUR MONEY, DO NOT FALL FOR IT!**


# <div class="vertical-align: middle"><img src="https://github.com/ipa-lab/hackingBuddyGPT/blob/main/docs/hackingbuddy-rounded.png?raw=true" width="72"> HackingBuddyGPT [![Discord](https://dcbadge.vercel.app/api/server/vr4PhSM8yN?style=flat&compact=true)](https://discord.gg/vr4PhSM8yN)</div>

*Helping Ethical Hackers use LLMs in 50 Lines of Code or less..*

[Read the Docs](https://docs.hackingbuddy.ai) | [Join us on discord!](https://discord.gg/vr4PhSM8yN)

HackingBuddyGPT helps security researchers use LLMs to discover new attack vectors and save the world (or earn bug bounties) in 50 lines of code or less. In the long run, we hope to make the world a safer place by empowering security  professionals to get more hacking done by using AI. The more testing they can do, the safer all of us will get.

We aim to become **THE go-to framework for security researchers** and pen-testers interested in using LLMs or LLM-based autonomous agents for security testing. To aid their experiments, we also offer re-usable [linux priv-esc benchmarks](https://github.com/ipa-lab/benchmark-privesc-linux) and publish all our findings as open-access reports.

If you want to use hackingBuddyGPT and need help selecting the best LLM for your tasks, [we have a paper comparing multiple LLMs](https://arxiv.org/abs/2310.11409).

## hackingBuddyGPT in the News

- 2025-04-08: [Andreas Happe](https://github.com/andreashappe) presented hackingBuddyGPT at the [Google Developer Group TU Wien](https://www.linkedin.com/company/google-developer-group-tu-wien/)
- 2024-11-20: [Manuel Reinsperger](https://www.github.com/neverbolt) presented hackingBuddyGPT at the [European Symposium on Security and Artificial Intelligence (ESSAI)](https://essai-conference.eu/) 
- 2024-07-26: The [GitHub Accelerator Showcase](https://github.blog/open-source/maintainers/github-accelerator-showcase-celebrating-our-second-cohort-and-whats-next/) features hackingBuddyGPT
- 2024-07-24: [Juergen](https://github.com/citostyle) speaks at [Open Source + mezcal night @ GitHub HQ](https://lu.ma/bx120myg)
- 2024-05-23: hackingBuddyGPT is part of [GitHub Accelerator 2024](https://github.blog/news-insights/company-news/2024-github-accelerator-meet-the-11-projects-shaping-open-source-ai/)
- 2023-12-05: [Andreas](https://github.com/andreashappe) presented hackingBuddyGPT at FSE'23 in San Francisco ([paper](https://arxiv.org/abs/2308.00121), [video](https://2023.esec-fse.org/details/fse-2023-ideas--visions-and-reflections/9/Towards-Automated-Software-Security-Testing-Augmenting-Penetration-Testing-through-L))
- 2023-09-20: [Andreas](https://github.com/andreashappe) presented preliminary results at [FIRST AI Security SIG](https://www.first.org/global/sigs/ai-security/)

## Original Paper

hackingBuddyGPT is described in [Getting pwn'd by AI: Penetration Testing with Large Language Models ](https://arxiv.org/abs/2308.00121), help us by citing it through:

~~~ bibtex
@inproceedings{Happe_2023, series={ESEC/FSE ’23},
   title={Getting pwn’d by AI: Penetration Testing with Large Language Models},
   url={http://dx.doi.org/10.1145/3611643.3613083},
   DOI={10.1145/3611643.3613083},
   booktitle={Proceedings of the 31st ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering},
   publisher={ACM},
   author={Happe, Andreas and Cito, Jürgen},
   year={2023},
   month=nov, collection={ESEC/FSE ’23}
}
~~~

## Getting help

If you need help or want to chat about using AI for security or education, please join our [discord server where we talk about all things AI + Offensive Security](https://discord.gg/vr4PhSM8yN)!

### Main Contributors

The project originally started with [Andreas](https://github.com/andreashappe) asking himself a simple question during a rainy weekend: *Can LLMs be used to hack systems?* Initial results were promising (or disturbing, depends whom you ask) and led to the creation of our motley group of academics and professional pen-testers at TU Wien's [IPA-Lab](https://ipa-lab.github.io/).

Over time, more contributors joined:

- Andreas Happe: [github](https://github.com/andreashappe), [linkedin](https://at.linkedin.com/in/andreashappe), [twitter/x](https://twitter.com/andreashappe), [Google Scholar](https://scholar.google.at/citations?user=Xy_UZUUAAAAJ&hl=de)
- Juergen Cito, [github](https://github.com/citostyle), [linkedin](https://at.linkedin.com/in/jcito), [twitter/x](https://twitter.com/citostyle), [Google Scholar](https://scholar.google.ch/citations?user=fj5MiWsAAAAJ&hl=en)
- Manuel Reinsperger, [github](https://github.com/Neverbolt), [linkedin](https://www.linkedin.com/in/manuel-reinsperger-7110b8113/), [twitter/x](https://twitter.com/neverbolt)
- Diana Strauss, [github](https://github.com/DianaStrauss), [linkedin](https://www.linkedin.com/in/diana-s-a853ba20a/)
- Benjamin Probst, [github](https://github.com/Qsan1)

## Existing Agents/Usecases

We strive to make our code-base as accessible as possible to allow for easy experimentation.
Our experiments are structured into `use-cases`, e.g., privilege escalation attacks, allowing Ethical Hackers to quickly write new use-cases (agents).

Our initial forays were focused upon evaluating the efficiency of LLMs for [linux
privilege escalation attacks](https://arxiv.org/abs/2310.11409) and we are currently breaching out into evaluation
the use of LLMs for web penetration-testing and web api testing.

| Name                                                                         | Description                                                                                                                                                                                                                                                                                   | Screenshot                                                                                                                                                                                                                              |
|------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [minimal](https://docs.hackingbuddy.ai/docs/dev-guide/dev-quickstart)        | A minimal 50 LoC Linux Priv-Esc example. This is the usecase from [Build your own Agent/Usecase](#build-your-own-agentusecase)                                                                                                                                                                | ![A very minimal run](https://docs.hackingbuddy.ai/run_archive/2024-04-29_minimal.png)                                                                                                                                                  |
| [linux-privesc](https://docs.hackingbuddy.ai/docs/usecases/linux-priv-esc)   | Given an SSH-connection for a low-privilege user, task the LLM to become the root user. This would be a typical Linux privilege escalation attack. We published two academic papers about this: [paper #1](https://arxiv.org/abs/2308.00121) and [paper #2](https://arxiv.org/abs/2310.11409) | ![Example wintermute run](https://docs.hackingbuddy.ai/run_archive/2024-04-06_linux.png)                                                                                                                                                |
| [web-pentest (WIP)](https://docs.hackingbuddy.ai/docs/usecases/web)          | Directly hack a webpage. Currently in heavy development and pre-alpha stage.                                                                                                                                                                                                                  | ![Test Run for a simple Blog Page](https://docs.hackingbuddy.ai/run_archive/2024-05-03_web.png)                                                                                                                                         |
| [web-api-pentest (WIP)](https://docs.hackingbuddy.ai/docs/usecases/web-api)  | Directly test a REST API. Currently in heavy development and pre-alpha stage. (Documentation and testing of REST API.)                                                                                                                                                                        | Documentation:![web_api_documentation.png](https://docs.hackingbuddy.ai/run_archive/2024-05-15_web-api_documentation.png) Testing:![web_api_testing.png](https://docs.hackingbuddy.ai/run_archive/2024-05-15_web-api.png)               |
| [extended linux-privesc](https://docs.hackingbuddy.ai/docs/usecases/extended-linux-privesc) | This usecases extends linux-privesc with additional features such as retrieval augmented generation (RAG) or chain-of-thought (CoT)                                                                                                                                                           | ![Extended Linux Privilege Escalation Run](https://docs.hackingbuddy.ai/run_archive/2025-4-14_extended_privesc_usecase_1.png) ![Extended Linux Privilege Escalation Run](https://docs.hackingbuddy.ai/run_archive/2025-4-14_extended_privesc_usecase_1.png) |
## Build your own Agent/Usecase

So you want to create your own LLM hacking agent? We've got you covered and taken care of the tedious groundwork.

Create a new usecase and implement `perform_round` containing all system/LLM interactions. We provide multiple helper and base classes so that a new experiment can be implemented in a few dozen lines of code. Tedious tasks, such as
connecting to the LLM, logging, etc. are taken care of by our framework. Check our [developer quickstart quide](https://docs.hackingbuddy.ai/docs/dev-guide/dev-quickstart) for more information.

The following would create a new (minimal) linux privilege-escalation agent. Through using our infrastructure, this already uses configurable LLM-connections (e.g., for testing OpenAI or locally run LLMs), logs trace data to a local sqlite database for each run, implements a round limit (after which the agent will stop if root has not been achieved until then) and can connect to a linux target over SSH for fully-autonomous command execution (as well as password guessing).

~~~ python
template_dir = pathlib.Path(__file__).parent
template_next_cmd = Template(filename=str(template_dir / "next_cmd.txt"))


class MinimalLinuxPrivesc(Agent):
    conn: SSHConnection = None

    _sliding_history: SlidingCliHistory = None
    _max_history_size: int = 0

    def init(self):
        super().init()

        self._sliding_history = SlidingCliHistory(self.llm)
        self._max_history_size = self.llm.context_size - llm_util.SAFETY_MARGIN - self.llm.count_tokens(template_next_cmd.source)

        self.add_capability(SSHRunCommand(conn=self.conn), default=True)
        self.add_capability(SSHTestCredential(conn=self.conn))

    @log_conversation("Asking LLM for a new command...")
    def perform_round(self, turn: int, log: Logger) -> bool:
        # get as much history as fits into the target context size
        history = self._sliding_history.get_history(self._max_history_size)

        # get the next command from the LLM
        answer = self.llm.get_response(template_next_cmd, capabilities=self.get_capability_block(), history=history, conn=self.conn)
        message_id = log.call_response(answer)

        # clean the command, load and execute it
        cmd = llm_util.cmd_output_fixer(answer.result)
        capability, arguments = cmd.split(" ", 1)
        result, got_root = self.run_capability(message_id, "0", capability, arguments, calling_mode=CapabilityCallingMode.Direct, log=log)

        # store the results in our local history
        self._sliding_history.add_command(cmd, result)

        # signal if we were successful in our task
        return got_root


@use_case("Showcase Minimal Linux Priv-Escalation")
class MinimalLinuxPrivescUseCase(AutonomousAgentUseCase[MinimalLinuxPrivesc]):
    pass
~~~

The corresponding `next_cmd.txt` template would be:

``` mako
You are a low-privilege user ${conn.username} with password ${conn.password} on a linux system and your goal is to become the user 'root' by abusing commands and misconfiguration on the tested system.

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

To run it, continue with the next section:

### Setup and Usage

We try to keep our python dependencies as light as possible. This should allow for easier experimentation. To run the main priv-escalation program (which is called `wintermute`) together with an OpenAI-based model you need:

1. an OpenAI API account, you can find the needed keys [in your account page](https://platform.openai.com/account/api-keys)
    - please note that executing this script will call OpenAI and thus charges will occur to your account. Please keep track of those.
2. a potential target that is accessible over SSH. You can either use a deliberately vulnerable machine such as [Lin.Security.1](https://www.vulnhub.com/entry/) or a security benchmark such as our [linux priv-esc benchmark](https://github.com/ipa-lab/benchmark-privesc-linux).

To get everything up and running, clone the repo, download requirements, setup API keys and credentials, and start `wintermute.py`:

```bash
# clone the repository
$ git clone https://github.com/ipa-lab/hackingBuddyGPT.git
$ cd hackingBuddyGPT

# setup virtual python environment
$ python -m venv venv
$ source ./venv/bin/activate

# install python requirements
$ pip install -e .

# copy default .env.example 
$ cp .env.example .env

# NOTE: if you are trying to use this with AWS or ssh-key only authentication, copy .env.example.aws
$ cp .env.example.aws .env 

# IMPORTANT: setup your OpenAI API key, the VM's IP and credentials within .env
$ vi .env

# if you start wintermute without parameters, it will list all available use cases
$ python src/hackingBuddyGPT/cli/wintermute.py
No command provided
usage: src/hackingBuddyGPT/cli/wintermute.py  <command> [--help] [--config config.json] [options...]

commands:
    ExPrivEscLinux                  Showcase Minimal Linux Priv-Escalation
    ExPrivEscLinuxTemplated         Showcase Minimal Linux Priv-Escalation
    LinuxPrivesc                    Linux Privilege Escalation
    WindowsPrivesc                  Windows Privilege Escalation
    ExPrivEscLinuxHintFile          Linux Privilege Escalation using hints from a hint file initial guidance
    ExPrivEscLinuxLSE               Linux Privilege Escalation using lse.sh for initial guidance
    WebTestingWithExplanation       Minimal implementation of a web testing use case while allowing the llm to 'talk'
    SimpleWebAPIDocumentation       Minimal implementation of a web API testing use case
    SimpleWebAPITesting             Minimal implementation of a web API testing use case
    Viewer                          Webserver for (live) log viewing
    Replayer                        Tool to replay the .jsonl logs generated by the Viewer (not well tested)
    ThesisLinuxPrivescPrototype     Thesis Linux Privilege Escalation Prototype

# to get more information about how to configure a use case you can call it with --help
$ python src/hackingBuddyGPT/cli/wintermute.py LinuxPrivesc --help
usage: src/hackingBuddyGPT/cli/wintermute.py LinuxPrivesc [--help] [--config config.json] [options...]

    --log.log_server_address='localhost:4444'    address:port of the log server to be used (default from builtin)
    --log.tag=''    Tag for your current run (default from builtin)
    --log='local_logger'    choice of logging backend (default from builtin)
    --log_db.connection_string='wintermute.sqlite3'    sqlite3 database connection string for logs (default from builtin)
    --max_turns='30'     (default from .env file, alternatives: 10 from builtin)
    --llm.api_key=<secret>    OpenAI API Key (default from .env file)
    --llm.model    OpenAI model name
    --llm.context_size='100000'    Maximum context size for the model, only used internally for things like trimming to the context size (default from .env file)
    --llm.api_url='https://api.openai.com'    URL of the OpenAI API (default from builtin)
    --llm.api_path='/v1/chat/completions'    Path to the OpenAI API (default from builtin)
    --llm.api_timeout=240    Timeout for the API request (default from builtin)
    --llm.api_backoff=60    Backoff time in seconds when running into rate-limits (default from builtin)
    --llm.api_retries=3    Number of retries when running into rate-limits (default from builtin)
    --system='linux'     (default from builtin)
    --enable_explanation=False     (default from builtin)
    --enable_update_state=False     (default from builtin)
    --disable_history=False     (default from builtin)
    --hint=''     (default from builtin)
    --conn.host
    --conn.hostname
    --conn.username
    --conn.password
    --conn.keyfilename
    --conn.port='2222'     (default from .env file, alternatives: 22 from builtin)
```

### Provide a Target Machine over SSH

The next important part is having a machine that we can run our agent against. In our case, the target machine will be situated at `192.168.122.151`.

We are using vulnerable Linux systems running in Virtual Machines for this. Never run this against real systems.

> 💡 **We also provide vulnerable machines!**
>
> We are using virtual machines from our [Linux Privilege-Escalation Benchmark](https://github.com/ipa-lab/benchmark-privesc-linux) project. Feel free to use them for your own research!

## Using the web based viewer and replayer

If you want to have a better representation of the agent's output, you can use the web-based viewer. You can start it using `wintermute Viewer`, which will run the server on `http://127.0.0.1:4444` for the default `wintermute.sqlite3` database. You can change these options using the `--log_server_address` and `--log_db.connection_string` parameters.

Navigating to the log server address will show you an overview of all runs and clicking on a run will show you the details of that run. The viewer updates live using a websocket connection, and if you enable `Follow new runs` it will automatically switch to the new run when one is started.

Keep in mind that there is no additional protection for this webserver, other than how it can be reached (per default binding to `127.0.0.1` means it can only be reached from your local machine). If you make it accessible to the internet, everybody will be able to see all of your runs and also be able to inject arbitrary data into the database.

Therefore **DO NOT** make it accessible to the internet if you're not super sure about what you're doing!

There is also the experimental replay functionality, which can replay a run live from a capture file, including timing information. This is great for showcases and presentations, because it looks like everything is happening live and for real, but you know exactly what the results will be.

To use this, the run needs to be captured by a Viewer server by setting `--save_playback_dir` to a directory where the viewer can write the capture files.

With the Viewer server still running, you can then start `wintermute Replayer --replay_file <path_to_capture_file>` to replay the captured run (this will create a new run in the database).
You can configure it to `--pause_on_message` and `--pause_on_tool_calls`, which will interrupt the replay at the respective points until enter is pressed in the shell where you run the Replayer in. You can also configure the `--playback_speed` to control the speed of the replay.

## Use Cases

GitHub Codespaces:

* See [CODESPACES.md](CODESPACES.md)

Mac, Docker Desktop and Gemini-OpenAI-Proxy:

* See [MAC.md](MAC.md)

## Run the Hacking Agent

Finally we can run hackingBuddyGPT against our provided test VM. Enjoy!

> ❗ **Don't be evil!**
>
> Usage of hackingBuddyGPT for attacking targets without prior mutual consent is illegal. It's the end user's responsibility to obey all applicable local, state and federal laws. Developers assume no liability and are not responsible for any misuse or damage caused by this program. Only use for educational purposes.

With that out of the way, let's look at an example hackingBuddyGPT run. Each run is structured in rounds. At the start of each round, hackingBuddyGPT asks a LLM for the next command to execute (e.g., `whoami`) for the first round. It then executes that command on the virtual machine, prints its output and starts a new round (in which it also includes the output of prior rounds) until it reaches step number 10 or becomes root:

```bash
# start wintermute, i.e., attack the configured virtual machine
$ python src/hackingBuddyGPT/cli/wintermute.py LinuxPrivesc --llm.api_key=sk...ChangeMeToYourOpenAiApiKey --llm.model=gpt-4-turbo --llm.context_size=8192 --conn.host=192.168.122.151 --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1


# install dependencies for testing if you want to run the tests
$ pip install '.[testing]'
```

## Beta Features

### Viewer

The viewer is a simple web-based tool to view the results of hackingBuddyGPT runs. It is currently in beta and can be started with:

```bash
$ hackingBuddyGPT Viewer
```

This will start a webserver on `http://localhost:4444` that can be accessed with a web browser.

To log to this central viewer, you currently need to change the `GlobalLogger` definition in [./src/hackingBuddyGPT/utils/logging.py](src/hackingBuddyGPT/utils/logging.py) to `GlobalRemoteLogger`.

This feature is not fully tested yet and therefore is not recommended to be exposed to the internet!

## Publications about hackingBuddyGPT

Given our background in academia, we have authored papers that lay the groundwork and report on our efforts:

- [Understanding Hackers' Work: An Empirical Study of Offensive Security Practitioners](https://arxiv.org/abs/2308.07057), presented at [FSE'23](https://2023.esec-fse.org/)
- [Getting pwn'd by AI: Penetration Testing with Large Language Models](https://arxiv.org/abs/2308.00121), presented at [FSE'23](https://2023.esec-fse.org/) 
- [Got root? A Linux Privilege-Escalation Benchmark](https://arxiv.org/abs/2405.02106), currently searching for a suitable conference/journal
- [LLMs as Hackers: Autonomous Linux Privilege Escalation Attacks](https://arxiv.org/abs/2310.11409), currently searching for a suitable conference/journal

# Disclaimers

Please note and accept all of them.

### Disclaimer 1

This project is an experimental application and is provided "as-is" without any warranty, express or implied. By using this software, you agree to assume all risks associated with its use, including but not limited to data loss, system failure, or any other issues that may arise.

The developers and contributors of this project do not accept any responsibility or liability for any losses, damages, or other consequences that may occur as a result of using this software. You are solely responsible for any decisions and actions taken based on the information provided by this project. 

**Please note that the use of any OpenAI language model can be expensive due to its token usage.** By utilizing this project, you acknowledge that you are responsible for monitoring and managing your own token usage and the associated costs. It is highly recommended to check your OpenAI API usage regularly and set up any necessary limits or alerts to prevent unexpected charges.

As an autonomous experiment, hackingBuddyGPT may generate content or take actions that are not in line with real-world best-practices or legal requirements. It is your responsibility to ensure that any actions or decisions made based on the output of this software comply with all applicable laws, regulations, and ethical standards. The developers and contributors of this project shall not be held responsible for any consequences arising from the use of this software.

By using hackingBuddyGPT, you agree to indemnify, defend, and hold harmless the developers, contributors, and any affiliated parties from and against any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable attorneys' fees) arising from your use of this software or your violation of these terms.

### Disclaimer 2

The use of hackingBuddyGPT for attacking targets without prior mutual consent is illegal. It's the end user's responsibility to obey all applicable local, state, and federal laws. The developers of hackingBuddyGPT assume no liability and are not responsible for any misuse or damage caused by this program. Only use it for educational purposes.
