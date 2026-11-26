#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements-render.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py inicializar_produccion
python manage.py cifrar_datos_cuentas || true
python manage.py aplicar_rls || true
python manage.py sincronizar_puntos_sda --si-vacio || true
