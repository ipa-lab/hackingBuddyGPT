#!/bin/bash

# Purpose: In GitHub Codespaces, automates the setup of Docker containers,
# preparation of Ansible inventory, and modification of tasks for testing.
# Usage: ./scripts/codespaces_create_and_start_containers.sh

# Enable strict error handling for better script robustness
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -o pipefail  # Return the exit status of the last command in a pipeline that failed
set -x  # Print each command before executing it (useful for debugging)

cd $(dirname $0)

bash_version=$(/bin/bash --version | head -n 1 | awk '{print $4}' | cut -d. -f1)

if (( bash_version < 4 )); then
  echo 'Error: Requires Bash version 4 or higher.'
  exit 1
fi

# Step 1: Initialization

if [ ! -f hosts.ini ]; then
    echo "hosts.ini not found! Please ensure your Ansible inventory file exists before running the script."
    exit 1
fi

if [ ! -f tasks.yaml ]; then
    echo "tasks.yaml not found! Please ensure your Ansible playbook file exists before running the script."
    exit 1
fi

# Default values for network and base port, can be overridden by environment variables
DOCKER_NETWORK_NAME=${DOCKER_NETWORK_NAME:-192_168_122_0_24}
DOCKER_NETWORK_SUBNET="192.168.122.0/24"
BASE_PORT=${BASE_PORT:-49152}

# Step 2: Define helper functions

# Function to find an available port starting from a base port
find_available_port() {
    local base_port="$1"
    local port=$base_port
    local max_port=65535
    while ss -tuln | grep -q ":$port "; do
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
    ssh-keygen -t rsa -b 4096 -f ./codespaces_ansible_id_rsa -N '' -q <<< y
    echo "New SSH key pair generated."
    chmod 600 ./codespaces_ansible_id_rsa
}

# Function to create and start Docker container with SSH enabled
start_container() {
    local container_name="$1"
    local base_port="$2"
    local container_ip="$3"
    local image_name="ansible-ready-ubuntu"

    if [ "$(docker ps -aq -f name=${container_name})" ]; then
        echo "Container ${container_name} already exists. Removing it..." >&2
        docker stop ${container_name} > /dev/null 2>&1 || true
        docker rm ${container_name} > /dev/null 2>&1 || true
    fi

    echo "Starting Docker container ${container_name} with IP ${container_ip} on port ${base_port}..." >&2
    docker run -d --name ${container_name} -h ${container_name} --network ${DOCKER_NETWORK_NAME} --ip ${container_ip} -p "${base_port}:22" ${image_name} > /dev/null 2>&1
    
    # Copy SSH public key to container
    docker cp ./codespaces_ansible_id_rsa.pub ${container_name}:/home/ansible/.ssh/authorized_keys
    docker exec ${container_name} chown ansible:ansible /home/ansible/.ssh/authorized_keys
    docker exec ${container_name} chmod 600 /home/ansible/.ssh/authorized_keys

    echo "${container_ip}"
}

# Function to check if SSH is ready on a container
check_ssh_ready() {
    local container_ip="$1"
    timeout 1 ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ./codespaces_ansible_id_rsa ansible@${container_ip} exit 2>/dev/null
    return $?
}

# Function to replace IP address and add Ansible configuration
replace_ip_and_add_config() {
    local original_ip="$1"
    local container_name="${original_ip//./_}"

    # Find an available port for the container
    local available_port=$(find_available_port "$BASE_PORT")

    # Start the container with the available port
    local container_ip=$(start_container "$container_name" "$available_port" "$original_ip")

    # Replace the original IP with the new container IP and add Ansible configuration
    sed -i "s/^[[:space:]]*$original_ip[[:space:]]*$/$container_ip ansible_user=ansible ansible_ssh_private_key_file=.\/codespaces_ansible_id_rsa ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=\/dev\/null'/" codespaces_ansible_hosts.ini

    echo "Started container ${container_name} with IP ${container_ip}, mapped to host port ${available_port}"
    echo "Updated IP ${original_ip} to ${container_ip} in codespaces_ansible_hosts.ini"

    # Increment BASE_PORT for the next container
    BASE_PORT=$((available_port + 1))
}

# Step 3: Update and install prerequisites

echo "Updating package lists..."

# Install prerequisites and set up Docker
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Step 4: Set up Docker repository and install Docker components

echo "Adding Docker's official GPG key..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Updating package lists again..."
sudo apt-get update

echo "Installing Moby components (moby-engine, moby-cli, moby-tini)..."
sudo apt-get install -y moby-engine moby-cli moby-tini moby-containerd

# Step 5: Start Docker and containerd services

echo "Starting Docker daemon using Moby..."
sudo service docker start || true
sudo service containerd start || true

# Step 6: Wait for Docker to be ready

echo "Waiting for Docker to be ready..."
timeout=60
while ! sudo docker info >/dev/null 2>&1; do
    if [ $timeout -le 0 ]; then
        echo "Timed out waiting for Docker to start."
        sudo service docker status || true
        echo "Docker daemon logs:"
        sudo cat /var/log/docker.log || true
        exit 1
    fi
    echo "Waiting for Docker to be available... ($timeout seconds left)"
    timeout=$(($timeout - 1))
    sleep 1
done

echo "Docker (Moby) is ready."

# Step 7: Install Python packages and Ansible

echo "Verifying Docker installation..."
docker --version
docker info

echo "Installing other required packages..."
sudo apt-get install -y python3 python3-pip sshpass

echo "Installing Ansible and passlib using pip..."
pip3 install ansible passlib

# Step 8: Build Docker image with SSH enabled

echo "Building Docker image with SSH enabled..."
if ! docker build -t ansible-ready-ubuntu -f codespaces_create_and_start_containers.Dockerfile .; then
    echo "Failed to build Docker image." >&2
    exit 1
fi

# Step 9: Create a custom Docker network if it does not exist

echo "Checking if the custom Docker network '${DOCKER_NETWORK_NAME}' with subnet 192.168.122.0/24 exists..."

if ! docker network inspect ${DOCKER_NETWORK_NAME} >/dev/null 2>&1; then
    docker network create --subnet="${DOCKER_NETWORK_SUBNET}" "${DOCKER_NETWORK_NAME}" || echo "Network creation failed, but continuing..."
fi

# Generate SSH key
generate_ssh_key

# Step 10: Copy hosts.ini to codespaces_ansible_hosts.ini and update IP addresses

echo "Copying hosts.ini to codespaces_ansible_hosts.ini and updating IP addresses..."

# Copy hosts.ini to codespaces_ansible_hosts.ini
cp hosts.ini codespaces_ansible_hosts.ini

# Read hosts.ini to get IP addresses and create containers
current_group=""
while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ ^\[(.+)\] ]]; then
        current_group="${BASH_REMATCH[1]}"
        echo "Processing group: $current_group"
    elif [[ $line =~ ^[[:space:]]*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)[[:space:]]*$ ]]; then
        ip="${BASH_REMATCH[1]}"
        echo "Found IP $ip in group $current_group"
        replace_ip_and_add_config "$ip"
    fi
done < hosts.ini

# Add [all:vars] section if it doesn't exist
if ! grep -q "\[all:vars\]" codespaces_ansible_hosts.ini; then
    echo "Adding [all:vars] section to codespaces_ansible_hosts.ini"
    echo "" >> codespaces_ansible_hosts.ini
    echo "[all:vars]" >> codespaces_ansible_hosts.ini
    echo "ansible_python_interpreter=/usr/bin/python3" >> codespaces_ansible_hosts.ini
fi

echo "Finished updating codespaces_ansible_hosts.ini"

# Step 11: Wait for SSH services to start on all containers

echo "Waiting for SSH services to start on all containers..."
declare -A exit_statuses  # Initialize an associative array to track exit statuses

# Check SSH readiness sequentially for all containers
while IFS= read -r line; do
    if [[ "$line" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+.* ]]; then
        container_ip=$(echo "$line" | awk '{print $1}')

        echo "Checking SSH readiness for $container_ip..."
        if check_ssh_ready "$container_ip"; then
            echo "$container_ip is ready"
            exit_statuses["$container_ip"]=0  # Mark as success
        else
            echo "$container_ip failed SSH check"
            exit_statuses["$container_ip"]=1  # Mark as failure
        fi
    fi
done < codespaces_ansible_hosts.ini

# Check for any failures in the SSH checks
ssh_check_failed=false
for container_ip in "${!exit_statuses[@]}"; do
    if [ "${exit_statuses[$container_ip]}" -ne 0 ]; then
        echo "Error: SSH check failed for $container_ip"
        ssh_check_failed=true
    fi
done

if [ "$ssh_check_failed" = true ]; then
    echo "Not all containers are ready. Exiting."
    exit 1  # Exit the script with error if any SSH check failed
else
    echo "All containers are ready!"
fi

# Step 12: Create ansible.cfg file

# Generate Ansible configuration file
cat << EOF > codespaces_ansible.cfg
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

# Step 13: Set ANSIBLE_CONFIG environment variable

export ANSIBLE_CONFIG=$(pwd)/codespaces_ansible.cfg

echo "Setup complete. You can now run your Ansible playbooks."

# Step 14: Run Ansible playbooks

echo "Running Ansible playbook..."

ansible-playbook -i codespaces_ansible_hosts.ini tasks.yaml

echo "Feel free to run tests now..."

exit 0
