#!/bin/bash

# Purpose: On a Mac, start hackingBuddyGPT against a container
# Usage: ./scripts/mac_start_hackingbuddygpt_against_a_container.sh

# Enable strict error handling for better script robustness
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -o pipefail  # Return the exit status of the last command in a pipeline that failed
set -x  # Print each command before executing it (useful for debugging)

cd $(dirname $0)

# Check Bash version (adjust version as needed)
if [[ ! $(bash --version | head -n1 | awk '{print $4}' | cut -d'.' -f1-2) =~ ^3\. ]]; then
  echo "Error: Requires Bash version 3 or higher." >&2
  exit 1
fi

# Step 1: Install prerequisites

# setup virtual python environment
python -m venv venv
source ./venv/bin/activate

# install python requirements
pip install -e .

# Step 2: Request a Gemini API key

echo You can obtain a Gemini API key from the following URLs:
echo https://aistudio.google.com/
echo https://aistudio.google.com/app/apikey
echo

echo "Enter your Gemini API key and press the return key:"

# Check if GEMINI_API_KEY is set, prompt if not
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "Enter your Gemini API key and press the return key:"
    read -r GEMINI_API_KEY
else
    echo "Using existing GEMINI_API_KEY from environment."
fi

echo

# Step 3: Start hackingBuddyGPT against a container

echo "Starting hackingBuddyGPT against a container..."
echo

PORT=$(docker ps | grep ansible-ready-ubuntu | cut -d ':' -f2 | cut -d '-' -f1)

# Gemini free tier has a limit of 15 requests per minute, and 1500 requests per day
# Hence --max_turns 999999999 will exceed the daily limit

# http://localhost:8080 is genmini-openai-proxy

wintermute LinuxPrivesc --llm.api_key=$GEMINI_API_KEY --llm.model=gemini-1.5-flash-latest --llm.context_size=1000000 --conn.host=localhost --conn.port $PORT --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1 --llm.api_url=http://localhost:8080 --llm.api_backoff=60 --max_turns 999999999
