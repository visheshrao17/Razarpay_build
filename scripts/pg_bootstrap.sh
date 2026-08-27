#!/bin/bash
# Idempotent PostgreSQL bootstrap for SettleSense: ensures cluster, role and database exist.
set -u

PG_VERSION=15
DATA_DIR="/var/lib/postgresql/${PG_VERSION}/main"

if ! command -v psql >/dev/null 2>&1; then
  apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-contrib
fi

if [ ! -f "${DATA_DIR}/PG_VERSION" ]; then
  pg_createcluster "${PG_VERSION}" main || true
  supervisorctl restart postgresql || true
fi

for i in $(seq 1 60); do
  pg_isready -h localhost -p 5432 -q && break
  sleep 1
done

sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='settlesense'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER settlesense WITH PASSWORD 'settlesense_local';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='settlesense'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE settlesense OWNER settlesense;"

supervisorctl restart backend || true
echo "pg_bootstrap: done"
exit 0
