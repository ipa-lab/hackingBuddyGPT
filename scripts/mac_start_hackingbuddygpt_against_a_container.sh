#!/bin/bash

# Purpose: On a Mac, start hackingBuddyGPT against a container
# Usage: ./scripts/mac_start_hackingbuddygpt_against_a_container.sh

# Enable strict error handling for better script robustness
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -o pipefail  # Return the exit status of the last command in a pipeline that failed
set -x  # Print each command before executing it (useful for debugging)

cd $(dirname $0)

bash_version=$(/bin/bash --version | head -n 1 | awk '{print $4}' | cut -d. -f1)

if (( bash_version < 3 )); then
  echo 'Error: Requires Bash version 3 or higher.'
  exit 1
fi

# Step 1: Install prerequisites

# setup virtual python environment
cd ..
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

# http://localhost:8080 is gemini-openai-proxy

# gpt-4 maps to gemini-1.5-flash-latest

# https://github.com/zhu327/gemini-openai-proxy/blob/559085101f0ce5e8c98a94fb75fefd6c7a63d26d/README.md?plain=1#L146

#    | gpt-4 | gemini-1.5-flash-latest |

# https://github.com/zhu327/gemini-openai-proxy/blob/559085101f0ce5e8c98a94fb75fefd6c7a63d26d/pkg/adapter/models.go#L60-L61

# 	case strings.HasPrefix(openAiModelName, openai.GPT4):
# 		return Gemini1Dot5Flash

# Hence use gpt-4 below in --llm.model=gpt-4

# Gemini free tier has a limit of 15 requests per minute, and 1500 requests per day

# Hence --max_turns 999999999 will exceed the daily limit

wintermute LinuxPrivesc --llm.api_key=$GEMINI_API_KEY --llm.model=gpt-4 --llm.context_size=1000000 --conn.host=localhost --conn.port $PORT --conn.username=lowpriv --conn.password=trustno1 --conn.hostname=test1 --llm.api_url=http://localhost:8080 --llm.api_backoff=60 --max_turns 999999999
