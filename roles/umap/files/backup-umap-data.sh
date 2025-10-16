#!/bin/bash

# uMap Data Backup Script
# Usage: ./backup-umap-data.sh

# Configuration
export BORG_RSH='ssh -i ~/.ssh/$ssh_key_name'
export BORG_PASSPHRASE="$borg_passphrase"
export REPO="ssh://$remote_backup_user@$remote_backup_host:$remote_backup_port/$remote_backup_directory"

# Initialize repository if it doesn't exist
echo "Checking if repository exists..."
if ! borg info ${REPO} >/dev/null 2>&1; then
    echo "Repository does not exist. Initializing..."
    borg init --encryption=repokey ${REPO}
    echo "Repository initialized successfully"
else
    echo "Repository exists, continuing with backup"
fi

# Backup uMap data
echo "Starting uMap data backup..."
nice -n 19 \
ionice -c idle \
        borg create ${REPO}::umapdata-`date +%Y%m%d%H%M` \
        /srv/umap/umapdata/media_root \
        -C lz4 \
        -v \
        --stats \
        --list \
        --exclude-caches \
        2>&1 \
        | egrep -v "^[Udshcb] "

if [ $? -eq 0 ]; then
    echo "uMap data backup completed successfully"
else
    echo "uMap data backup failed!"
    exit 1
fi

# Prune old backups
echo "Pruning old uMap data backups..."
borg prune -sv ${REPO} \
        --keep-daily=7 \
        --keep-weekly=4 \
        --keep-monthly=3 \
        --prefix="umapdata-"

# Compact repository
echo "Compacting repository..."
borg compact -v ${REPO}

echo "uMap data backup process completed"
