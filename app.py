import time
import random
import sqlite3
from flask import Flask, jsonify, request, redirect, url_for, render_template_string
from flask_cors import CORS

# --- Sovelluksen määritykset ---
app = Flask(__name__)
# CORS sallii Unity-clientin ottaa yhteyttä (tarpeellinen kehityksessä)
CORS(app)

# Tietokantatiedoston nimi
DATABASE = 'database.db'

# --- Tietokantafunktiot ---

def get_db_connection():
    """ Luo tietokantayhteyden ja asettaa rivien palautusmuodoksi sanakirjan (sqlite3.Row). """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """ Alustaa tietokannan luomalla items- ja users-taulut, jos ne eivät ole jo olemassa. """
    conn = get_db_connection()
    # 1. Esineet (Items)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            nimi TEXT NOT NULL,
            numero TEXT,
            lisatieto TEXT,
            maara TEXT,
            verkkosivu TEXT
        )
    ''')
    # 2. Käyttäjät (Users) - Päivitetty taulu tilapäiselle avaimelle ja vanhenemisajalle
    # one_time_key: 8-numeroinen numerosarja (STRING)
    # key_expiry: Unix-aikaleima (REAL)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            one_time_key TEXT,
            key_expiry REAL
        )
    ''')
    conn.commit()
    conn.close()

# Alusta tietokanta heti sovelluksen käynnistyessä
with app.app_context():
    init_db()

# --- Reitit / API Endpoints ---

@app.route('/get_all_items_by_id/<user_id>', methods=['GET'])
def get_all_items_by_id(user_id):
    """ Hakee kaikki esineet tietylle käyttäjälle ilman erillistä todennusta (säännöllinen lataus). """
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    conn = get_db_connection()
    # Haetaan tiedot
    items = conn.execute("SELECT id, nimi, numero, lisatieto, maara, verkkosivu FROM items WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    # Palautetaan data JSON-muodossa
    return jsonify([dict(item) for item in items])


@app.route('/generate_transfer_key', methods=['POST'])
def generate_transfer_key():
    """ Luo satunnaisen 8-numeroisen siirtoavaimen, joka on voimassa 15 minuuttia (900s). """
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # 1. Luo satunnainen 8-numeroinen numerosarja
    key = ''.join([str(random.randint(0, 9)) for _ in range(8)])

    # 2. Laske vanhenemisaika (15 minuuttia = 900 sekuntia)
    EXPIRY_SECONDS = 900
    expiry_time = time.time() + EXPIRY_SECONDS # Unix timestamp

    conn = get_db_connection()
    try:
        # Tarkista, onko user_id users-taulussa (käytetään UPSET-tyyppistä logiikkaa)
        cursor = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            # Päivitä olemassa oleva rivi
            conn.execute("UPDATE users SET one_time_key = ?, key_expiry = ? WHERE user_id = ?",
                         (key, expiry_time, user_id))
        else:
            # Lisää uusi rivi
            conn.execute("INSERT INTO users (user_id, one_time_key, key_expiry) VALUES (?, ?, ?)",
                         (user_id, key, expiry_time))

        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        print(f"Database error during key generation: {e}")
        return jsonify({"error": "Database error during key generation."}), 500

    conn.close()

    return jsonify({
        "message": "One-time key generated successfully",
        "one_time_key": key,
        "expires_in_seconds": EXPIRY_SECONDS
    }), 200


@app.route('/all_items_web', methods=['GET'])
def all_items_web():
    """
    DEBUGGAUSREITTI: Näyttää kaikki tallennetut tiedot suoraan selaimessa (HTML-muodossa)
    ja lisää poistonapit jokaiselle riville sekä käyttäjän ID:lle.
    """
    conn = get_db_connection()
    # Haetaan items- ja users-taulujen tiedot yhdistäen ne user_id:n perusteella
    items = conn.execute("SELECT i.*, u.one_time_key, u.key_expiry FROM items i LEFT JOIN users u ON i.user_id = u.user_id").fetchall()
    conn.close()

    html_output = """
    <!DOCTYPE html>
    <html lang="fi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kaikki Tallennetut Tiedot</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
            h1 { color: #0056b3; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #fff; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
            th { background-color: #007bff; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            tr:hover { background-color: #e9e9e9; }
            .no-data { text-align: center; color: #888; padding: 20px; }
            .expired { color: red; font-weight: bold; }
            .delete-btn { background-color: #dc3545; color: white; border: none; padding: 5px 10px; text-align: center; text-decoration: none; display: inline-block; font-size: 14px; margin: 2px 2px; cursor: pointer; border-radius: 4px; }
            .delete-btn:hover { background-color: #c82333; }
            .user-row { background-color: #e1f5fe !important; font-weight: bold; }
        </style>
        <script>
            // Varmistusfunktio
            function confirmDelete(message) {
                return confirm(message);
            }
        </script>
    </head>
    <body>
        <h1>Kaikki Tallennetut Tiedot</h1>
    """

    current_time = time.time()

    if not items:
        html_output += "<p class='no-data'>Ei tallennettuja tietoja.</p>"
    else:
        html_output += """
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Käyttäjän ID</th>
                    <th>Poista KÄYTTÄJÄN DATA</th>
                    <th>Tilapäinen Avain</th>
                    <th>Vanhenee (UTC)</th>
                    <th>Vanhentunut?</th>
                    <th>Nimi</th>
                    <th>Numero</th>
                    <th>Lisätieto</th>
                    <th>Salasana / Määrä</th>
                    <th>Verkkosivu</th>
                    <th>Poista ESINE</th>
                </tr>
            </thead>
            <tbody>
        """

        # Kerätään uniikit käyttäjä-ID:t
        user_ids = sorted(list(set(item['user_id'] for item in items)))

        # Kerätään users-taulun tiedot erikseen
        users_data = {}
        conn = get_db_connection()
        user_rows = conn.execute("SELECT user_id, one_time_key, key_expiry FROM users").fetchall()
        conn.close()
        for row in user_rows:
            users_data[row['user_id']] = dict(row)


        # Näytetään tiedot käyttäjittäin (epävirallinen ryhmittely)
        for user_id in user_ids:
            # Käyttäjäkohtainen poistonappi (Poistaa kaiken, myös avaimen users-taulusta)
            user_data = users_data.get(user_id, {'one_time_key': None, 'key_expiry': None})

            expiry_timestamp = user_data['key_expiry']
            key_expired = expiry_timestamp is not None and current_time > expiry_timestamp
            expiry_status = f"<span class='{'expired' if key_expired else ''}'>{'KYLLÄ' if key_expired else 'EI'}</span>"
            expiry_str = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(expiry_timestamp)) if expiry_timestamp else 'N/A'

            # Poistonappi koko käyttäjälle
            delete_user_form = f"""
                <form method="POST" action="{url_for('delete_user_data', user_id=user_id)}" onsubmit="return confirmDelete('Oletko varma, että haluat poistaa KAIKKI tiedot käyttäjältä {user_id}?');">
                    <input type="submit" value="Poista KAIKKI" class="delete-btn">
                </form>
            """

            # Lisätään tyhjä rivi käyttäjän tiedoille
            html_output += f"""
                <tr class="user-row">
                    <td>-</td>
                    <td>{user_id}</td>
                    <td>{delete_user_form}</td>
                    <td>{user_data['one_time_key'] if user_data['one_time_key'] else 'Ei asetettu'}</td>
                    <td>{expiry_str}</td>
                    <td>{expiry_status}</td>
                    <td colspan="6"></td>
                </tr>
            """

            # Näytetään käyttäjän esineet
            for item in [i for i in items if i['user_id'] == user_id]:
                # Poistonappi yksittäiselle esineelle
                delete_item_form = f"""
                    <form method="POST" action="{url_for('delete_item_web', item_id=item['id'], user_id=item['user_id'])}" onsubmit="return confirmDelete('Oletko varma, että haluat poistaa esineen ID {item['id']}?');">
                        <input type="submit" value="Poista" class="delete-btn">
                    </form>
                """

                html_output += f"""
                    <tr>
                        <td>{item['id']}</td>
                        <td>{item['user_id']}</td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td>{item['nimi']}</td>
                        <td>{item['numero']}</td>
                        <td>{item['lisatieto']}</td>
                        <td>{item['maara']}</td>
                        <td><a href="{item['verkkosivu']}" target="_blank">{item['verkkosivu']}</a></td>
                        <td>{delete_item_form}</td>
                    </tr>
                """
        html_output += """
            </tbody>
        </table>
        """

    html_output += """
    </body>
    </html>
    """
    return html_output, 200, {'Content-Type': 'text/html'}


# UUSI REITTI: Poistaa yksittäisen esineen selainkäyttöliittymästä
@app.route('/delete_item_web/<int:item_id>/<user_id>', methods=['POST'])
def delete_item_web(item_id, user_id):
    """ Poistaa esineen sen ID:n ja user_id:n perusteella ja ohjaa takaisin all_items_web-sivulle. """
    conn = get_db_connection()
    try:
        # Tarkista ensin, että esine on olemassa ja kuuluu käyttäjälle
        cursor = conn.execute("SELECT id FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        item = cursor.fetchone()

        if item is None:
            conn.close()
            # Virheilmoitus selaimessa (yksinkertaisuuden vuoksi)
            return f"Virhe: Esineä ID {item_id} tai käyttäjää {user_id} ei löydy.", 404

        # Suorita poisto
        conn.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        return f"Tietokantavirhe poistettaessa esinettä: {e}", 500

    conn.close()

    # Ohjaa takaisin listaussivulle
    return redirect(url_for('all_items_web'))


# UUSI REITTI: Poistaa kaikki käyttäjän tiedot (items ja users)
@app.route('/delete_user_data/<user_id>', methods=['POST'])
def delete_user_data(user_id):
    """ Poistaa KAIKKI tiedot (items ja users-taulusta) annetulle user_id:lle. """
    conn = get_db_connection()
    try:
        # 1. Poista kaikki esineet items-taulusta
        conn.execute("DELETE FROM items WHERE user_id = ?", (user_id,))

        # 2. Poista käyttäjän avain users-taulusta
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        return f"Tietokantavirhe poistettaessa käyttäjän dataa: {e}", 500

    conn.close()

    # Ohjaa takaisin listaussivulle
    return redirect(url_for('all_items_web'))
# ---------------------------------------------------------------------------------------------------


@app.route('/check_user/<user_id>', methods=['GET'])
def check_user(user_id):
    """ Tarkistaa, onko annetulla user_id:llä tallennettuja esineitä. """
    conn = get_db_connection()
    # Lasketaan rivien määrä annetulla user_id:llä
    cursor = conn.execute("SELECT COUNT(*) FROM items WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()

    exists = count > 0
    return jsonify({"exists": exists}), 200

@app.route('/add_item', methods=['POST'])
def add_item():
    """ Lisää uuden esineen tietokantaan. """
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    nimi = data.get('nimi')
    numero = data.get('numero')
    lisatieto = data.get('lisatieto')
    maara = data.get('maara') # Käyttöliittymässä tämä on 'maara1', mutta sisältö on salasana/määrä
    verkkosivu = data.get('verkkosivu')

    if not nimi:
        return jsonify({"error": "Nimi is required"}), 400

    conn = get_db_connection()
    conn.execute("INSERT INTO items (user_id, nimi, numero, lisatieto, maara, verkkosivu) VALUES (?, ?, ?, ?, ?, ?)",
                 (user_id, nimi, numero, lisatieto, maara, verkkosivu))
    conn.commit()
    # Palautetaan juuri lisätyn rivin ID takaisin Unityyn
    item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({"message": "Item added successfully", "id": item_id}), 201

# Päivitetty: Käyttää tilapäistä avainta (one_time_key) ja tarkistaa vanhenemisen
@app.route('/get_items', methods=['POST'])
def get_items():
    """
    Hakee kaikki esineet tietylle käyttäjälle VAHVISTETUN, VOIMASSA OLEVAN tilapäisen avaimen avulla.
    """
    data = request.json
    user_id = data.get('user_id')
    # HUOM: Avain on nyt one_time_key
    one_time_key = data.get('one_time_key')

    if not user_id or not one_time_key:
        return jsonify({"error": "User ID and One-Time Key are required"}), 400

    conn = get_db_connection()

    # 1. Hae avain ja vanhenemisaika
    cursor = conn.execute("SELECT one_time_key, key_expiry FROM users WHERE user_id = ?", (user_id,))
    stored_data = cursor.fetchone()
    conn.close() # Suljetaan yhteys heti, kun data on haettu

    current_time = time.time()

    if stored_data is None:
        # Käyttäjää ei löydy users-taulusta, joka on OK, jos hänellä ei ole koskaan ollutkaan avainta
        return jsonify({"error": "Authentication failed. User not found (Key not generated for this ID)."}), 403

    stored_key = stored_data['one_time_key']
    expiry_time = stored_data['key_expiry']

    # 2. Avain ei täsmää
    if stored_key != one_time_key:
        return jsonify({"error": "Authentication failed. Invalid One-Time Key."}), 403

    # 3. Avain on vanhentunut TAI sitä ei ole koskaan asetettu
    if expiry_time is None or current_time > expiry_time:
        # Vastaus, joka erottaa vanhentuneen avaimen virheen
        return jsonify({"error": "Authentication failed. One-Time Key has expired."}), 403

    # Varmennus onnistui, haetaan tiedot
    conn = get_db_connection()
    items = conn.execute("SELECT id, nimi, numero, lisatieto, maara, verkkosivu FROM items WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    return jsonify([dict(item) for item in items])

@app.route('/delete_item/<user_id>/<int:item_id>', methods=['DELETE'])
def delete_item(user_id, item_id):
    """ Poistaa esineen sen ID:n perusteella varmistaen, että se kuuluu pyytäjälle. """
    conn = get_db_connection()

    # Tarkista ensin, että esine on olemassa ja kuuluu käyttäjälle
    cursor = conn.execute("SELECT id FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
    item = cursor.fetchone()

    if item is None:
        conn.close()
        return jsonify({"error": "Item not found or you do not have permission to delete it"}), 404

    # Suorita poisto
    conn.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Item deleted successfully"}), 200


if __name__ == "__main__":
    # Aja palvelin kuunnellen kaikkia IP-osoitteita portissa 50
    app.run(host='0.0.0.0', port=5001)