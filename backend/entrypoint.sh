#!/bin/sh
set -e

# Aplicar migraciones antes de aceptar peticiones.
alembic upgrade head

exec "$@"
