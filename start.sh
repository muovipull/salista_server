#!/bin/bash

# --- Asetukset ---

# Virtuaaliympäristön polku
VENV_PATH="venv"

# Flask-sovelluksen tiedostonimi (oletetaan app.py, jossa Flask-instanssi on 'app')
APP_FILE="app.py"

# Flask-instanssin muuttujan nimi sovellustiedostossa (yleensä 'app')
# MUISTA: Gunicornin syntaksi on [tiedosto]:[instanssin_nimi]
FLASK_INSTANCE_NAME="app"

# Gunicornin työntekijöiden (workers) määrä (yleensä 2x CPU-ytimien määrä + 1)
WORKERS=5

# Palvelimen osoite ja portti
# Korvaa tarvittaessa 0.0.0.0:5000 haluamallasi osoitteella
BIND_ADDRESS="0.0.0.0:5000"

# --- Skripti alkaa ---

echo "Käynnistetään Flask-palvelin (Gunicornilla)..."

# 1. Tarkista ja aktivoi virtuaaliympäristö
if [ -d "$VENV_PATH" ]; then
    echo "Aktivoidaan virtuaaliympäristö $VENV_PATH/bin/activate"
    # Aktivoi ympäristö käyttämällä 'source'
    source "$VENV_PATH/bin/activate"
else
    echo "VIRHE: Virtuaaliympäristöä ei löydy polusta $VENV_PATH."
    echo "Luo virtuaaliympäristö komennolla 'python3 -m venv venv' ja asenna Flask/Gunicorn."
    exit 1
fi

# 2. Tarkista, onko sovellustiedosto olemassa
# Poistetaan .py-pääte tiedostonimestä Gunicornia varten
APP_MODULE=$(basename "$APP_FILE" .py)

if [ ! -f "$APP_FILE" ]; then
    echo "VIRHE: Sovellustiedostoa '$APP_FILE' ei löydy."
    deactivate # Poistu virtuaaliympäristöstä
    exit 1
fi

# 3. Tarkista, onko Gunicorn asennettu (valinnainen, mutta suositeltava)
if ! command -v gunicorn &> /dev/null; then
    echo "VIRHE: Gunicorn ei ole asennettu virtuaaliympäristöön."
    echo "Asenna se komennolla 'pip install gunicorn' ja yritä uudelleen."
    deactivate
    exit 1
fi

# 4. Käynnistä Flask-sovellus Gunicornilla
# Syntaksi: gunicorn --workers [workers] --bind [osoite] [moduuli]:[instanssi]
echo "Suoritetaan komento: gunicorn --workers $WORKERS --bind $BIND_ADDRESS $APP_MODULE:$FLASK_INSTANCE_NAME"

gunicorn --workers "$WORKERS" --bind "$BIND_ADDRESS" "$APP_MODULE":"$FLASK_INSTANCE_NAME"

# --- Skripti loppuu ---

# Kun Gunicorn suljetaan (esim. Ctrl+C), deaktivoi ympäristö
deactivate
echo "Palvelin suljettu ja virtuaaliympäristö deaktivoitu."