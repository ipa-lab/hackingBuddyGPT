# Agent: LInux Privilege-Escalation Attacks

How are we doing this? The initial tool `wintermute` targets linux priv-esc attacks. It uses SSH to connect to a (presumably) vulnerable virtual machine and then asks OpenAI GPT to suggest linux commands that could be used for finding security vulnerabilities or privilege escalation. The provided command is then executed within the virtual machine, the output fed back to the LLM and, finally, a new command is requested from it..

## Current features (wintermute):

- connects over SSH (linux targets) or SMB/PSExec (windows targets)
- supports OpenAI REST-API compatible models (gpt-3.5-turbo, gpt4, gpt-3.5-turbo-16k, etc.)
- supports locally running LLMs
- beautiful console output
- logs run data through sqlite either into a file or in-memory
- automatic root detection
- can limit rounds (how often the LLM will be asked for a new command)

## Example run

This is a simple example run of `wintermute.py` using GPT-4 against a vulnerable VM. More example runs can be seen in [our collection of historic runs](docs/old_runs/old_runs.md).

![Example wintermute run](docs/example_run_gpt4.png)

Some things to note:

- initially the current configuration is output. Yay, so many colors!
- "Got command from LLM" shows the generated command while the panel afterwards has the given command as title and the command's output as content.
- the table contains all executed commands. ThinkTime denotes the time that was needed to generate the command (Tokens show the token count for the prompt and its response). StateUpdTime shows the time that was needed to generate a new state (the next column also gives the token count)
- "What does the LLM know about the system?" gives an LLM generated list of system facts. To generate it, it is given the latest executed command (and it's output) as well as the current list of system facts. This is the operation which time/token usage is shown in the overview table as StateUpdTime/StateUpdTokens. As the state update takes forever, this is disabled by default and has to be enabled through a command line switch.
- Then the next round starts. The next given command (`sudo tar`) will lead to a pwn'd system BTW.

## Publications on Priv-Esc Attacks using this Agent

Preliminary results for the linux privilege escalation use-case can be found in [Evaluating LLMs for Privilege-Escalation Scenarios](https://arxiv.org/abs/2310.11409):

~~~ bibtex
@misc{happe2024llms,
      title={LLMs as Hackers: Autonomous Linux Privilege Escalation Attacks}, 
      author={Andreas Happe and Aaron Kaplan and Jürgen Cito},
      year={2024},
      eprint={2310.11409},
      archivePrefix={arXiv},
      primaryClass={cs.CR}
}
~~~

This work is partially based upon our empiric research into [how hackers work](https://arxiv.org/abs/2308.07057):

~~~ bibtex
@inproceedings{Happe_2023, series={ESEC/FSE ’23},
   title={Understanding Hackers’ Work: An Empirical Study of Offensive Security Practitioners},
   url={http://dx.doi.org/10.1145/3611643.3613900},
   DOI={10.1145/3611643.3613900},
   booktitle={Proceedings of the 31st ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering},
   publisher={ACM},
   author={Happe, Andreas and Cito, Jürgen},
   year={2023},
   month=nov, collection={ESEC/FSE ’23}
}
~~~