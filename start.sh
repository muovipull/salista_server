#!/bin/bash

# --- Asetukset ---

# Virtuaaliympäristön polku
VENV_PATH="venv"

# Flask-sovelluksen tiedostonimi
APP_FILE="app.py"

# Flask-instanssin muuttujan nimi
FLASK_INSTANCE_NAME="app"

# Gunicornin työntekijöiden määrä
WORKERS=5

# Palvelimen osoite ja portti
BIND_ADDRESS="0.0.0.0:5000"

# --- LOKIASETUKSET (Fail2Ban tarvitsee nämä) ---
ACCESS_LOG="access.log"
ERROR_LOG="error.log"

# --- Skripti alkaa ---

echo "Käynnistetään Flask-palvelin (Gunicornilla)..."

# 1. Tarkista ja aktivoi virtuaaliympäristö
if [ -d "$VENV_PATH" ]; then
    echo "Aktivoidaan virtuaaliympäristö"
    source "$VENV_PATH/bin/activate"
else
    echo "VIRHE: Virtuaaliympäristöä ei löydy."
    exit 1
fi

# 2. Tarkista sovellustiedosto
APP_MODULE=$(basename "$APP_FILE" .py)

if [ ! -f "$APP_FILE" ]; then
    echo "VIRHE: Sovellustiedostoa '$APP_FILE' ei löydy."
    deactivate
    exit 1
fi

# 3. Tarkista Gunicorn
if ! command -v gunicorn &> /dev/null; then
    echo "VIRHE: Gunicorn ei ole asennettu."
    deactivate
    exit 1
fi

# 4. Käynnistä Flask-sovellus Gunicornilla ja kirjoita lokia
echo "Suoritetaan Gunicorn portaassa $BIND_ADDRESS..."
echo "Loki tallennetaan tiedostoon: $ACCESS_LOG"

# TÄMÄ ON MUUTETTU RIVI:
gunicorn --workers "$WORKERS" \
         --bind "$BIND_ADDRESS" \
         --access-logfile "$ACCESS_LOG" \
         --error-logfile "$ERROR_LOG" \
         --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
         "$APP_MODULE":"$FLASK_INSTANCE_NAME"

# --- Skripti loppuu ---

deactivate
echo "Palvelin suljettu."
