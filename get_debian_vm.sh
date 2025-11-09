#!/bin/bash
set -euo pipefail

# Configuration
DEB_NAME=trixie
DEB_VERSION=13
IMAGE_URL="https://cloud.debian.org/images/cloud/${DEB_NAME}/latest/debian-${DEB_VERSION}-generic-amd64.qcow2"
VM_NAME="OSM-server-debian-${DEB_NAME}"
DISK_SIZE=20G
VM_RAM=2048
VM_VCPUS=2
VM_IP="192.168.137.13"
IMAGE_FILE=/var/lib/libvirt/images/debian-${DEB_NAME}.qcow

if [ "$(virsh dominfo OSM-server-debian-$DEB_NAME)" ]
then
  echo "OSM-server-debian-trixie already exists, exiting"
  exit 0
fi

cd vm
wget -Nc ${IMAGE_URL}
cd -

# resize disk
echo "Resizing disk to $DISK_SIZE"
sudo cp vm/debian-${DEB_VERSION}-generic-amd64.qcow2 $IMAGE_FILE
sudo chown libvirt-qemu:kvm $IMAGE_FILE
sudo chmod 644 $IMAGE_FILE
sudo -u libvirt-qemu qemu-img resize $IMAGE_FILE "$DISK_SIZE"

# create temporary key for use before bootstrapping
if [ ! -f vm/id_ed25519 ]
then
  ssh-keygen -t ed25519 -f vm/id_ed25519 -N ""
fi

#create static network
virsh net-define vm/static-net.xml
if [ ! "$(virsh net-info osm-server | grep "Active.*yes")" ]
then
  echo start static network osm-server
  virsh net-start osm-server
  virsh net-autostart osm-server
fi


#create user-data file for cloud-init
echo "#cloud-config
hostname: $VM_NAME
users:
  - name: root
    ssh_authorized_keys:
      - $(cat vm/id_ed25519.pub)
    shell: /bin/bash
chpasswd:
  expire: False

package_upgrade: true
packages:
  - avahi-daemon
  - python3
  - zstd
" > vm/user-data

#create network-config
echo "# cloud init network config
network:
  version: 2
  ethernets:
    enp1s0:
      dhcp4: false
      addresses:
        - $VM_IP/24
      gateway4: 192.168.137.1
      nameservers:
        addresses: 
          - 192.168.137.1
" > vm/network-config

echo Install VM
virt-install \
    --name "$VM_NAME" \
    --memory "$VM_RAM" \
    --vcpus "$VM_VCPUS" \
    --disk "$IMAGE_FILE",bus=virtio \
    --os-variant debian${DEB_VERSION} \
    --virt-type kvm \
    --graphics spice \
    --noautoconsole \
    --network bridge=vm-osm-server,model=virtio \
    --import \
    --cloud-init user-data="vm/user-data",network-config="vm/network-config"
#    --cloud-init user-data="vm/user-data,meta-data=vm/meta-data,network-config=vm/network-config"

ssh-keygen -R $VM_IP

echo VM created, waiting a few seconds...
sleep 15
echo Doing ansible bootstrap

ansible-playbook -i vm/ansible_vm.ini bootstrap.yml -l $DEB_NAME --key-file vm/id_ed25519
