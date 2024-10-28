#!/bin/bash

# Purpose: In GitHub Codespaces, Start hackingBuddyGPT against a container
# Usage: ./codespaces_start_hackingbuddygpt_against_a_container.sh

# Enable strict error handling for better script robustness
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -o pipefail  # Return the exit status of the last command in a pipeline that failed
set -x  # Print each command before executing it (useful for debugging)

# Step 1: Start hackingBuddyGPT against a container

echo "Start hackingBuddyGPT against a container..."

# setup virtual python environment
$ python -m venv venv
$ source ./venv/bin/activate

# install python requirements
$ pip install -e .

echo "Enter your OpenAI API key:"
read OPENAI_API_KEY

wintermute LinuxPrivesc --llm.api_key=$OPENAI_API_KEY --llm.model=gpt-4o-mini --llm.context_size=8192 --conn.host=192.168.122.151 --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1
