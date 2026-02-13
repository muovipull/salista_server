import random
import sqlite3
import time
from flask import Flask, jsonify, request, redirect, url_for
from flask_cors import CORS

# --- Sovelluksen määritykset ---
app = Flask(__name__)
CORS(app)

DATABASE = 'database.db'

# --- Tietokantafunktiot ---

def get_db_connection():
    """ Luo tietokantayhteyden ja asettaa rivien palautusmuodoksi sanakirjan. """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """ Alustaa tietokannan modernilla rakenteella. """
    conn = get_db_connection()
    # Items-taulu: lisätty created_at (REAL eli Unix timestamp)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            nimi TEXT NOT NULL,
            numero TEXT,
            lisatieto TEXT,
            maara TEXT,
            verkkosivu TEXT,
            created_at REAL
        )
    ''')
    # Users-taulu: hallitsee siirtoavaimia
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            one_time_key TEXT,
            key_expiry REAL
        )
    ''')
    conn.commit()
    conn.close()

# Alusta tietokanta käynnistyksessä
with app.app_context():
    init_db()

# --- Web-käyttöliittymä (Moderni Dashboard) ---

@app.route('/all_items_web', methods=['GET'])
def all_items_web():
    conn = get_db_connection()
    # Haetaan kohteet uusimmat ensin
    items_rows = conn.execute("SELECT i.*, u.one_time_key, u.key_expiry FROM items i LEFT JOIN users u ON i.user_id = u.user_id ORDER BY i.created_at DESC").fetchall()
    user_rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    users_data = {row['user_id']: dict(row) for row in user_rows}
    current_time = time.time()

    # Ryhmitellään esineet käyttäjittäin koodissa
    grouped_items = {}
    for item in items_rows:
        uid = item['user_id']
        if uid not in grouped_items:
            grouped_items[uid] = []
        grouped_items[uid].append(dict(item))

    html_output = """
    <!DOCTYPE html>
    <html lang="fi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hallintapaneeli</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #6366f1;
                --primary-dark: #4f46e5;
                --danger: #ef4444;
                --bg: #f3f4f6;
                --card: #ffffff;
                --text-main: #1f2937;
                --text-muted: #6b7280;
                --border: #e5e7eb;
            }
            
            body { 
                font-family: 'Inter', sans-serif; 
                background-color: var(--bg); 
                color: var(--text-main); 
                margin: 0; 
                padding: 20px;
            }

            .container { max-width: 1000px; margin: 40px auto; }
            
            header { 
                margin-bottom: 30px; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
            }

            h1 { font-weight: 600; font-size: 1.75rem; margin: 0; letter-spacing: -0.025em; }

            .user-card { 
                background: var(--card); 
                border-radius: 12px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
                margin-bottom: 24px; 
                border: 1px solid var(--border);
                overflow: hidden;
            }

            .user-header { 
                background: #fafafa; 
                padding: 16px 24px; 
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .user-id { font-weight: 600; color: var(--text-main); font-size: 1rem; }
            
            .badge {
                font-size: 0.75rem;
                padding: 4px 10px;
                border-radius: 9999px;
                font-weight: 600;
                margin-left: 10px;
            }
            .badge-key { background: #e0e7ff; color: var(--primary-dark); }
            .badge-expired { background: #fee2e2; color: var(--danger); }

            table { width: 100%; border-collapse: collapse; }
            th { 
                text-align: left; 
                padding: 12px 24px; 
                font-size: 0.75rem; 
                text-transform: uppercase; 
                color: var(--text-muted);
                border-bottom: 1px solid var(--border);
                letter-spacing: 0.05em;
            }

            td { padding: 16px 24px; border-bottom: 1px solid #f9fafb; font-size: 0.9rem; }
            
            .item-title { font-weight: 600; display: block; }
            .time-sub { font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; }

            .btn {
                padding: 7px 14px;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 600;
                cursor: pointer;
                border: 1px solid transparent;
                transition: all 0.15s ease;
                text-decoration: none;
                display: inline-block;
            }

            .btn-danger-light { background: #fff1f2; color: var(--danger); border-color: #fecaca; }
            .btn-danger-light:hover { background: var(--danger); color: white; }

            .btn-ghost { color: var(--text-muted); border-color: var(--border); background: white; }
            .btn-ghost:hover { border-color: var(--danger); color: var(--danger); }

            .empty { padding: 60px; text-align: center; color: var(--text-muted); font-size: 0.9rem; }
            
            a.link { color: var(--primary); font-weight: 500; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Pilvitallennus</h1>
                <div class="time-sub">Palvelimen aika: """ + time.strftime('%H:%M') + """</div>
            </header>
    """

    if not grouped_items:
        html_output += "<div class='user-card'><div class='empty'>Tietokanta on tyhjä.</div></div>"
    else:
        for uid, items in grouped_items.items():
            udata = users_data.get(uid, {'one_time_key': 'N/A', 'key_expiry': 0})
            is_expired = udata['key_expiry'] and current_time > udata['key_expiry']
            
            html_output += f"""
            <div class="user-card">
                <div class="user-header">
                    <div>
                        <span class="user-id">ID: {uid}</span>
                        <span class="badge badge-key">Avain: {udata['one_time_key']}</span>
                        {"<span class='badge badge-expired'>VANHENTUNUT</span>" if is_expired else ""}
                    </div>
                    <form method="POST" action="{url_for('delete_user_data', user_id=uid)}">
                        <button type="submit" class="btn btn-danger-light" onclick="return confirm('Poistetaanko käyttäjä?')">Tyhjennä käyttäjä</button>
                    </form>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Nimi & Luotu</th>
                            <th>Numero / Määrä</th>
                            <th>Linkki</th>
                            <th style="text-align:right">Toiminto</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for item in items:
                # Muunnetaan tallennettu aikaleima muotoon pp.kk.vvvv
                dt = time.strftime('%d.%m.%Y %H:%M', time.gmtime(item['created_at'])) if item['created_at'] else 'Alkuperäinen'
                link_html = f'<a class="link" href="{item["verkkosivu"]}" target="_blank">Avaa</a>' if item['verkkosivu'] else '-'
                
                html_output += f"""
                        <tr>
                            <td>
                                <span class="item-title">{item['nimi']}</span>
                                <div class="time-sub">{dt}</div>
                            </td>
                            <td>
                                <div>{item['numero'] or '-'}</div>
                                <div class="time-sub">{item['maara'] or '-'}</div>
                            </td>
                            <td>{link_html}</td>
                            <td style="text-align:right">
                                <form method="POST" action="{url_for('delete_item_web', item_id=item['id'], user_id=uid)}">
                                    <button type="submit" class="btn btn-ghost">Poista</button>
                                </form>
                            </td>
                        </tr>
                """
            html_output += "</tbody></table></div>"

    html_output += "</div></body></html>"
    return html_output, 200, {'Content-Type': 'text/html'}

# --- API Reitit ---

@app.route('/add_item', methods=['POST'])
def add_item():
    data = request.json
    user_id = data.get('user_id')
    if not user_id: return jsonify({"error": "User ID is required"}), 400

    nimi = data.get('nimi')
    if not nimi: return jsonify({"error": "Nimi is required"}), 400

    # Tallennetaan nykyinen aika Unix-muodossa
    created_at = time.time()

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO items (user_id, nimi, numero, lisatieto, maara, verkkosivu, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, nimi, data.get('numero'), data.get('lisatieto'), data.get('maara'), data.get('verkkosivu'), created_at))
    conn.commit()
    item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    
    return jsonify({"status": "success", "id": item_id, "created_at": created_at}), 201

@app.route('/generate_transfer_key', methods=['POST'])
def generate_transfer_key():
    data = request.json
    user_id = data.get('user_id')
    if not user_id: return jsonify({"error": "User ID is required"}), 400

    key = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    expiry_time = time.time() + 900 # 15 min

    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO users (user_id, one_time_key, key_expiry) VALUES (?, ?, ?)",
                 (user_id, key, expiry_time))
    conn.commit()
    conn.close()

    return jsonify({"one_time_key": key, "expires_in": 900}), 200

@app.route('/get_items', methods=['POST'])
def get_items():
    data = request.json
    user_id = data.get('user_id')
    key = data.get('one_time_key')

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    if not user or user['one_time_key'] != key or time.time() > user['key_expiry']:
        conn.close()
        return jsonify({"error": "Invalid or expired key"}), 403

    items = conn.execute("SELECT * FROM items WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(item) for item in items])

# --- Poistoreitit (Web) ---

@app.route('/delete_item_web/<int:item_id>/<user_id>', methods=['POST'])
def delete_item_web(item_id, user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('all_items_web'))

@app.route('/delete_user_data/<user_id>', methods=['POST'])
def delete_user_data(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM items WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('all_items_web'))

if __name__ == "__main__":
    # Käynnistetään portissa 5001
    app.run(host='0.0.0.0', port=5001)