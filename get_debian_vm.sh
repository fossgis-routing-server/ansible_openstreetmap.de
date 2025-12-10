#!/bin/bash
set -euo pipefail

declare -A DEB_RELEASES=(
  [bookworm]=12
  [trixie]=13
)

# Configuration
DEFAULT_DEB_NAME=trixie
DEFAULT_DEB_VERSION=${DEB_RELEASES[$DEFAULT_DEB_NAME]}
DEFAULT_DISK_SIZE=20G
DEFAULT_VM_RAM=2048
VM_VCPUS=2
VM_USER="root"

# Read
read -p "Enter disk size [default: $DEFAULT_DISK_SIZE]: " input_disk
DISK_SIZE="${input_disk:-$DEFAULT_DISK_SIZE}"

read -p "Enter RAM in MB [default: $DEFAULT_VM_RAM]: " input_ram
VM_RAM="${input_ram:-$DEFAULT_VM_RAM}"

echo "Available Debian releases:"
for name in "${!DEB_RELEASES[@]}"; do
  echo "  $name: ${DEB_RELEASES[$name]}"
done

read -p "Enter Debian version [default: $DEFAULT_DEB_VERSION]: " input_version
DEB_VERSION="${input_version:-$DEFAULT_DEB_VERSION}"

VM_IP="192.168.137.$DEB_VERSION"

for name in "${!DEB_RELEASES[@]}"; do
  if [[ "${DEB_RELEASES[$name]}" == "$DEB_VERSION" ]]; then
    DEB_NAME="$name"
    break
  fi
done

IMAGE_FILE=/var/lib/libvirt/images/debian-${DEB_NAME}.qcow
IMAGE_URL="https://cloud.debian.org/images/cloud/${DEB_NAME}/latest/debian-${DEB_VERSION}-generic-amd64.qcow2"
VM_NAME="OSM-server-debian-${DEB_NAME}"

# Use system-wide daemon, we need to be able to create a network.
export LIBVIRT_DEFAULT_URI='qemu:///system'

# Check if VM exists
if virsh dominfo "$VM_NAME" &>/dev/null; then
    echo "VM $VM_NAME already exists."
    read -p "Do you want to delete it? [y/N]: " delete_choice
    case "$delete_choice" in
        y|Y )
            echo "Deleting VM..."
            virsh destroy "$VM_NAME" 2>/dev/null || true
            virsh undefine "$VM_NAME" 2>/dev/null || true
            if [ -f "$IMAGE_FILE" ]; then
                echo "Deleting disk $IMAGE_FILE..."
                sudo rm -f "$IMAGE_FILE"
            fi
            if virsh net-info osm-server &>/dev/null; then
                echo "Stopping and removing network osm-server..."
                virsh net-destroy osm-server 2>/dev/null || true
                virsh net-undefine osm-server 2>/dev/null || true
            fi
            echo "VM has been removed."

            # Recreate the VM
            read -p "Do you want to recreate the VM now? [y/N]: " recreate_choice
            case "$recreate_choice" in
                y|Y )
                    echo "Proceeding to recreate the VM..."
                    ;;
                * )
                    echo "Not recreating. Exiting."
                    exit 0
                    ;;
            esac
            ;;
        * )
            echo "VM not deleted. Exiting."
            exit 0
            ;;
    esac
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
  - name: $VM_USER
    ssh_authorized_keys:
      - $(cat vm/id_ed25519.pub)
    shell: /bin/bash
chpasswd:
  expire: False

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

ssh-keygen -R $VM_IP

set +e

while sleep 2; do
    echo VM created, trying to connect...
    ssh -i vm/id_ed25519 $VM_USER@$VM_IP echo Success.
    if [ "$?" -eq 0 ]; then
        break
    fi
done

echo "Waiting for cloud-init to finish..."
for i in $(seq 1 60); do
    status=$(ssh -i vm/id_ed25519 $VM_USER@$VM_IP cloud-init status)
    echo "Cloud-init status: $status"

    if [[ "$status" == *"done"* ]]; then
        echo "Cloud-init finished!"
        break
    fi

    sleep 5
done

echo Doing ansible bootstrap

ansible-playbook -i vm/ansible_vm.ini bootstrap.yml -l $DEB_NAME --key-file vm/id_ed25519
