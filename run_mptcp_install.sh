#!/bin/bash
wget -O install.sh https://raw.githubusercontent.com/Ysurac/openmptcprouter-vps/develop/debian9-x86_64.sh
chmod +x install.sh
export DEBIAN_FRONTEND=noninteractive
yes "" | sudo -E ./install.sh
