#!/bin/bash

# Set the data directory for PostgreSQL
PGDATA="./pgdata"

# Set postgres configurations
PGPORT=5432

# Initialize a new PostgreSQL database cluster
initdb -D "$PGDATA"

# Start PostgreSQL server
pg_ctl -D "$PGDATA" -l logfile start

# Create a new PostgreSQL user and database
createdb mydatabase
createuser myuser --superuser
psql -c "ALTER USER myuser WITH PASSWORD 'mypassword';"

# Save environment configuration to db_config.env
cat > db_config.env <<EOL
PG_USER=myuser
PG_PASSWORD=mypassword
PG_PORT=$PGPORT
PG_HOST=localhost
PG_DATABASE=mydatabase
PGDATA=$PGDATA
EOL

echo "PostgreSQL server initialized and running."
echo "Config saved in db_config.env."
