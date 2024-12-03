# codespaces_create_and_start_containers.Dockerfile

FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

# Use the TIMEZONE variable to configure the timezone
ENV TIMEZONE=Etc/UTC
RUN ln -fs /usr/share/zoneinfo/$TIMEZONE /etc/localtime && echo $TIMEZONE > /etc/timezone

# Update package list and install dependencies in one line
RUN apt-get update && apt-get install -y \
    software-properties-common \
    openssh-server \
    sudo \
    python3 \
    python3-venv \
    python3-setuptools \
    python3-wheel \
    python3-apt \
    passwd \
    tzdata \
    iproute2 \
    wget \
    cron \
    --no-install-recommends && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-distutils \
    python3.11-dev && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install pip using get-pip.py
RUN wget https://bootstrap.pypa.io/get-pip.py && python3.11 get-pip.py && rm get-pip.py

# Install required Python packages
RUN python3.11 -m pip install --no-cache-dir passlib cffi cryptography

# Ensure python3-apt is properly installed and linked
RUN ln -s /usr/lib/python3/dist-packages/apt_pkg.cpython-310-x86_64-linux-gnu.so /usr/lib/python3/dist-packages/apt_pkg.so || true

# Prepare SSH server
RUN mkdir /var/run/sshd

# Create ansible user
RUN useradd -m -s /bin/bash ansible

# Set up SSH for ansible
RUN mkdir -p /home/ansible/.ssh && \
    chmod 700 /home/ansible/.ssh && \
    chown ansible:ansible /home/ansible/.ssh

# Configure sudo access for ansible
RUN echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible

# Disable root SSH login
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config

# Expose SSH port
EXPOSE 22

# Start SSH server
CMD ["/usr/sbin/sshd", "-D"]
