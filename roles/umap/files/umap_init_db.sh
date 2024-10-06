#!/bin/bash
set -e

# wait until DB is ready to accept connections
until pg_isready -U "${POSTGRES_USER}"; do
  sleep 2
done

# check if DB already exists
DB_EXISTS=$(psql -U "${POSTGRES_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'")


if [[ ${DB_EXISTS} != "1" ]]; then
    echo "No DB found, initializing DB ${DB_NAME}"

    echo "Creating DB user ${DB_USER_UMAP} "
    psql -U "${POSTGRES_USER}" -c "CREATE USER ${DB_USER_UMAP} WITH PASSWORD '${DB_USER_PASSWORD}'"

    echo "Creating database ${DB_NAME} "
    psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER_UMAP}"

    # Check if DUMP_FILE exists before attempting to restore backup
    if [[ -n ${DUMP_FILE} && -f ${DUMP_FILE} ]]; then
        echo "Restore backup ${DUMP_FILE} "
        psql -U "${POSTGRES_USER}" -d "${DB_NAME}" -f "${DUMP_FILE}"
        #todo import pictograms
    else
        echo "Backup file ${DUMP_FILE} not found, installing PostGIS to ${DB_NAME} and granting privileges to user ${DB_USER_UMAP}."
        # Install PostGIS in the newly created database
        psql -U "${POSTGRES_USER}" -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
        # Grant all privileges to the created user
        psql -U "${POSTGRES_USER}" -d "${DB_NAME}" -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER_UMAP};"
    fi
else
    echo "Database ${DB_NAME} already exists."
fi

