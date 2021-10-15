#!/bin/bash
#
# Set up an inventory for the Vagrant test machine.
#
# Usage: init_vagrant_inventory.sh [inventory-file]
#
# If the given inventory exists, try to replace the ansible host IP for the
# 'vagrant' machine with the IP of the VM. If the file does not exist set
# up a new one.
#
# If no inventory file is given, use 'vagrant.ini'.

CONFIG=${1:-vagrant.ini}
SSH_IP=`vagrant ssh-config | grep HostName | sed 's:.*HostName *::'`

if [[ -f $CONFIG ]]; then
    # just make sure the IP address is set correctly
    sed -i "s:vagrant ansible_host=[0-9.]*:vagrant ansible_host=$SSH_IP:" $CONFIG
else
   # create a new inventory file for vagrant
   echo vagrant ansible_host=$SSH_IP > $CONFIG
fi
