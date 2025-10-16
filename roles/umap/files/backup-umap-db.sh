#!/bin/bash

# uMap Database Backup Script
# Usage: ./backup-umap-db.sh

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

# Backup database
echo "Starting uMap database backup..."
docker exec umap_db pg_dump -U postgres umapdb \
        | borg create --stats -v -C lz4 \
        ${REPO}::umapdb-`date +%Y%m%d%H%M` - 

if [ $? -eq 0 ]; then
    echo "Database backup completed successfully"
else
    echo "Database backup failed!"
    exit 1
fi

# Prune old backups
echo "Pruning old database backups..."
borg prune -sv ${REPO} \
        --keep-daily=7 \
        --keep-weekly=4 \
        --keep-monthly=3 \
        --prefix="umapdb-"

# Compact repository
echo "Compacting repository..."
borg compact -v ${REPO}

echo "Database backup process completed"
