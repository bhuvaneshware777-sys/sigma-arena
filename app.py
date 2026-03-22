Yes! **Delete everything and paste only this complete code!**

---

## Step 1 — Go to GitHub

```
https://github.com/bhuvaneshware777-sys/sigma-arena
```

## Step 2 — Click app.py → pencil icon ✏️

## Step 3 — Press Ctrl + A then Delete

## Step 4 — Paste this COMPLETE code:

```python
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_mail import Mail, Message
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import sqlite3, os, hashlib, hmac, razorpay, uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'sigma-super-secret-2026')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

jwt = JWTManager(app)
mail = Mail(app)

rz = razorpay.Client(
    auth=(
        os.getenv('RAZORPAY_KEY_ID', 'rzp_test_XXXXXXXXXXXXXXXX'),
        os.getenv('RAZORPAY_KEY_SECRET', 'XXXXXXXXXXXXXXXXXXXXXXXX')
    )
)

DB_PATH = 'sigma_arena.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
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
            razorpay_order_id TEXT,
            razorpay_payment_id TEXT,
            status TEXT DEFAULT "Pending",
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized!")

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_booking_email(to_email, name, booking):
    try:
        msg = Message(
            subject="Booking Confirmed - Sigma Arena",
            recipients=[to_email]
        )
        msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;background:#0d1720;color:#e8f0fe;padding:32px;border-radius:12px;">
          <h1 style="color:#00ffcc;">SIGMA ARENA</h1>
          <h2>Hi {name}!</h2>
          <p>Your slot has been successfully booked.</p>
          <p>Booking ID: <strong>{booking['id']}</strong></p>
          <p>Sport: {booking['sport']}</p>
          <p>Date: {booking['date']}</p>
          <p>Slot: {booking['slot']}</p>
          <p>Amount: Rs.{booking['amount']}</p>
          <p>Please arrive 10 minutes before your slot.</p>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        print(f"Email failed: {e}")

@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'sigma_arena.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not name or not email or not password:
        return jsonify({'error': 'All fields are required.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400
    conn = get_db()
    c = conn.cursor()
    existing = c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Email already registered.'}), 409
    hashed = hash_password(password)
    c.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, hashed))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    token = create_access_token(identity={'id': user_id, 'email': email, 'name': name, 'is_admin': 0})
    return jsonify({'message': 'Registration successful!', 'token': token, 'user': {'id': user_id, 'name': name, 'email': email, 'is_admin': 0}}), 201

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
    return jsonify({'message': 'Login successful!', 'token': token, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'is_admin': user['is_admin']}}), 200

@app.route('/api/slots', methods=['GET'])
def get_slots():
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date required.'}), 400
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT slot FROM bookings WHERE date=? AND status='Confirmed'", (date,)).fetchall()
    conn.close()
    return jsonify({'date': date, 'booked_slots': [row['slot'] for row in rows]}), 200

@app.route('/api/payment/create-order', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    amount = data.get('amount', 0)
    try:
        order = rz.order.create({'amount': int(amount) * 100, 'currency': 'INR', 'receipt': 'sa_' + str(uuid.uuid4())[:8], 'payment_capture': 1})
        return jsonify({'order_id': order['id'], 'amount': order['amount'], 'currency': order['currency'], 'razorpay_key': os.getenv('RAZORPAY_KEY_ID', 'rzp_test_XXXXXXXXXXXXXXXX')}), 200
    except Exception as e:
        return jsonify({'error': 'Payment setup failed.'}), 500

@app.route('/api/payment/verify', methods=['POST'])
@jwt_required()
def verify_payment():
    current_user = get_jwt_identity()
    data = request.get_json()
    razorpay_order_id = data.get('razorpay_order_id', '')
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_signature = data.get('razorpay_signature', '')
    name = data.get('name')
    phone = data.get('phone')
    sport = data.get('sport')
    date = data.get('date')
    slot = data.get('slot')
    amount = data.get('amount')
    try:
        key_secret = os.getenv('RAZORPAY_KEY_SECRET', '').encode()
        msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        expected = hmac.new(key_secret, msg, 'sha256').hexdigest()
        if not hmac.compare_digest(expected, razorpay_signature):
            return jsonify({'error': 'Payment verification failed!'}), 400
    except Exception as e:
        return jsonify({'error': 'Signature error.'}), 400
    conn = get_db()
    c = conn.cursor()
    existing = c.execute("SELECT id FROM bookings WHERE date=? AND slot=? AND status='Confirmed'", (date, slot)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Slot already booked.'}), 409
    booking_id = 'SA-' + str(uuid.uuid4())[:6].upper()
    booking = {'id': booking_id, 'user_id': current_user['id'], 'name': name, 'email': current_user['email'], 'phone': phone, 'sport': sport, 'date': date, 'slot': slot, 'amount': amount, 'pay_method': 'razorpay', 'razorpay_order_id': razorpay_order_id, 'razorpay_payment_id': razorpay_pay
