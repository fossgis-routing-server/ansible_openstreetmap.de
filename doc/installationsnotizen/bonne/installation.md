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

todo1 mount /dev/mapper/control /mnt

#### Root Passwort

todo2 https://docs.hetzner.com/robot/dedicated-server/troubleshooting/hetzner-rescue-system/#resetting-the-root-password


#### Betriebssystem

todo1
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

### ZFS

#### Ptolemy

##### Aktuell

```
astrid@ptolemy:~$ sudo fdisk -l
Disk /dev/nvme0n1: 953.87 GiB, 1024209543168 bytes, 2000409264 sectors
Disk model: SAMSUNG MZVLB1T0HALR-00000              
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: dos
Disk identifier: 0x9b6883fd

Device         Boot     Start        End    Sectors   Size Id Type
/dev/nvme0n1p1           2048    8390655    8388608     4G fd Linux raid autodetect
/dev/nvme0n1p2        8390656   10487807    2097152     1G fd Linux raid autodetect
/dev/nvme0n1p3       10487808  115345407  104857600    50G fd Linux raid autodetect
/dev/nvme0n1p4      115345408 2000409263 1885063856 898.9G fd Linux raid autodetect


Disk /dev/nvme1n1: 953.87 GiB, 1024209543168 bytes, 2000409264 sectors
Disk model: SAMSUNG MZVLB1T0HALR-00000              
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: dos
Disk identifier: 0x472b7d64

Device         Boot     Start        End    Sectors   Size Id Type
/dev/nvme1n1p1           2048    8390655    8388608     4G fd Linux raid autodetect
/dev/nvme1n1p2        8390656   10487807    2097152     1G fd Linux raid autodetect
/dev/nvme1n1p3       10487808  115345407  104857600    50G fd Linux raid autodetect
/dev/nvme1n1p4      115345408 2000409263 1885063856 898.9G fd Linux raid autodetect


Disk /dev/md2: 49.97 GiB, 53652488192 bytes, 104790016 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes


Disk /dev/md1: 1022 MiB, 1071644672 bytes, 2093056 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes


Disk /dev/md0: 4 GiB, 4289724416 bytes, 8378368 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes


Disk /dev/md127: 1.76 TiB, 1930034151424 bytes, 3769597952 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 524288 bytes / 1048576 bytes
Disklabel type: gpt
Disk identifier: D6FA7FE6-F503-8F4F-8F45-D7523A471D1C

Device            Start        End    Sectors  Size Type
/dev/md127p1       2048 3769579519 3769577472  1.8T Solaris /usr & Apple ZFS
/dev/md127p9 3769579520 3769595903      16384    8M Solaris reserved 1

```

```
astrid@ptolemy:~$ sudo lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINT
NAME          FSTYPE              SIZE MOUNTPOINT
nvme0n1                         953.9G 
├─nvme0n1p1   linux_raid_member     4G 
│ └─md0       swap                  4G [SWAP]
├─nvme0n1p2   linux_raid_member     1G 
│ └─md1       ext3               1022M /boot
├─nvme0n1p3   linux_raid_member    50G 
│ └─md2       ext4                 50G /
└─nvme0n1p4   linux_raid_member 898.9G 
  └─md127                         1.8T 
    ├─md127p1 zfs_member          1.8T 
    └─md127p9                       8M 
nvme1n1                         953.9G 
├─nvme1n1p1   linux_raid_member     4G 
│ └─md0       swap                  4G [SWAP]
├─nvme1n1p2   linux_raid_member     1G 
│ └─md1       ext3               1022M /boot
├─nvme1n1p3   linux_raid_member    50G 
│ └─md2       ext4                 50G /
└─nvme1n1p4   linux_raid_member 898.9G 
  └─md127                         1.8T 
    ├─md127p1 zfs_member          1.8T 
    └─md127p9                       8M 

```

```
astrid@ptolemy:~$ sudo lsblk -f -m
NAME          FSTYPE            FSVER LABEL       UUID                                 FSAVAIL FSUSE% MOUNTPOINT   SIZE OWNER GROUP MODE
nvme0n1                                                                                                          953.9G root  disk  brw-rw----
├─nvme0n1p1   linux_raid_member 1.2   rescue:0    0a5cbf6e-beb6-8980-8320-90365c5ba4bc                               4G root  disk  brw-rw----
│ └─md0       swap              1                 525e0f77-7f7c-4570-83d1-a6040827256a                [SWAP]         4G root  disk  brw-rw----
├─nvme0n1p2   linux_raid_member 1.2   rescue:1    db58efd5-fea8-f2b2-07ef-62e346e04a67                               1G root  disk  brw-rw----
│ └─md1       ext3              1.0               93bb0cda-ca66-4c9b-9603-190fd1edfef7  829.9M    11% /boot       1022M root  disk  brw-rw----
├─nvme0n1p3   linux_raid_member 1.2   rescue:2    4d5077da-b1df-2b99-cdb1-4e8b870ef80c                              50G root  disk  brw-rw----
│ └─md2       ext4              1.0               0f4930f3-ac24-43b9-a006-b66d7fdbefe5   34.9G    23% /             50G root  disk  brw-rw----
└─nvme0n1p4   linux_raid_member 1.2   ptolemy:md3 92f436a3-96f8-f31f-2a67-53048907f985                           898.9G root  disk  brw-rw----
  └─md127                                                                                                          1.8T root  disk  brw-rw----
    ├─md127p1 zfs_member        5000  database    3114522629682411855                                              1.8T root  disk  brw-rw----
    └─md127p9                                                                                                        8M root  disk  brw-rw----
nvme1n1                                                                                                          953.9G root  disk  brw-rw----
├─nvme1n1p1   linux_raid_member 1.2   rescue:0    0a5cbf6e-beb6-8980-8320-90365c5ba4bc                               4G root  disk  brw-rw----
│ └─md0       swap              1                 525e0f77-7f7c-4570-83d1-a6040827256a                [SWAP]         4G root  disk  brw-rw----
├─nvme1n1p2   linux_raid_member 1.2   rescue:1    db58efd5-fea8-f2b2-07ef-62e346e04a67                               1G root  disk  brw-rw----
│ └─md1       ext3              1.0               93bb0cda-ca66-4c9b-9603-190fd1edfef7  829.9M    11% /boot       1022M root  disk  brw-rw----
├─nvme1n1p3   linux_raid_member 1.2   rescue:2    4d5077da-b1df-2b99-cdb1-4e8b870ef80c                              50G root  disk  brw-rw----
│ └─md2       ext4              1.0               0f4930f3-ac24-43b9-a006-b66d7fdbefe5   34.9G    23% /             50G root  disk  brw-rw----
└─nvme1n1p4   linux_raid_member 1.2   ptolemy:md3 92f436a3-96f8-f31f-2a67-53048907f985                           898.9G root  disk  brw-rw----
  └─md127                                                                                                          1.8T root  disk  brw-rw----
    ├─md127p1 zfs_member        5000  database    3114522629682411855                                              1.8T root  disk  brw-rw----
    └─md127p9                                                                                                        8M root  disk  brw-rw----
```



```
astrid@ptolemy:~$ lsblk
NAME          MAJ:MIN RM   SIZE RO TYPE  MOUNTPOINT
nvme0n1       259:0    0 953.9G  0 disk  
├─nvme0n1p1   259:2    0     4G  0 part  
│ └─md0         9:0    0     4G  0 raid1 [SWAP]
├─nvme0n1p2   259:3    0     1G  0 part  
│ └─md1         9:1    0  1022M  0 raid1 /boot
├─nvme0n1p3   259:6    0    50G  0 part  
│ └─md2         9:2    0    50G  0 raid1 /
└─nvme0n1p4   259:7    0 898.9G  0 part  
  └─md127       9:127  0   1.8T  0 raid0 
    ├─md127p1 259:10   0   1.8T  0 part  
    └─md127p9 259:11   0     8M  0 part  
nvme1n1       259:1    0 953.9G  0 disk  
├─nvme1n1p1   259:4    0     4G  0 part  
│ └─md0         9:0    0     4G  0 raid1 [SWAP]
├─nvme1n1p2   259:5    0     1G  0 part  
│ └─md1         9:1    0  1022M  0 raid1 /boot
├─nvme1n1p3   259:8    0    50G  0 part  
│ └─md2         9:2    0    50G  0 raid1 /
└─nvme1n1p4   259:9    0 898.9G  0 part  
  └─md127       9:127  0   1.8T  0 raid0 
    ├─md127p1 259:10   0   1.8T  0 part  
    └─md127p9 259:11   0     8M  0 part  
```

```
astrid@ptolemy:~$ sudo zpool list -v
NAME        SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
database   1.75T   678G  1.09T        -         -    53%    37%  1.00x    ONLINE  -
md127      1.75T   678G  1.09T        -         -    53%  37.8%      -    ONLINE
```


```
astrid@ptolemy:~$ sudo zfs list 
NAME                  USED  AVAIL     REFER  MOUNTPOINT
database              678G  1.03T      140G  /database
database/flatnode    67.4G  1.03T     67.4G  /database/flatnode
database/postgresql   387G  1.03T      387G  /database/postgresql
database/tiles       82.4G  1.03T     82.4G  /var/cache/tirex/
```


```
astrid@ptolemy:~$ sudo zpool status
  pool: database
 state: ONLINE
  scan: scrub repaired 0B in 00:06:31 with 0 errors on Sun May 14 00:30:32 2023
config:

	NAME        STATE     READ WRITE CKSUM
	database    ONLINE       0     0     0
	  md127     ONLINE       0     0     0

errors: No known data errors
```

##### Notizen

zfs for 1T SSD, better performance for postgres. Otherwise, disk consumtion keeps rising

50G für root als raid1

sudo apt install zfs-dkms zfsutils-linux
sudo zpool create -f ssd -o ashift=12 /dev/nvme..
sudo zfs set compression=lz4 ssd
sudo zfs set xattr=sa ssd
sudo zfs set atime=off ssd
sudo zfs create ssd/postgresql
sudo zfs set recordsize=64K ssd/postgresql
sudo zfs create ssd/flatnode
sudo zfs set recordsize=64K ssd/flatnode


##### Geplante Befehle

```
sudo apt install zfs-dkms zfsutils-linux
```

> `zfs-dkms` enthält die SPA (Storage Pool Allocator), DMU (Data Management Unit), ZVOL (ZFS-Volumes) und ZPL ((ZFS POSIX Layer) Komponenten von OpenZFS (https://packages.debian.org/sid/zfs-dkms/; https://wiki.lustre.org/images/4/49/Beijing-2010.2-ZFS_overview_3.1_Dilger.pdf)
> `zfsutils-linux` enthält die Befehle `zfs` und `zpool`, um OpenZFS-Dateisysteme zu erstellen und zu verwalten (https://packages.debian.org/de/sid/zfsutils-linux). 

```
sudo zpool create -f ssd ashift=12 /dev/nvme0n1 /dev/nvme1n1 /dev/nvme2n1
```

> Mittels `sudo zpool create -f [new pool name] /Laufwerk /Laufwerk` wird ein Speicherpool erstellt, in dem die Daten auf alle angegebenen Laufwerke verteilt werden (RAID0). Der Verlust eines der Laufwerke hat den Verlust aller Daten zur Folge. (https://blog.programster.org/zfs-create-disk-pools) 

> Ashift teilt ZFS die zugrunde liegende physikalische Blockgröße mit, die die Festplatten verwenden. Sie wird in Bits angegeben, also bedeutet ashift=9 512B-Sektoren (verwendet von allen alten Festplatten), ashift=12 bedeutet 4K-Sektoren (verwendet von den meisten modernen Festplatten) und ashift=13 bedeutet 8K-Sektoren (verwendet von einigen modernen SSDs).
Wenn man sich hier irrt, sollte man sich möglichst hoch irren. Ein zu niedriger ashift-Wert wird die Leistungsfähigkeit einschränken. Ein zu hoher ashift-Wert hat bei fast jeder normalen Arbeitslast keine große Auswirkung (https://jrs-s.net/2018/08/17/zfs-tuning-cheat-sheet/).

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


##### Weitere Optionen?

1. In ZFS definiert `recordsize` die Größe jedes Schreibvorgangs. Der Standardwert für `recordsize` ist 128Kb. 

```
astrid@ptolemy:/var/cache/tirex/tiles/osmde/20/133/86/40/51$ ls -lh
total 213K
-rw-r--r-- 1 _tirex _tirex  90K May 22 16:40 136.meta
-rw-r--r-- 1 _tirex _tirex 109K May 22 16:40 8.meta

astrid@ptolemy:/var/cache/tirex/tiles/osmde/19/100/98/2/110$ ls -lh
total 277K
-rw-r--r-- 1 _tirex _tirex 136K May 22 17:21 136.meta
-rw-r--r-- 1 _tirex _tirex 129K May 22 17:21 8.meta

astrid@ptolemy:/var/cache/tirex/tiles/osmde/14/0/16/203/8$ ls -lh
total 25K
-rw-r--r-- 1 _tirex _tirex 9.1K May 22 13:57 136.meta
-rw-r--r-- 1 _tirex _tirex  26K May 22 13:57 8.meta

astrid@ptolemy:/var/cache/tirex/tiles/osmde/9/0/0/17/20$ ls -lh
total 18K
-rw-r--r-- 1 _tirex _tirex 7.0K May 10 23:31 0.meta
-rw-r--r-- 1 _tirex _tirex 7.0K May 10 23:31 128.meta
-rw-r--r-- 1 _tirex _tirex 7.0K May 10 23:31 136.meta
-rw-r--r-- 1 _tirex _tirex 7.0K May 10 23:31 8.meta

astrid@ptolemy:/var/cache/tirex/tiles/osmde/2/0/0/0/0$ ls -lh
total 77K
-rw-r--r-- 1 _tirex _tirex 71K May 21 21:32 0.meta

astrid@ptolemy:/var/cache/tirex/tiles/osmde/0/0/0/0/0$ ls -lh
total 8.5K
-rw-r--r-- 1 _tirex _tirex 7.3K May 21 22:39 0.meta
```

2. Caching mit L2ARC (lesen - Level 2 ARC) oder Separate Log (schreiben - kurz SLOG) https://www.starline.de/magazin/technische-artikel/ram-und-ssd-cache-optionen-fuer-openzfs 


## Installation

### installimage

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
DRIVE3 /dev/nvme2n1

## if you dont want raid over your three drives then comment out the following line and set SWRAIDLEVEL not to 5
## please make sure the DRIVE[nr] variable is strict ascending with the used harddisks, when you comment out one or more harddisks


## ===============
##  SOFTWARE RAID:
## ===============

## activate software RAID?  < 0 | 1 >

SWRAID 1

## Choose the level for the software RAID < 0 | 1 | 5 | 10 >

## todo SWRAIDLEVEL 5
SWRAIDLEVEL 0

## ==========
##  HOSTNAME:
## ==========

## which hostname should be set?
##

## todo HOSTNAME Debian-1106-bullseye-amd64-base
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
# Disk /dev/nvme0n1: 1024 GB (=> 953 GiB) doesn't contain a valid partition table
# Disk /dev/nvme1n1: 3840 GB (=> 3576 GiB) doesn't contain a valid partition table
# Disk /dev/nvme2n1: 1024 GB (=> 953 GiB) doesn't contain a valid partition table
#
## Based on your disks and which RAID level you will choose you have
## the following free space to allocate (in GiB):
# RAID  0: ~2859
# RAID  1: ~953
# RAID  5: ~1906
#



## todo PART swap swap 4G
## todo PART /boot ext3 1024M
## todo PART / ext4 all

PART swap swap 4G
PART /boot ext3 1024M
PART / ext4 50GB
PART / ext4 all


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