#!/bin/bash
#
# Set up an inventory for the Vagrant test machine.
#
# Usage: init_vagrant_inventory.sh [inventory-file]
#
# Make sure that the virtual machine is active before you execute this file.
#
# If the given inventory exists, try to replace the ansible host IP, Port and IdentityFile for the
# 'vagrant' machine with the IP, Port and IdentityFile of the VM. If the file does not exist set
# up a new one.
# The inventory file must have a server for acme. A dummy entry is fine.
#
# If no inventory file is given, use 'vagrant.ini'.

CONFIG=${1:-vagrant.ini}
SSH_IP=`vagrant ssh-config | grep HostName | sed 's:.*HostName *::'`
SSH_Port=`vagrant ssh-config | grep Port | sed 's:.*Port *::'`
SSH_IdentityFile=`vagrant ssh-config | grep IdentityFile | sed 's:.*IdentityFile *::'`

if [[ -f $CONFIG ]]; then
    # just make sure the IP address, Port and IdentityFile is set correctly
    sed -i "s:vagrant ansible_host=[0-9.]*:vagrant ansible_host=$SSH_IP:" $CONFIG
    sed -i "s:ansible_port=[0-9]*:ansible_port=$SSH_Port:" $CONFIG
    sed -i "s:ansible_ssh_private_key_file=.*:ansible_ssh_private_key_file=$SSH_IdentityFile:" $CONFIG
else
   # create a new inventory file for vagrant
   cat > $CONFIG <<EOF
vagrant ansible_host=$SSH_IP ansible_port=$SSH_Port ansible_ssh_private_key_file=$SSH_IdentityFile

[acme]
dummy

[your test group]
vagrant
EOF
fi
