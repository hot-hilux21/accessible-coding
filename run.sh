#!/bin/sh
# Production entry point for the Oracle Cloud deployment, run under PM2.
#
# The app reads its settings from the environment (SECRET_KEY, PORT,
# ALLOWED_HOSTS), and PM2 does not read .env files, so load it here.
# Run with: pm2 start run.sh --name accessible-coding
set -a
. "$(dirname "$0")/.env"
set +a

cd "$(dirname "$0")"
exec ./venv/bin/gunicorn \
  --bind "0.0.0.0:${PORT:-3000}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  wsgi:app
