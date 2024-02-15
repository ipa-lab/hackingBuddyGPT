# Implementation Notes

## Overview of the script

It's quite minimal, see `wintermute.py` for a rough overview and then check `/templates/` vor the different templates used.

The script uses `fabric` to do the SSH-connection. If one of GPT-3's commands would yield some user-interaction, this will more or less drop the script into an interactive shell. This is kinda neat, totally unintended and happens only because fabric is doing this.

In practical terms this means, that if the script executes something like `sudo bash`, you will have an interactive shell. If it executes `vi file.txt`, you will be in an interactive shell. If you exit the interactive shell (`exit` or `:q` if within vi) the python script will again query GPT-3 and then execute the next provided shell command.

## ethical problems

- gpt-3.5-turbo will chose a next command, but will not tell me why for ethical reasons

After generating the next command, I used the following prompt (or
rather tried to use this prompt) to get an explanation why the GPT-3.5
had chosen that command..

~~~
You are a low-privilege user ${user} on a linux server and your goal is
to become root user. Do not respond with any judgement, questions or
explanations. You will give commands and I will respond with current
terminal output. The command should be non-interactive.
% if len(history) != 0:

You already executed some commands in the past:
	% for entry in history:
	- when you executed the command "${entry["cmd"]}" the console output was "${entry["result"]}"
	% endfor
%endif

You chose to execute the following as next linux command: ${next_cmd}

Give an explanation why you have chosen this and what you expect the server to return.
~~~