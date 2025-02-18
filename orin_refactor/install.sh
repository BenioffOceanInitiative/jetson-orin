#!/bin/bash

help_menu="Usage: ./install.sh [should_install_ssh_agent] [should_install_python_deps]
note: Must be run as root!
should_install_ssh_agent: true/false
should_install_python_deps: true/false
should_install_tracker: true/false
Example: sudo ./install.sh true true true
Example: sudo ./install.sh --all (installs all services)
Example: sudo ./install.sh -h (displays this help menu)
"

# Check for help flags
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "$help_menu"
    exit 0
fi

if [ "$1" = "--all" ]; then
    echo "Installing all services"
    should_install_ssh_agent="true"
    should_install_python_deps="true"
    should_install_tracker="true"
    echo "should_install_ssh_agent: $should_install_ssh_agent"
    echo "should_install_python_deps: $should_install_python_deps"
    echo "should_install_tracker: $should_install_tracker"
    echo "Running install.sh $should_install_ssh_agent $should_install_python_deps $should_install_tracker"
    ./install.sh $should_install_ssh_agent $should_install_python_deps $should_install_tracker
    exit 0
fi

# Check number of arguments
if [ "$#" -lt 1 ]; then
    echo "Invalid number of arguments"
    echo "$help_menu"
    exit 1
fi

# Validate each argument
should_install_ssh_agent=$1
if [ "$should_install_ssh_agent" != "true" ] && [ "$should_install_ssh_agent" != "false" ]; then
    echo "Invalid value for should_install_ssh_agent: $should_install_ssh_agent"
    echo "$help_menu"
    exit 1
fi

should_install_python_deps=$2
if [ "$should_install_python_deps" != "true" ] && [ "$should_install_python_deps" != "false" ]; then
    echo "Invalid value for should_install_python_deps: $should_install_python_deps"
    echo "$help_menu"
    exit 1
fi

should_install_tracker=$3
if [ "$should_install_tracker" != "true" ] && [ "$should_install_tracker" != "false" ]; then
    echo "Invalid value for should_install_tracker: $should_install_tracker"
    echo "$help_menu"
    exit 1
fi

echo "should_install_ssh_agent: $should_install_ssh_agent"
echo "should_install_python_deps: $should_install_python_deps"
echo "should_install_tracker: $should_install_tracker"

#check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Install python deps
if [ "$should_install_python_deps" = "true" ]; then
    echo "Installing python dependencies"
    sudo apt-get update
    pip install -r requirements.txt
    echo "Python dependencies installed"
fi

if [ "$should_install_ssh_agent" = "true" ]; then
    echo "Installing ssh-agent"
    sudo cp services/ssh-agent.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable ssh-agent.service
    sudo systemctl start ssh-agent.service
    echo "ssh-agent installed and started"
    echo "To check the status of the service run: sudo systemctl status ssh-agent.service"
    echo "To stop the service run: sudo systemctl stop ssh-agent.service"
    echo "To start the service run: sudo systemctl start ssh-agent.service"
    echo "To uninstall the service run: sudo systemctl disable ssh-agent.service && sudo rm /etc/systemd/system/ssh-agent.service && sudo systemctl daemon-reload"
fi

if [ "$should_install_tracker" = "true" ]; then
    echo "Installing tracker.service"
    sudo cp services/tracker.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable tracker.service
    sudo systemctl enable ssh-agent.service
    sudo systemctl start tracker.service
    sudo systemctl start ssh-agent.service
    echo "tracker.service installed and started"
    echo "To check the status of the service run: sudo systemctl status tracker.service"
    echo "To stop the service run: sudo systemctl stop tracker.service"
    echo "To start the service run: sudo systemctl start tracker.service"
    echo "To uninstall the service run: sudo systemctl disable tracker.service && sudo rm /etc/systemd/system/tracker.service && sudo systemctl daemon-reload"
fi

echo "Installation complete"
exit 0