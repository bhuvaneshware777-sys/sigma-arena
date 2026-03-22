# ============================================================
#  SIGMA ARENA – Flask Backend
#  Tech: Python + Flask + SQLite + JWT + Flask-Mail + Razorpay
# ============================================================

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_mail import Mail, Message
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
import sqlite3, os, hashlib, hmac, razorpay, uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ── Load environment variables from .env file ──────────────
load_dotenv()

# ── Create Flask app ────────────────────────────────────────
app = Flask(__name__, static_folder='.')
CORS(app)  # Allow frontend (HTML) to talk to this server

# ── JWT Configuration ───────────────────────────────────────
app.config['JWT_SECRET_KEY']          = os.getenv('JWT_SECRET', 'sigma-super-secret-2026')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# ── Email (Gmail SMTP) Configuration ───────────────────────
app.config['MAIL_SERVER']         = 'smtp.gmail.com'
app.config['MAIL_PORT']           = 587
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# ── Initialize Extensions ───────────────────────────────────
jwt  = JWTManager(app)
mail = Mail(app)

# ── Razorpay Client ─────────────────────────────────────────
rz = razorpay.Client(
    auth=(
        os.getenv('RAZORPAY_KEY_ID',     'rzp_test_XXXXXXXXXXXXXXXX'),
        os.getenv('RAZORPAY_KEY_SECRET', 'XXXXXXXXXXXXXXXXXXXXXXXX')
    )
)

# ============================================================
#  DATABASE SETUP
# ============================================================

DB_PATH = 'sigma_arena.db'

def get_db():
    """Open a database connection and return rows as dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us use row['column'] syntax
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = get_db()
    c    = conn.cursor()

    # ── Users table ─────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            is_admin   INTEGER DEFAULT 0,
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Bookings table ───────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id                  TEXT    PRIMARY KEY,
            user_id             INTEGER,
            name                TEXT,
            email               TEXT,
            phone               TEXT,
            sport               TEXT,
            date                TEXT,
            slot                TEXT,
            amount              INTEGER,
            pay_method          TEXT,
            razorpay_order_id   TEXT,
            razorpay_payment_id TEXT,
            status              TEXT DEFAULT "Pending",
            created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized!")


# Run DB setup when server starts
init_db()


# ============================================================
#  HELPER FUNCTIONS
# ============================================================

def hash_password(password: str) -> str:
    """Hash a plain-text password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def send_booking_email(to_email: str, name: str, booking: dict):
    """Send an HTML booking confirmation email."""
    try:
        msg = Message(
            subject = "✅ Booking Confirmed – Sigma Arena",
            recipients = [to_email]
        )
        msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;
                    background:#0d1720;color:#e8f0fe;padding:32px;border-radius:12px;">
          <h1 style="color:#00ffcc;font-size:28px;margin-bottom:4px;">SIGMA ARENA</h1>
          <p style="color:#7a9bbf;margin-bottom:24px;">Turf Booking Confirmation</p>

          <h2 style="font-size:20px;">Hi {name}! 👋</h2>
          <p>Your slot has been successfully booked. Here are your details:</p>

          <table style="width:100%;border-collapse:collapse;margin:20px 0;">
            <tr style="border-bottom:1px solid #1f3a50;">
              <td style="padding:10px;color:#7a9bbf;">Booking ID</td>
              <td style="padding:10px;font-weight:bold;color:#00ffcc;">{booking['id']}</td>
            </tr>
            <tr style="border-bottom:1px solid #1f3a50;">
              <td style="padding:10px;color:#7a9bbf;">Sport</td>
              <td style="padding:10px;">{booking['sport']}</td>
            </tr>
            <tr style="border-bottom:1px solid #1f3a50;">
              <td style="padding:10px;color:#7a9bbf;">Date</td>
              <td style="padding:10px;">{booking['date']}</td>
            </tr>
            <tr style="border-bottom:1px solid #1f3a50;">
              <td style="padding:10px;color:#7a9bbf;">Time Slot</td>
              <td style="padding:10px;">{booking['slot']}</td>
            </tr>
            <tr>
              <td style="padding:10px;color:#7a9bbf;">Amount Paid</td>
              <td style="padding:10px;color:#00ffcc;font-size:18px;font-weight:bold;">
                ₹{booking['amount']:,}
              </td>
            </tr>
          </table>

          <p style="color:#7a9bbf;font-size:13px;">
            Please arrive 10 minutes before your slot. Show this email at reception.
          </p>
          <p style="color:#7a9bbf;font-size:12px;margin-top:24px;">
            © 2026 Sigma Arena · enquire@sigmaarena.com · +91 98765 43210
          </p>
        </div>
        """
        mail.send(msg)
        print(f"📧 Email sent to {to_email}")
    except Exception as e:
        # Don't crash the server if email fails — just log it
        print(f"⚠️  Email failed: {e}")


# ============================================================
#  SERVE FRONTEND
# ============================================================

@app.route('/')
def serve_frontend():
    """Serve the main HTML file."""
    return send_from_directory('.', 'sigma_arena.html')


# ============================================================
#  AUTH ROUTES
# ============================================================

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()

    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # Basic validation
    if not name or not email or not password:
        return jsonify({'error': 'All fields are required.'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    conn = get_db()
    c    = conn.cursor()

    # Check if email already exists
    existing = c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Email already registered. Please login.'}), 409

    # Save new user
    hashed = hash_password(password)
    c.execute(
        'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
        (name, email, hashed)
    )
    conn.commit()
    user_id = c.lastrowid
    conn.close()

    # Create JWT token
    token = create_access_token(identity={'id': user_id, 'email': email, 'name': name, 'is_admin': 0})

    return jsonify({
        'message': 'Registration successful!',
        'token': token,
        'user': {'id': user_id, 'name': name, 'email': email, 'is_admin': 0}
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    """Login an existing user."""
    data = request.get_json()

    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    conn = get_db()
    c    = conn.cursor()

    user = c.execute(
        'SELECT * FROM users WHERE email=?', (email,)
    ).fetchone()
    conn.close()

    if not user or user['password'] != hash_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    # Create JWT token
    token = create_access_token(identity={
        'id':       user['id'],
        'email':    user['email'],
        'name':     user['name'],
        'is_admin': user['is_admin']
    })

    return jsonify({
        'message': 'Login successful!',
        'token': token,
        'user': {
            'id':       user['id'],
            'name':     user['name'],
            'email':    user['email'],
            'is_admin': user['is_admin']
        }
    }), 200


# ============================================================
#  SLOT AVAILABILITY
# ============================================================

@app.route('/api/slots', methods=['GET'])
def get_slots():
    """Return which slots are already booked for a given date."""
    date = request.args.get('date')

    if not date:
        return jsonify({'error': 'Date parameter is required.'}), 400

    conn = get_db()
    c    = conn.cursor()

    rows = c.execute(
        "SELECT slot FROM bookings WHERE date=? AND status='Confirmed'",
        (date,)
    ).fetchall()
    conn.close()

    booked_slots = [row['slot'] for row in rows]
    return jsonify({'date': date, 'booked_slots': booked_slots}), 200


# ============================================================
#  PAYMENT ROUTES (Razorpay)
# ============================================================

@app.route('/api/payment/create-order', methods=['POST'])
@jwt_required()
def create_order():
    """Create a Razorpay order before showing payment popup."""
    data   = request.get_json()
    amount = data.get('amount', 0)  # in rupees

    try:
        order = rz.order.create({
            'amount':   int(amount) * 100,   # Razorpay needs paise (1 rupee = 100 paise)
            'currency': 'INR',
            'receipt':  'sa_' + str(uuid.uuid4())[:8],
            'payment_capture': 1             # Auto capture payment
        })
        return jsonify({
            'order_id':    order['id'],
            'amount':      order['amount'],
            'currency':    order['currency'],
            'razorpay_key': os.getenv('RAZORPAY_KEY_ID', 'rzp_test_XXXXXXXXXXXXXXXX')
        }), 200

    except Exception as e:
        print(f"Razorpay order error: {e}")
        return jsonify({'error': 'Payment setup failed. Try again.'}), 500


@app.route('/api/payment/verify', methods=['POST'])
@jwt_required()
def verify_payment():
    """
    After Razorpay processes payment, verify the signature
    and save the booking to database.
    """
    current_user = get_jwt_identity()
    data         = request.get_json()

    # ── Razorpay fields ──────────────────────────────────────
    razorpay_order_id   = data.get('razorpay_order_id',   '')
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_signature  = data.get('razorpay_signature',  '')

    # ── Booking fields ───────────────────────────────────────
    name       = data.get('name')
    phone      = data.get('phone')
    sport      = data.get('sport')
    date       = data.get('date')
    slot       = data.get('slot')
    amount     = data.get('amount')
    pay_method = data.get('pay_method', 'razorpay')

    # ── Verify Razorpay signature ────────────────────────────
    try:
        key_secret = os.getenv('RAZORPAY_KEY_SECRET', '').encode()
        msg        = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        expected   = hmac.new(key_secret, msg, 'sha256').hexdigest()

        if not hmac.compare_digest(expected, razorpay_signature):
            return jsonify({'error': 'Payment verification failed!'}), 400
    except Exception as e:
        print(f"Signature verify error: {e}")
        return jsonify({'error': 'Signature error.'}), 400

    # ── Check slot still available ───────────────────────────
    conn = get_db()
    c    = conn.cursor()

    existing = c.execute(
        "SELECT id FROM bookings WHERE date=? AND slot=? AND status='Confirmed'",
        (date, slot)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({'error': 'This slot was just booked by someone else. Please choose another.'}), 409

    # ── Save booking ─────────────────────────────────────────
    booking_id = 'SA-' + str(uuid.uuid4())[:6].upper()
    booking = {
        'id':                  booking_id,
        'user_id':             current_user['id'],
        'name':                name,
        'email':               current_user['email'],
        'phone':               phone,
        'sport':               sport,
        'date':                date,
        'slot':                slot,
        'amount':              amount,
        'pay_method':          pay_method,
        'razorpay_order_id':   razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'status':              'Confirmed'
    }

    c.execute('''
        INSERT INTO bookings
          (id, user_id, name, email, phone, sport, date, slot, amount,
           pay_method, razorpay_order_id, razorpay_payment_id, status)
        VALUES
          (:id, :user_id, :name, :email, :phone, :sport, :date, :slot, :amount,
           :pay_method, :razorpay_order_id, :razorpay_payment_id, :status)
    ''', booking)

    conn.commit()
    conn.close()

    # ── Send confirmation email ──────────────────────────────
    send_booking_email(current_user['email'], current_user['name'], booking)

    return jsonify({
        'message':    'Booking confirmed!',
        'booking_id': booking_id,
        'booking':    booking
    }), 201


# ── Cash / UPI (no Razorpay) booking ────────────────────────
@app.route('/api/payment/offline', methods=['POST'])
@jwt_required()
def offline_payment():
    """Save booking with cash/offline UPI — no Razorpay needed."""
    current_user = get_jwt_identity()
    data         = request.get_json()

    name       = data.get('name')
    phone      = data.get('phone')
    sport      = data.get('sport')
    date       = data.get('date')
    slot       = data.get('slot')
    amount     = data.get('amount')
    pay_method = data.get('pay_method', 'cash')

    # Check slot availability
    conn = get_db()
    c    = conn.cursor()

    existing = c.execute(
        "SELECT id FROM bookings WHERE date=? AND slot=? AND status='Confirmed'",
        (date, slot)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({'error': 'Slot already booked. Pick another.'}), 409

    booking_id = 'SA-' + str(uuid.uuid4())[:6].upper()
    booking = {
        'id':          booking_id,
        'user_id':     current_user['id'],
        'name':        name,
        'email':       current_user['email'],
        'phone':       phone,
        'sport':       sport,
        'date':        date,
        'slot':        slot,
        'amount':      amount,
        'pay_method':  pay_method,
        'status':      'Confirmed'
    }

    c.execute('''
        INSERT INTO bookings
          (id, user_id, name, email, phone, sport, date, slot, amount, pay_method, status)
        VALUES
          (:id, :user_id, :name, :email, :phone, :sport, :date, :slot, :amount, :pay_method, :status)
    ''', booking)

    conn.commit()
    conn.close()

    send_booking_email(current_user['email'], current_user['name'], booking)

    return jsonify({
        'message':    'Booking confirmed!',
        'booking_id': booking_id,
        'booking':    booking
    }), 201


# ============================================================
#  USER BOOKINGS
# ============================================================

@app.route('/api/bookings/my', methods=['GET'])
@jwt_required()
def my_bookings():
    """Return all bookings for the logged-in user."""
    current_user = get_jwt_identity()

    conn = get_db()
    c    = conn.cursor()

    rows = c.execute(
        'SELECT * FROM bookings WHERE user_id=? ORDER BY created_at DESC',
        (current_user['id'],)
    ).fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows]), 200


@app.route('/api/bookings/<booking_id>', methods=['DELETE'])
@jwt_required()
def cancel_booking(booking_id):
    """Cancel / delete a booking (user can only cancel their own)."""
    current_user = get_jwt_identity()

    conn = get_db()
    c    = conn.cursor()

    # Make sure the booking belongs to this user
    row = c.execute(
        'SELECT * FROM bookings WHERE id=? AND user_id=?',
        (booking_id, current_user['id'])
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'Booking not found or access denied.'}), 404

    c.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Booking cancelled successfully.'}), 200


# ============================================================
#  ADMIN ROUTES
# ============================================================

def require_admin():
    """Helper – return error if logged-in user is not admin."""
    identity = get_jwt_identity()
    if not identity.get('is_admin'):
        return jsonify({'error': 'Admin access required.'}), 403
    return None


@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def admin_stats():
    """Dashboard statistics for admin panel."""
    err = require_admin()
    if err: return err

    conn = get_db()
    c    = conn.cursor()

    total      = c.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'").fetchone()[0]
    football   = c.execute("SELECT COUNT(*) FROM bookings WHERE sport='Football' AND status='Confirmed'").fetchone()[0]
    cricket    = c.execute("SELECT COUNT(*) FROM bookings WHERE sport='Cricket'  AND status='Confirmed'").fetchone()[0]
    badminton  = c.execute("SELECT COUNT(*) FROM bookings WHERE sport='Badminton'AND status='Confirmed'").fetchone()[0]
    midnight   = c.execute("SELECT COUNT(*) FROM bookings WHERE sport='Midnight' AND status='Confirmed'").fetchone()[0]
    revenue    = c.execute("SELECT SUM(amount) FROM bookings WHERE status='Confirmed'").fetchone()[0] or 0
    users      = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    return jsonify({
        'total':     total,
        'football':  football,
        'cricket':   cricket,
        'badminton': badminton,
        'midnight':  midnight,
        'revenue':   revenue,
        'users':     users
    }), 200


@app.route('/api/admin/bookings', methods=['GET'])
@jwt_required()
def admin_all_bookings():
    """Return ALL bookings (optionally filter by sport)."""
    err = require_admin()
    if err: return err

    sport  = request.args.get('sport', 'all')
    conn   = get_db()
    c      = conn.cursor()

    if sport == 'all':
        rows = c.execute('SELECT * FROM bookings ORDER BY created_at DESC').fetchall()
    else:
        rows = c.execute(
            'SELECT * FROM bookings WHERE sport=? ORDER BY created_at DESC', (sport,)
        ).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows]), 200


@app.route('/api/admin/bookings/<booking_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_booking(booking_id):
    """Admin can delete any booking."""
    err = require_admin()
    if err: return err

    conn = get_db()
    c    = conn.cursor()
    c.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Booking deleted.'}), 200


@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def admin_all_users():
    """Return all registered users."""
    err = require_admin()
    if err: return err

    conn = get_db()
    c    = conn.cursor()
    rows = c.execute('SELECT id,name,email,is_admin,created_at FROM users ORDER BY created_at DESC').fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows]), 200


@app.route('/api/admin/make-admin', methods=['POST'])
@jwt_required()
def make_admin():
    """Promote a user to admin by email."""
    err = require_admin()
    if err: return err

    email = request.get_json().get('email', '').lower()
    conn  = get_db()
    c     = conn.cursor()
    c.execute('UPDATE users SET is_admin=1 WHERE email=?', (email,))
    conn.commit()
    conn.close()
    return jsonify({'message': f'{email} is now an admin.'}), 200


# ============================================================
#  CONTACT MESSAGE
# ============================================================

@app.route('/api/contact', methods=['POST'])
def contact():
    """Receive a contact form message and email it to admin."""
    data    = request.get_json()
    name    = data.get('name','').strip()
    email   = data.get('email','').strip()
    message = data.get('message','').strip()

    if not name or not email or not message:
        return jsonify({'error': 'All fields are required.'}), 400

    try:
        msg = Message(
            subject    = f"📩 New Contact Message from {name} – Sigma Arena",
            recipients = [os.getenv('MAIL_USERNAME', 'enquire@sigmaarena.com')]
        )
        msg.body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        mail.send(msg)
    except Exception as e:
        print(f"Contact email error: {e}")

    return jsonify({'message': 'Message received! We will reply within 24 hours.'}), 200


# ============================================================
#  RUN SERVER
# ============================================================
if __name__ == '__main__':
    print("🚀 Sigma Arena Backend starting...")
    print("📍 Open: http://localhost:5000")
    app.run(debug=True, port=5000)
