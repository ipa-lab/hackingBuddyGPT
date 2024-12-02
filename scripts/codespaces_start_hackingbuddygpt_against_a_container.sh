#!/bin/bash

# Purpose: In GitHub Codespaces, start hackingBuddyGPT against a container
# Usage: ./scripts/codespaces_start_hackingbuddygpt_against_a_container.sh

# Enable strict error handling for better script robustness
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -o pipefail  # Return the exit status of the last command in a pipeline that failed
set -x  # Print each command before executing it (useful for debugging)

cd $(dirname $0)

# Check Bash version (adjust version as needed)
if [[ ! $(bash --version | head -n1 | awk '{print $4}' | cut -d'.' -f1-2) =~ ^5\. ]]; then
  echo "Error: Requires Bash version 5 or higher." >&2
  exit 1
fi

# Step 1: Install prerequisites

# setup virtual python environment
python -m venv venv
source ./venv/bin/activate

# install python requirements
pip install -e .

# Step 2: Request an OpenAI API key

echo
echo 'Currently, May 2024, running hackingBuddyGPT with GPT-4-turbo against a benchmark containing 13 VMs (with maximum 20 tries per VM) cost around $5.'
echo
echo 'Therefore, running hackingBuddyGPT with GPT-4-turbo against containing a container with maximum 10 tries would cost around $0.20.'
echo
echo "Enter your OpenAI API key and press the return key:"
read OPENAI_API_KEY
echo

# Step 3: Start hackingBuddyGPT against a container

echo "Starting hackingBuddyGPT against a container..."
echo

wintermute LinuxPrivesc --llm.api_key=$OPENAI_API_KEY --llm.model=gpt-4-turbo --llm.context_size=8192 --conn.host=192.168.122.151 --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1
