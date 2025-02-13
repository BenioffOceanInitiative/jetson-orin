# Orin on device code for tracking system

## Setup
- Navigate to the orin_refactor directory
- Copy the .env.example file into a .env file, and fill it out

```bash
cp .env.example .env
```
- In the device management dashboard, create a new device, and copy the device secret to the .env file
- run 
```bash
chmod +x install.sh
```
- To install run the install script as root
```bash
sudo ./install.sh
```

- This will install the dependencies and the systemd service file