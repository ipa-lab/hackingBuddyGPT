# HackingBuddyGPT

## About

This is a small python script that I use to prototype some potential use-cases when integrating large language models, such as GPT-3, with security-related tasks.

What is it doing? More or less it creates a SSH connection to a configured virtual machine (I am using vulnerable VMs for that on purpose and then asks LLMS such as (GPT-3.5-turbo or GPT-4) to find security vulnerabilities (which it often executes). Evicts a bit of an eerie feeling for me.

Current features:

- connects over SSH (linux targets) or SMB/PSExec (windows targets)
- supports multiple openai models (gpt-3.5-turbo, gpt4, gpt-3.5-turbo-16k, etc.)
- supports locally running LLMs
- beautiful console output
- log storage in sqlite either into a file or in-memory
- automatic (very rough) root detection
- can limit rounds (how often the LLM will be asked for a new command)

### Vision Paper

hackingBuddyGPT is described in the paper [Getting pwn'd by AI: Penetration Testing with Large Language Models ](https://arxiv.org/abs/2308.00121).

If you cite this repository/paper, please use:

~~~ bibtex
@inproceedings{getting_pwned,
author = {Happe, Andreas and Jürgen, Cito},
title = {Getting pwn’d by AI: Penetration Testing with Large Language Models},
year = {2023},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3611643.3613083},
doi = {10.1145/3611643.3613083},
booktitle = {Proceedings of the 31st ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering},
numpages = {5},
keywords = {machine learning, penetration testing},
location = {San Francisco, USA},
series = {ESEC/FSE 2023}
}
~~~

# Example runs

- more can be seen at [history notes](https://github.com/ipa-lab/hackingBuddyGPT/blob/main/docs/history_notes.md)

## updated version using GPT-4

This happened during a recent run:

![Example wintermute run](example_run_gpt4.png)

Some things to note:

- initially the current configuration is output. Yay, so many colors!
- "Got command from LLM" shows the generated command while the panel afterwards has the given command as title and the command's output as content.
- the table contains all executed commands. ThinkTime denotes the time that was needed to generate the command (Tokens show the token count for the prompt and its response). StateUpdTime shows the time that was needed to generate a new state (the next column also gives the token count)
- "What does the LLM know about the system?" gives an LLM generated list of system facts. To generate it, it is given the latest executed command (and it's output) as well as the current list of system facts. This is the operation which time/token usage is shown in the overview table as StateUpdTime/StateUpdTokens. As the state update takes forever, this is disabled by default and has to be enabled through a command line switch.
- Then the next round starts. The next given command (`sudo tar`) will lead to a pwn'd system BTW.

## High-Level Description

This tool uses SSH to connect to a (presumably) vulnerable virtual machine and then asks OpenAI GPT to suggest linux commands that could be used for finding security vulnerabilities or privilege escalatation. The provided command is then executed within the virtual machine, the output fed back to the LLM and, finally, a new command is requested from it..

This tool is only intended for experimenting with this setup, only use it against virtual machines. Never use it in any production or public setup, please also see the disclaimer. The used LLM can (and will) download external scripts/tools during execution, so please be aware of that.

## Setup

You'll need:

1. a vulnerable virtual machine, I am currenlty using [Lin.Security.1](https://www.vulnhub.com/entry/linsecurity-1,244/) as a target.
    - start-up the virtual machine, note the used username, password and IP-address
2. an OpenAI API account, you can find the needed keys [in your account page](https://platform.openai.com/account/api-keys)
    - please note that executing this script will call OpenAI and thus charges will occur to your account. Please keep track of those.

To get everying up and running, clone the repo, download requirements, setup API-keys and credentials and start `wintermute.py`:

~~~ bash
# clone the repository
$ git clone https://github.com/andreashappe/hackingBuddyGPT.git
$ cd hackingBuddyGPT

# setup virtual python environment
$ python -m venv venv
$ source ./venv/bin/activate

# install python requirements
$ pip install -r requirements.txt

# copy default .env.example
$ cp .env.example .env

# IMPORTANT: setup your OpenAI API key, the VM's IP and credentials within .env
$ vi .env
~~~

## Usage

It's just a simple python script, so..

~~~ bash
# start wintermute
$ python wintermute.py
~~~

## Overview of the script

It's quite minimal, see `wintermute.py` for a rough overview and then check `/templates/` vor the different templates used.

The script uses `fabric` to do the SSH-connection. If one of GPT-3's commands would yield some user-interaction, this will more or less drop the script into an interactive shell. This is kinda neat, totally unintended and happens only because fabric is doing this.

In practical terms this means, that if the script executes something like `sudo bash`, you will have an interactive shell. If it executes `vi file.txt`, you will be in an interactive shell. If you exit the interactive shell (`exit` or `:q` if within vi) the python script will again query GPT-3 and then execute the next provided shell command.

# Disclaimers

Please note and accept all of them.

### Disclaimer 1

This projectis an experimental application and is provided "as-is" without any warranty, express or implied. By using this software, you agree to assume all risks associated with its use, including but not limited to data loss, system failure, or any other issues that may arise.

The developers and contributors of this project do not accept any responsibility or liability for any losses, damages, or other consequences that may occur as a result of using this software. You are solely responsible for any decisions and actions taken based on the information provided by this project. 

**Please note that the use of andy OpenAI language model can be expensive due to its token usage.** By utilizing this project, you acknowledge that you are responsible for monitoring and managing your own token usage and the associated costs. It is highly recommended to check your OpenAI API usage regularly and set up any necessary limits or alerts to prevent unexpected charges.

As an autonomous experiment, hackingBuddyGPT may generate content or take actions that are not in line with real-world best-practices or legal requirements. It is your responsibility to ensure that any actions or decisions made based on the output of this software comply with all applicable laws, regulations, and ethical standards. The developers and contributors of this project shall not be held responsible for any consequences arising from the use of this software.

By using hackingBuddyGPT, you agree to indemnify, defend, and hold harmless the developers, contributors, and any affiliated parties from and against any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable attorneys' fees) arising from your use of this software or your violation of these terms.

### Disclaimer 2

Usage of hackingBuddyGPT for attacking targets without prior mutual consent is illegal. It's the end user's responsibility to obey all applicable local, state and federal laws. Developers assume no liability and are not responsible for any misuse or damage caused by this program. Only use for educational purposes.
