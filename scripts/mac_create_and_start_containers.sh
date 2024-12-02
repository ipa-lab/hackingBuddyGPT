#!/opt/homebrew/bin/bash

# Purpose: Automates the setup of docker containers for local testing on Mac
# Usage: ./scripts/mac_create_and_start_containers.sh

# Enable strict error handling for better script robustness
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -o pipefail  # Return the exit status of the last command in a pipeline that failed
set -x  # Print each command before executing it (useful for debugging)

cd $(dirname $0)

bash_version=$(/opt/homebrew/bin/bash --version | head -n 1 | awk '{print $4}' | cut -d. -f1)

if (( bash_version < 4 )); then
  echo 'Error: Requires Bash version 4 or higher.'
  exit 1
fi

# Step 1: Initialization

if [ ! -f hosts.ini ]; then
    echo "hosts.ini not found! Please ensure your Ansible inventory file exists."
    exit 1
fi

if [ ! -f tasks.yaml ]; then
    echo "tasks.yaml not found! Please ensure your Ansible playbook file exists."
    exit 1
fi

# Default values for network and base port, can be overridden by environment variables
DOCKER_NETWORK_NAME=${DOCKER_NETWORK_NAME:-192_168_65_0_24}
DOCKER_NETWORK_SUBNET="192.168.65.0/24"
BASE_PORT=${BASE_PORT:-49152}

# Step 2: Define helper functions

# Function to find an available port
find_available_port() {
    local base_port="$1"
    local port=$base_port
    local max_port=65535
    while lsof -i :$port; do 
        port=$((port + 1))
        if [ "$port" -gt "$max_port" ]; then
            echo "No available ports in the range $base_port-$max_port." >&2
            exit 1
        fi
    done
    echo $port
}

# Function to generate SSH key pair
generate_ssh_key() {
    ssh-keygen -t rsa -b 4096 -f ./mac_ansible_id_rsa -N '' -q <<< y
    echo "New SSH key pair generated."
    chmod 600 ./mac_ansible_id_rsa
}

# Function to create and start docker container with SSH enabled
start_container() {
    local container_name="$1"
    local port="$2"
    local image_name="ansible-ready-ubuntu"

    if docker --debug ps -aq -f name=${container_name}; then
        echo "Container ${container_name} already exists. Removing it..." >&2
        docker --debug stop ${container_name} || true
        docker --debug rm ${container_name} || true
    fi

    echo "Starting docker container ${container_name} on port ${port}..." >&2

    # Uncomment the following line to use a custom Docker network
    # docker --debug run --restart=unless-stopped -it -d --network ${DOCKER_NETWORK_NAME} -p "${port}:22" --name ${container_name} -h ${container_name} ${image_name}
    # The line is commented out because of the bugs in Docker Desktop on Mac causing hangs

    # Alternatively, start Docker container with SSH enabled on localhost without using a custom Docker network
    docker --debug run --restart=unless-stopped -it -d -p "${port}:22" --name ${container_name} -h ${container_name} ${image_name}

    # Retrieve the IP address assigned by Docker
    container_ip=$(docker --debug inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$container_name")

    # Verify that container_ip is not empty
    if [ -z "$container_ip" ]; then
        echo "Error: Could not retrieve IP address for container $container_name." >&2
        exit 1
    fi

    echo "Container ${container_name} started with IP ${container_ip} and port ${port}."

    # Copy SSH public key to container
    docker --debug cp ./mac_ansible_id_rsa.pub ${container_name}:/home/ansible/.ssh/authorized_keys
    docker --debug exec ${container_name} chown ansible:ansible /home/ansible/.ssh/authorized_keys
    docker --debug exec ${container_name} chmod 600 /home/ansible/.ssh/authorized_keys
}

# Function to check if SSH is ready on a container
check_ssh_ready() {
    local port="$1"
    ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ./mac_ansible_id_rsa -p ${port} ansible@localhost exit 2>/dev/null
    return $?
}

# Step 3: Verify docker Desktop

echo "Checking if docker Desktop is running..."
if ! docker --debug info; then
    echo If the above says
    echo
    echo "Server:"
    echo "ERROR: request returned Internal Server Error for API route and version http://%2FUsers%2Fusername%2F.docker%2Frun%2Fdocker.sock/v1.47/info, check if the server supports the requested API version"
    echo "errors pretty printing info"
    echo
    echo You may need to uninstall Docker Desktop https://docs.docker.com/desktop/uninstall/ and reinstall it from https://docs.docker.com/desktop/setup/install/mac-install/ and try again.
    echo
    echo Alternatively, restart Docker Desktop and try again.
    echo
    echo There are known issues with Docker Desktop on Mac, such as:
    echo
    echo Bug: Docker CLI Hangs for all commands
    echo https://github.com/docker/for-mac/issues/6940
    echo
    echo Regression: Docker does not recover from resource saver mode
    echo https://github.com/docker/for-mac/issues/6933
    echo
    echo "Docker Desktop is not running. Please start Docker Desktop and try again."
    echo
    exit 1
fi

# Step 4: Install prerequisites

echo "Installing required Python packages..."
if ! command -v pip3 >/dev/null 2>&1; then
    echo "pip3 not found. Please install Python3 and pip3 first."
    exit 1
fi

echo "Installing Ansible and passlib using pip..."
pip3 install ansible passlib

# Step 5: Build docker image

echo "Building docker image with SSH enabled..."
if ! docker --debug build -t ansible-ready-ubuntu -f codespaces_create_and_start_containers.Dockerfile .; then
    echo "Failed to build docker image." >&2
    exit 1
fi

# Step 6: Create a custom docker network if it does not exist

# Commenting out this step because Docker bug and its regression that are clausing CLI to hang

# There is a Docker bug that prevents creating custom networks on MacOS because it hangs

# Bug: Docker CLI Hangs for all commands
# https://github.com/docker/for-mac/issues/6940

# Regression: Docker does not recover from resource saver mode
# https://github.com/docker/for-mac/issues/6933

# echo "Checking if the custom docker network '${DOCKER_NETWORK_NAME}' with subnet {DOCKER_NETWORK_SUBNET} exists"

# if ! docker --debug network inspect ${DOCKER_NETWORK_NAME} >/dev/null 2>&1; then
#     docker --debug network create --subnet="${DOCKER_NETWORK_SUBNET}" "${DOCKER_NETWORK_NAME}" || echo "Network creation failed, but continuing..."
# fi

# Unfortunately, the above just hangs like this:

# + echo 'Checking if the custom docker network '\''192_168_65_0_24'\'' with subnet {DOCKER_NETWORK_SUBNET} exists'
# Checking if the custom docker network '192_168_65_0_24' with subnet {DOCKER_NETWORK_SUBNET} exists
# + docker --debug network inspect 192_168_65_0_24
# + docker --debug network create --subnet=192.168.65.0/24 192_168_65_0_24

# (It hangs here)

# For now, the workaround is to use localhost as the IP address on a dynamic or private TCP port, such as 41952

# Step 7: Generate SSH key
generate_ssh_key

# Step 8: Create mac inventory file

echo "Creating mac Ansible inventory..."
cat > mac_ansible_hosts.ini << EOF
[local]
localhost ansible_port=PLACEHOLDER ansible_user=ansible ansible_ssh_private_key_file=./mac_ansible_id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

[all:vars]
ansible_python_interpreter=/usr/bin/python3
EOF

# Step 9: Start container and update inventory

available_port=$(find_available_port "$BASE_PORT")
start_container "ansible-ready-ubuntu" "$available_port"

# Update the port in the inventory file
sed -i '' "s/PLACEHOLDER/$available_port/" mac_ansible_hosts.ini

# Step 10: Wait for SSH service

echo "Waiting for SSH service to start..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if check_ssh_ready "$available_port"; then
        echo "SSH is ready!"
        break
    fi
    echo "Waiting for SSH to be ready (attempt $attempt/$max_attempts)..."
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "SSH service failed to start. Exiting."
    exit 1
fi

# Step 11: Create ansible.cfg

cat > mac_ansible.cfg << EOF
[defaults]
interpreter_python = auto_silent
host_key_checking = False
remote_user = ansible

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False
EOF

# Step 12: Set ANSIBLE_CONFIG and run playbook

export ANSIBLE_CONFIG=$(pwd)/mac_ansible.cfg

echo "Running Ansible playbook..."
ansible-playbook -i mac_ansible_hosts.ini tasks.yaml

echo "Setup complete. Container ansible-ready-ubuntu is ready for testing."

# Step 13: Run gemini-openai-proxy container

if docker --debug ps -aq -f name=gemini-openai-proxy; then
    echo "Container gemini-openai-proxy already exists. Removing it..." >&2
    docker --debug stop gemini-openai-proxy || true
    docker --debug rm gemini-openai-proxy || true
fi

docker --debug run --restart=unless-stopped -it -d -p 8080:8080 --name gemini-openai-proxy zhu327/gemini-openai-proxy:latest

# Step 14: Ready to run hackingBuddyGPT

echo "You can now run ./scripts/mac_start_hackingbuddygpt_against_a_container.sh"

exit 0
