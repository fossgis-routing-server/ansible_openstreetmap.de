#zfs on tile server (6T, currently bonne)

- apt install linux-headers-amd64 zfs-dkms zfsutils-linux
- zpool create -f database -o ashift=12 /dev/md3
- zfs set compression=lz4 database
- zfs set xattr=sa database
- zfs set atime=off database
- zfs create database/postgresql
- zfs set recordsize=64K  database/postgresql
- zfs set mountpoint=/var/lib/postgresql database/postgresql
