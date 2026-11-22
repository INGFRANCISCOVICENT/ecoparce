#!/bin/bash
# Respaldo semanal de la base de datos (PythonAnywhere → Tasks, programado semanalmente).
# Las credenciales se leen del archivo ~/.my.cnf (permisos 600), nunca de este script.
set -euo pipefail
DESTINO="$HOME/respaldos"
mkdir -p "$DESTINO"
FECHA=$(date +%Y-%m-%d)
mysqldump --defaults-file="$HOME/.my.cnf" --single-transaction --no-tablespaces "usuario\$ecoparce" | gzip > "$DESTINO/ecoparce-$FECHA.sql.gz"
# Conservar solo los últimos 8 respaldos (dos meses)
ls -1t "$DESTINO"/ecoparce-*.sql.gz | tail -n +9 | xargs -r rm --
