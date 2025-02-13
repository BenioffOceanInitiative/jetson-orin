# installs tracker.service systemd service
#!/bin/bash

#check if the script is run as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

# Install python deps
sudo apt-get update
pip install -r requirements.txt

current_dir=$(pwd)
# make sure the current directory is orin_refactor
if [ ${current_dir##*/} != "orin_refactor" ]; then
    echo "Please run the script from the orin_refactor directory"
    exit
fi

echo "Current directory: $current_dir"
echo "Installing tracker.service"
sudo cp $current_dir/tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tracker.service
sudo systemctl start tracker.service
echo "tracker.service installed and started"
echo "To check the status of the service run: sudo systemctl status tracker.service"
echo "To stop the service run: sudo systemctl stop tracker.service"
echo "To start the service run: sudo systemctl start tracker.service"
echo "To uninstall the service run: sudo systemctl disable tracker.service && sudo rm /etc/systemd/system/tracker.service && sudo systemctl daemon-reload"

