from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import sqlite3, os, hashlib, uuid
from datetime import timedelta

app = Flask(__name__, static_folder='.')
CORS(app)

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'sigma-secret-2026')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

jwt = JWTManager(app)

DB_PATH = 'sigma_arena.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        name TEXT,
        email TEXT,
        phone TEXT,
        sport TEXT,
        date TEXT,
        slot TEXT,
        amount INTEGER,
        pay_method TEXT,
        status TEXT DEFAULT "Confirmed",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    print("Database ready!")

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    return send_from_directory('.', 'sigma_arena.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not name or not email or not password:
        return jsonify({'error': 'All fields required.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password too short.'}), 400
    conn = get_db()
    c = conn.cursor()
    if c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
        conn.close()
        return jsonify({'error': 'Email already registered.'}), 409
    c.execute('INSERT INTO users (name, email, password) VALUES (?,?,?)',
              (name, email, hash_password(password)))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    token = create_access_token(identity={'id': user_id, 'email': email, 'name': name, 'is_admin': 0})
    return jsonify({'token': token, 'user': {'id': user_id, 'name': name, 'email': email, 'is_admin': 0}}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    conn = get_db()
    c = conn.cursor()
    user = c.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    conn.close()
    if not user or user['password'] != hash_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401
    token = create_access_token(identity={'id': user['id'], 'email': user['email'], 'name': user['name'], 'is_admin': user['is_admin']})
    return jsonify({'token': token, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'is_admin': user['is_admin']}}), 200

@app.route('/api/slots', methods=['GET'])
def get_slots():
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date required.'}), 400
    conn = get_db()
    rows = conn.execute("SELECT slot FROM bookings WHERE date=? AND status='Confirmed'", (date,)).fetchall()
    conn.close()
    return jsonify({'booked_slots': [r['slot'] for r in rows]}), 200

@app.route('/api/payment/offline', methods=['POST'])
@jwt_required()
def offline_payment():
    current_user = get_jwt_identity()
    data = request.get_json()
    sport = data.get('sport')
    date = data.get('date')
    slot = data.get('slot')
    amount = data.get('amount')
    name = data.get('name')
    phone = data.get('phone')
    pay_method = data.get('pay_method', 'cash')
    conn = get_db()
    c = conn.cursor()
    if c.execute("SELECT id FROM bookings WHERE date=? AND slot=? AND status='Confirmed'", (date, slot)).fetchone():
        conn.close()
        return jsonify({'error': 'Slot already booked.'}), 409
    booking_id = 'SA-' + str(uuid.uuid4())[:6].upper()
    c.execute('INSERT INTO bookings (id,user_id,name,email,phone,sport,date,slot,amount,pay_method,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
              (booking_id, current_user['id'], name, current_user['email'], phone, sport, date, slot, amount, pay_method, 'Confirmed'))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Booking confirmed!', 'booking_id': booking_id}), 201

@app.route('/api/bookings/my', methods=['GET'])
@jwt_required()
def my_bookings():
    current_user = get_jwt_identity()
    conn = get_db()
    rows = conn.execute('SELECT * FROM bookings WHERE user_id=? ORDER BY created_at DESC', (current_user['id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/api/bookings/<booking_id>', methods=['DELETE'])
@jwt_required()
def cancel_booking(booking_id):
    current_user = get_jwt_identity()
    conn = get_db()
    c = conn.cursor()
    if not c.execute('SELECT id FROM bookings WHERE id=? AND user_id=?', (booking_id, current_user['id'])).fetchone():
        conn.close()
        return jsonify({'error': 'Not found.'}), 404
    c.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Cancelled.'}), 200

@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def admin_stats():
    conn = get_db()
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    revenue = c.execute("SELECT SUM(amount) FROM bookings").fetchone()[0] or 0
    users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return jsonify({'total': total, 'revenue': revenue, 'users': users}), 200

@app.route('/api/admin/bookings', methods=['GET'])
@jwt_required()
def admin_bookings():
    sport = request.args.get('sport', 'all')
    conn = get_db()
    if sport == 'all':
        rows = conn.execute('SELECT * FROM bookings ORDER BY created_at DESC').fetchall()
    else:
        rows = conn.execute('SELECT * FROM bookings WHERE sport=? ORDER BY created_at DESC', (sport,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/api/admin/bookings/<booking_id>', methods=['DELETE'])
@jwt_required()
def admin_delete(booking_id):
    conn = get_db()
    conn.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Deleted.'}), 200

@app.route('/api/contact', methods=['POST'])
def contact():
    return jsonify({'message': 'Message received!'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
