#!/bin/bash

# Purpose: On a Mac, start hackingBuddyGPT against a container
# Usage: ./mac_start_hackingbuddygpt_against_a_container.sh

# Enable strict error handling for better script robustness
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -o pipefail  # Return the exit status of the last command in a pipeline that failed
set -x  # Print each command before executing it (useful for debugging)

# Step 1: Install prerequisites

# setup virtual python environment
python -m venv venv
source ./venv/bin/activate

# install python requirements
pip install -e .

# Step 2: Run Gemini-OpenAI-Proxy

docker --debug stop gemini-openai-proxy || true
docker --debug rm gemini-openai-proxy || true
docker --debug run --restart=unless-stopped -it -d -p 8080:8080 --name gemini-openai-proxy zhu327/gemini-openai-proxy:latest

# Step 3: Request a Gemini API key

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

# Step 4: Start hackingBuddyGPT against a container

echo "Starting hackingBuddyGPT against a container..."
echo

wintermute LinuxPrivesc --llm.api_key=$GEMINI_API_KEY --llm.model=gpt-4-turbo --llm.context_size=8192 --conn.host=127.0.0.1 --conn.port 49152 --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1 --llm.api_url=http://localhost:8080 --llm.api_backoff=60
