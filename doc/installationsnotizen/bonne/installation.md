# Installation Bonne

## Daten 

### Hardware

Prozessoren: Intel Core i9 
SSD: 2x1T
NVMe: 1x4T

Ort: Rechenzentrum Falkenstein.

### Netzwerk

Hostname: bonne (https://de.wikipedia.org/wiki/Bonnesche_Projektion)

168.119.11.226
2a01:4f8:242:424f::2

ssh root@168.119.11.226

### Hetzner Rescue-System

```
$ ssh root@168.119.11.226
Linux rescue 6.3.1 #1 SMP Tue May  2 12:08:34 UTC 2023 x86_64

-------------------------------------------------------------------------------------------------------------------------

  Welcome to the Hetzner Rescue System.

  This Rescue System is based on Debian GNU/Linux 11 (bullseye) with a custom kernel.
  You can install software like you would in a normal system.

  To install a new operating system from one of our prebuilt images, run 'installimage' and follow the instructions.

  Important note: Any data that was not written to the disks will be lost during a reboot.

  For additional information, check the following resources:
    Rescue System:           https://docs.hetzner.com/robot/dedicated-server/troubleshooting/hetzner-rescue-system
    Installimage:            https://docs.hetzner.com/robot/dedicated-server/operating-systems/installimage
    Install custom software: https://docs.hetzner.com/robot/dedicated-server/operating-systems/installing-custom-images
    other articles:          https://docs.hetzner.com/robot

-------------------------------------------------------------------------------------------------------------------------

Rescue System up since 2023-05-22 21:05 +02:00

Last login: Mon May 22 21:37:30 2023 from 185.231.254.236
Hardware data:

   CPU1: Intel(R) Core(TM) i9-9900K CPU @ 3.60GHz (Cores 16)
   Memory:  128742 MB
   Disk /dev/nvme0n1: 1024 GB (=> 953 GiB) doesn't contain a valid partition table
   Disk /dev/nvme1n1: 3840 GB (=> 3576 GiB) doesn't contain a valid partition table
   Disk /dev/nvme2n1: 1024 GB (=> 953 GiB) doesn't contain a valid partition table
   Total capacity 5484 GiB with 3 Disks

Network data:
   eth0  LINK: yes
         MAC:  b4:2e:99:48:1c:65
         IP:   168.119.11.226
         IPv6: 2a01:4f8:242:424f::2/64
         Intel(R) PRO/1000 Network Driver

```

#### Mounting

```
root@rescue ~ # lsblk
NAME    MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
loop0     7:0    0   2.8G  1 loop 
nvme0n1 259:0    0 953.9G  0 disk 
nvme2n1 259:1    0 953.9G  0 disk 
nvme1n1 259:2    0   3.5T  0 disk 
```

```
root@rescue ~ # ls /dev/mapper/*
/dev/mapper/control
```

Hier ist nichts notwendig.

#### Root Passwort

Wird disabled. Macht das Ansible? todo
https://docs.hetzner.com/robot/dedicated-server/troubleshooting/hetzner-rescue-system/#resetting-the-root-password


#### Betriebssystem

https://docs.hetzner.com/robot/dedicated-server/operating-systems/installimage

Ptolemy ist Debian 11.

```
astrid@ptolemy:~$ lsb_release -a
No LSB modules are available.
Distributor ID:	Debian
Description:	Debian GNU/Linux 11 (bullseye)
Release:	11
Codename:	bullseye

```

## Installation

### installimage

#### Skript

debian -> debian-1106-bullseye-amd64-base

```

## ======================================================
##  Hetzner Online GmbH - installimage - standard config
## ======================================================


## ====================
##  HARD DISK DRIVE(S):
## ====================

## PLEASE READ THE NOTES BELOW!

# unkown
DRIVE1 /dev/nvme0n1
# unkown
DRIVE2 /dev/nvme1n1
# unkown
# DRIVE3 /dev/nvme2n1

## if you dont want raid over your three drives then comment out the following line and set SWRAIDLEVEL not to 5
## please make sure the DRIVE[nr] variable is strict ascending with the used harddisks, when you comment out one or more harddisks


## ===============
##  SOFTWARE RAID:
## ===============

## activate software RAID?  < 0 | 1 >

SWRAID 1

## Choose the level for the software RAID < 0 | 1 | 5 | 10 >

SWRAIDLEVEL 1

## ==========
##  HOSTNAME:
## ==========

## which hostname should be set?
##

HOSTNAME bonne

## ================
##  NETWORK CONFIG:
## ================

# IPV4_ONLY no


## =============
##  MISC CONFIG:
## =============

USE_KERNEL_MODE_SETTING yes

## ==========================
##  PARTITIONS / FILESYSTEMS:
## ==========================

## define your partitions and filesystems like this:
##
## PART  <mountpoint/lvm/btrfs.X>  <filesystem/VG>  <size in MB>
##
## * <mountpoint/lvm/btrfs.X>
##            mountpoint for this filesystem *OR*
##            keyword 'lvm' to use this PART as volume group (VG) for LVM *OR*
##            identifier 'btrfs.X' to use this PART as volume for
##            btrfs subvolumes. X can be replaced with a unique
##            alphanumeric keyword
##            NOTE: no support btrfs multi-device volumes
##            NOTE: reiserfs support is deprecated and will be removed in a future version
## * <filesystem/VG>
##            can be ext2, ext3, ext4, btrfs, reiserfs, xfs, swap  *OR*  name
##            of the LVM volume group (VG), if this PART is a VG.
## * <size>
##            you can use the keyword 'all' to assign all the
##            remaining space of the drive to the *last* partition.
##            you can use M/G/T for unit specification in MiB/GiB/TiB
##
## notes:
##   - extended partitions are created automatically
##   - '/boot' cannot be on a xfs filesystem
##   - '/boot' cannot be on LVM!
##   - when using software RAID 0, you need a '/boot' partition
##
## example without LVM (default):
## -> 4GB   swapspace
## -> 512MB /boot
## -> 10GB  /
## -> 5GB   /tmp
## -> all the rest to /home
#PART swap   swap        4G
#PART /boot  ext2      512M
#PART /      ext4       10G
#PART /tmp   xfs         5G
#PART /home  ext3       all
#
##
## to activate LVM, you have to define volume groups and logical volumes
##
## example with LVM:
#
## normal filesystems and volume group definitions:
## -> 512MB boot  (not on lvm)
## -> all the rest for LVM VG 'vg0'
#PART /boot  ext3     512M
#PART lvm    vg0       all
#
## logical volume definitions:
#LV <VG> <name> <mount> <filesystem> <size>
#
#LV vg0   root   /        ext4         10G
#LV vg0   swap   swap     swap          4G
#LV vg0   home   /home    xfs          20G
#
##
## to use btrfs subvolumes, define a volume identifier on a partition
##
## example with btrfs subvolumes:
##
## -> all space on one partition with volume 'btrfs.1'
#PART btrfs.1    btrfs       all
##
## btrfs subvolume definitions:
#SUBVOL <volume> <subvolume> <mount>
#
#SUBVOL btrfs.1  @           /
#SUBVOL btrfs.1  @/usr       /usr
#SUBVOL btrfs.1  @home       /home
#
## your system has the following devices:
#
# Disk /dev/nvme0n1: 3840 GB (=> 3576 GiB) 
# Disk /dev/nvme1n1: 1024 GB (=> 953 GiB) 
# Disk /dev/nvme2n1: 1024 GB (=> 953 GiB) 
#
## Based on your disks and which RAID level you will choose you have
## the following free space to allocate (in GiB):
# RAID  0: ~2859
# RAID  1: ~953
# RAID  5: ~1906
#

PART swap swap 4G
PART /boot ext3 1024M
PART / ext4 50G


## ========================
##  OPERATING SYSTEM IMAGE:
## ========================

## full path to the operating system image
##   supported image sources:  local dir,  ftp,  http,  nfs
##   supported image types: tar, tar.gz, tar.bz, tar.bz2, tar.xz, tgz, tbz, txz
## examples:
#
# local: /path/to/image/filename.tar.gz
# ftp:   ftp://<user>:<password>@hostname/path/to/image/filename.tar.bz2
# http:  http://<user>:<password>@hostname/path/to/image/filename.tbz
# https: https://<user>:<password>@hostname/path/to/image/filename.tbz
# nfs:   hostname:/path/to/image/filename.tgz
#
# for validation of the image, place the detached gpg-signature
# and your public key in the same directory as your image file.
# naming examples:
#  signature:   filename.tar.bz2.sig
#  public key:  public-key.asc

IMAGE /root/.oldroot/nfs/install/../images/Debian-1106-bullseye-amd64-base.tar.gz

```



#### Ergebnis

```

                Hetzner Online GmbH - installimage

  Your server will be installed now, this will take some minutes
             You can abort at any time with CTRL+C ...

         :  Reading configuration                           done 
         :  Loading image file variables                    done 
         :  Loading debian specific functions               done 
   1/16  :  Deleting partitions                             done 
   2/16  :  Test partition size                             done 
   3/16  :  Creating partitions and /etc/fstab              done 
   4/16  :  Creating software RAID level 1                  done 
   5/16  :  Formatting partitions
         :    formatting /dev/md/0 with swap                done 
         :    formatting /dev/md/1 with ext3                done 
         :    formatting /dev/md/2 with ext4                done 
   6/16  :  Mounting partitions                             done 
   7/16  :  Sync time via ntp                               done 
         :  Importing public key for image validation       done 
   8/16  :  Validating image before starting extraction     done 
   9/16  :  Extracting image (local)                        done 
  10/16  :  Setting up network config                       done 
  11/16  :  Executing additional commands
         :    Setting hostname                              done 
         :    Generating new SSH keys                       done 
         :    Generating mdadm config                       done 
         :    Generating ramdisk                            done 
         :    Generating ntp config                         done 
  12/16  :  Setting up miscellaneous files                  done 
  13/16  :  Configuring authentication
         :    Fetching SSH keys                             done 
         :    Disabling root password                       done 
         :    Disabling SSH root login with password        done 
         :    Copying SSH keys                              done 
  14/16  :  Installing bootloader grub                      done 
  15/16  :  Running some debian specific functions          done 
  16/16  :  Clearing log files                              done 

                  INSTALLATION COMPLETE
   You can now reboot and log in to your new system with the
 same credentials that you used to log into the rescue system.
```

#### Erstes Login

```
astrid@astrid-virtual-machine:~$ ssh root@168.119.11.226
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
Someone could be eavesdropping on you right now (man-in-the-middle attack)!
It is also possible that a host key has just been changed.
The fingerprint for the ED25519 key sent by the remote host is
SHA256:qNtId0u/sNSkGDwb+zMKfnzHzQR/MvcWo8e/fv8zPao.
Please contact your system administrator.
Add correct host key in /home/astrid/.ssh/known_hosts to get rid of this message.
Offending ECDSA key in /home/astrid/.ssh/known_hosts:40
  remove with:
  ssh-keygen -f "/home/astrid/.ssh/known_hosts" -R "168.119.11.226"
Host key for 168.119.11.226 has changed and you have requested strict checking.
Host key verification failed.
astrid@astrid-virtual-machine:~$ ssh root@168.119.11.226
The authenticity of host '168.119.11.226 (168.119.11.226)' can't be established.
ED25519 key fingerprint is SHA256:qNtId0u/sNSkGDwb+zMKfnzHzQR/MvcWo8e/fv8zPao.
This key is not known by any other names
Are you sure you want to continue connecting (yes/no/[fingerprint])? y
Please type 'yes', 'no' or the fingerprint: yes
Warning: Permanently added '168.119.11.226' (ED25519) to the list of known hosts.
root@168.119.11.226's password: 
Permission denied, please try again.
root@168.119.11.226's password: 
Permission denied, please try again.
root@168.119.11.226's password: 
root@168.119.11.226: Permission denied (publickey,password).
astrid@astrid-virtual-machine:~$ ssh root@168.119.11.226
root@168.119.11.226's password:
```

#### Bootstrap

Alle Konten erstellen via `ansible-playbook -l bonne bootstrap.yml`

### ZFS

##### Aktuell (vor zfs)

```
root@bonne ~ # mount
sysfs on /sys type sysfs (rw,nosuid,nodev,noexec,relatime)
proc on /proc type proc (rw,relatime)
udev on /dev type devtmpfs (rw,nosuid,relatime,size=65891472k,nr_inodes=16472868,mode=755)
devpts on /dev/pts type devpts (rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000)
tmpfs on /run type tmpfs (rw,nosuid,nodev,noexec,relatime,size=13182876k,mode=755)
/dev/md2 on / type ext4 (rw,relatime)
securityfs on /sys/kernel/security type securityfs (rw,nosuid,nodev,noexec,relatime)
tmpfs on /dev/shm type tmpfs (rw,nosuid,nodev)
tmpfs on /run/lock type tmpfs (rw,nosuid,nodev,noexec,relatime,size=5120k)
cgroup2 on /sys/fs/cgroup type cgroup2 (rw,nosuid,nodev,noexec,relatime,nsdelegate,memory_recursiveprot)
pstore on /sys/fs/pstore type pstore (rw,nosuid,nodev,noexec,relatime)
none on /sys/fs/bpf type bpf (rw,nosuid,nodev,noexec,relatime,mode=700)
systemd-1 on /proc/sys/fs/binfmt_misc type autofs (rw,relatime,fd=30,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=15785)
hugetlbfs on /dev/hugepages type hugetlbfs (rw,relatime,pagesize=2M)
mqueue on /dev/mqueue type mqueue (rw,nosuid,nodev,noexec,relatime)
debugfs on /sys/kernel/debug type debugfs (rw,nosuid,nodev,noexec,relatime)
tracefs on /sys/kernel/tracing type tracefs (rw,nosuid,nodev,noexec,relatime)
fusectl on /sys/fs/fuse/connections type fusectl (rw,nosuid,nodev,noexec,relatime)
configfs on /sys/kernel/config type configfs (rw,nosuid,nodev,noexec,relatime)
/dev/md1 on /boot type ext3 (rw,relatime)
tmpfs on /run/user/0 type tmpfs (rw,nosuid,nodev,relatime,size=13182872k,nr_inodes=3295718,mode=700)
```

```
root@bonne ~ # sudo fdisk -l /dev/md1
Disk /dev/md1: 1022 MiB, 1071644672 bytes, 2093056 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
root@bonne ~ # ^C
root@bonne ~ # sudo fdisk -l /dev/md0
Disk /dev/md0: 4 GiB, 4289724416 bytes, 8378368 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
root@bonne ~ # sudo fdisk -l /dev/md2
Disk /dev/md2: 49.97 GiB, 53652488192 bytes, 104790016 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
root@bonne ~ # sudo fdisk -l /dev/md3
fdisk: cannot open /dev/md3: No such file or directory
```

```
root@bonne ~ # df -h
Filesystem      Size  Used Avail Use% Mounted on
udev             63G     0   63G   0% /dev
tmpfs            13G  720K   13G   1% /run
/dev/md2         49G  1.1G   46G   3% /
tmpfs            63G     0   63G   0% /dev/shm
tmpfs           5.0M     0  5.0M   0% /run/lock
/dev/md1        989M   60M  879M   7% /boot
tmpfs            13G     0   13G   0% /run/user/0
```

```
root@bonne ~ # cat /proc/mdstat 
Personalities : [raid1] [linear] [multipath] [raid0] [raid6] [raid5] [raid4] [raid10] 
md2 : active raid1 nvme1n1p3[0] nvme2n1p3[2] nvme0n1p3[1]
      52395008 blocks super 1.2 [3/3] [UUU]
      
md1 : active raid1 nvme1n1p2[0] nvme2n1p2[2] nvme0n1p2[1]
      1046528 blocks super 1.2 [3/3] [UUU]
      
md0 : active (auto-read-only) raid1 nvme1n1p1[0] nvme2n1p1[2] nvme0n1p1[1]
      4189184 blocks super 1.2 [3/3] [UUU]
      
unused devices: <none>
```

```
root@bonne ~ # lsblk
NAME        MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINT
nvme0n1     259:0    0 953.9G  0 disk  
├─nvme0n1p1 259:1    0     4G  0 part  
│ └─md0       9:0    0     4G  0 raid1 [SWAP]
├─nvme0n1p2 259:2    0     1G  0 part  
│ └─md1       9:1    0  1022M  0 raid1 /boot
└─nvme0n1p3 259:3    0    50G  0 part  
  └─md2       9:2    0    50G  0 raid1 /
nvme1n1     259:4    0 953.9G  0 disk  
├─nvme1n1p1 259:5    0     4G  0 part  
│ └─md0       9:0    0     4G  0 raid1 [SWAP]
├─nvme1n1p2 259:6    0     1G  0 part  
│ └─md1       9:1    0  1022M  0 raid1 /boot
└─nvme1n1p3 259:7    0    50G  0 part  
  └─md2       9:2    0    50G  0 raid1 /
nvme2n1     259:8    0   3.5T  0 disk  
├─nvme2n1p1 259:9    0     4G  0 part  
│ └─md0       9:0    0     4G  0 raid1 [SWAP]
├─nvme2n1p2 259:10   0     1G  0 part  
│ └─md1       9:1    0  1022M  0 raid1 /boot
└─nvme2n1p3 259:11   0    50G  0 part  
  └─md2       9:2    0    50G  0 raid1 /

```

##### Partitionieren

```
cfdisk /dev/nvme0n1
cfdisk /dev/nvme1n1
cfdisk /dev/nvme2n1
```

dos kann per gdisk in gpt geändert werden.

```
gdisk /dev/nvme2n1
```

https://wiki.ubuntuusers.de/gdisk/


##### Befehle

> Via `sudo screen` kann man zusammen eine Konsole ansehen. Man kann den screen verlassen mit `ctrl-a ctrl-d` und wieder hervorholen mit `screen -r`. `screen -r xxxx` und `ctrl-a ` dann `k` zum `killen`.


```
sudo apt install linux-headers-amd64
sudo apt install linux-image-amd64
sudo apt install zfs-dkms zfsutils-linux
```

> `zfs-dkms` enthält die SPA (Storage Pool Allocator), DMU (Data Management Unit), ZVOL (ZFS-Volumes) und ZPL ((ZFS POSIX Layer) Komponenten von OpenZFS (https://packages.debian.org/sid/zfs-dkms/; https://wiki.lustre.org/images/4/49/Beijing-2010.2-ZFS_overview_3.1_Dilger.pdf)
> `zfsutils-linux` enthält die Befehle `zfs` und `zpool`, um OpenZFS-Dateisysteme zu erstellen und zu verwalten (https://packages.debian.org/de/sid/zfsutils-linux). 

```
sudo /sbin/modprobe zfs  
```

```
zpool create -f ssd -o ashift=12 /dev/nvme0n1p4 /dev/nvme1n1p4 /dev/nvme2n1p4
```

> Mittels `sudo zpool create -f [new pool name] /Laufwerk /Laufwerk` wird ein Speicherpool erstellt, in dem die Daten auf alle angegebenen Laufwerke verteilt werden (RAID0). Der Verlust eines der Laufwerke hat den Verlust aller Daten zur Folge. (https://blog.programster.org/zfs-create-disk-pools) 

> Ashift teilt ZFS die zugrunde liegende physikalische Blockgröße mit, die die Festplatten verwenden. Sie wird in Bits angegeben, also bedeutet ashift=9 512B-Sektoren (verwendet von allen alten Festplatten), ashift=12 bedeutet 4K-Sektoren (verwendet von den meisten modernen Festplatten) und ashift=13 bedeutet 8K-Sektoren (verwendet von einigen modernen SSDs).
Wenn man sich hier irrt, sollte man sich möglichst hoch irren. Ein zu niedriger ashift-Wert wird die Leistungsfähigkeit einschränken. Ein zu hoher ashift-Wert hat bei fast jeder normalen Arbeitslast keine große Auswirkung (https://jrs-s.net/2018/08/17/zfs-tuning-cheat-sheet/).


Überprüfen mit:
```
root@bonne ~ # sudo zpool list -v
NAME          SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
ssd          5.19T   408K  5.19T        -         -     0%     0%  1.00x    ONLINE  -
  nvme0n1p4   896G   152K   896G        -         -     0%  0.00%      -  ONLINE  
  nvme1n1p4   896G   104K   896G        -         -     0%  0.00%      -  ONLINE  
  nvme2n1p4  3.44T   152K  3.44T        -         -     0%  0.00%      -  ONLINE  
root@bonne ~ # sudo zfs list 
NAME   USED  AVAIL     REFER  MOUNTPOINT
ssd    408K  5.03T       96K  /ssd
```

```
sudo zfs set compression=lz4 ssd
```

> Die Komprimierung ist standardmäßig ausgeschaltet, und das ist ein schlechter Standardwert. Selbst wenn die Daten nicht komprimierbar sind, ist der ungenutze Speicher komprimierbar. (https://jrs-s.net/2018/08/17/zfs-tuning-cheat-sheet/; https://de.wikipedia.org/wiki/LZ4)

```
sudo zfs set xattr=sa ssd
```

> Legt Linux eXtended ATTRibutes direkt in den Inodes fest, anstatt als winzige kleine Dateien in speziellen versteckten Ordnern.
Dies kann erhebliche Auswirkungen auf die Leistung von Datensätzen mit vielen Dateien haben. Bei Datensätzen mit sehr wenigen, extrem großen Dateien ist dies unwichtig (https://jrs-s.net/2018/08/17/zfs-tuning-cheat-sheet/).

```
sudo zfs set atime=off ssd
```

> Wenn atime aktiviert ist - was standardmäßig der Fall ist - muss das System das Attribut "Accessed" jeder Datei jedes Mal aktualisieren, wenn darauf zugegriffen wird. Allein dadurch kann sich die IOPS-Last eines Systems leicht verdoppeln. Interessiert es jemanden, wann eine bestimmte Datei das letzte Mal geöffnet oder ein Verzeichnis das letzte Mal durchgelesen wurde? Wahrscheinlich nicht (https://jrs-s.net/2018/08/17/zfs-tuning-cheat-sheet/).

```
sudo zfs create ssd/postgresql
sudo zfs set recordsize=64K ssd/postgresql
```

```
sudo zfs create ssd/flatnode
sudo zfs set recordsize=64K ssd/flatnode
```

```
sudo zfs create ssd/tiles
sudo zfs set recordsize=64K ssd/tiles
```

Überprüfen:

```
root@bonne ~ # sudo zpool list -v
NAME          SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
ssd          5.19T  1.13M  5.19T        -         -     0%     0%  1.00x    ONLINE  -
  nvme0n1p4   896G   448K   896G        -         -     0%  0.00%      -  ONLINE  
  nvme1n1p4   896G   260K   896G        -         -     0%  0.00%      -  ONLINE  
  nvme2n1p4  3.44T   448K  3.44T        -         -     0%  0.00%      -  ONLINE  
root@bonne ~ # sudo zfs list 
NAME             USED  AVAIL     REFER  MOUNTPOINT
ssd             1.02M  5.03T      112K  /ssd
ssd/flatnode      96K  5.03T       96K  /ssd/flatnode
ssd/postgresql    96K  5.03T       96K  /ssd/postgresql
ssd/tiles         96K  5.03T       96K  /ssd/tiles
```

```
zfs set mountpoint=/var/cache/tirex/ ssd/tiles
zfs set mountpoint=/var/lib/postgresql ssd/postgresql
zfs set mountpoint=/ssd/planet ssd/planet

sudo chown tile /ssd/planet/
```

Überprüfen

```
astrid@bonne:~$ sudo zfs list
NAME             USED  AVAIL     REFER  MOUNTPOINT
ssd             69.0G  4.96T      104K  /ssd
ssd/flatnode      96K  4.96T       96K  /ssd/flatnode
ssd/planet      69.0G  4.96T     69.0G  /ssd/planet
ssd/postgresql  15.6M  4.96T     15.6M  /var/lib/postgresql
ssd/tiles        104K  4.96T      104K  /var/cache/tirex/
```

## Tile

### Playbook für Tile

`ansible-playbook -l bonne -i hosts.ini site.yml`

`sudo /usr/local/sbin/import-osm2pgsql`

Überprüfung: `https://bonne.openstreetmap.de/0/0/0.png` sollte eine Tile laden.

