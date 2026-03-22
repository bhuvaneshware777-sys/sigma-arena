# 🏟️ SIGMA ARENA – Backend Setup Guide
## Beginner-Friendly Step-by-Step Instructions

---

## 📁 YOUR PROJECT FILES

```
sigma_arena_project/
├── app.py               ← Flask backend (main server)
├── sigma_arena.html     ← Frontend (your website)
├── requirements.txt     ← Python packages list
├── .env.example         ← Copy this to .env and fill values
├── sigma_arena.db       ← SQLite database (auto-created on first run)
└── [your image files]   ← turf pic uid.jpg, Football.jpg, etc.
```

---

## ✅ STEP 1 – Install Python

1. Go to https://python.org/downloads
2. Download Python 3.11 or newer
3. **IMPORTANT:** Check the box ✅ "Add Python to PATH" during install
4. Click Install Now

**Verify it works:**
Open Command Prompt (Windows) or Terminal (Mac) and type:
```
python --version
```
You should see: `Python 3.11.x`

---

## ✅ STEP 2 – Install All Python Packages

Open Command Prompt / Terminal in your project folder and run:

```bash
pip install -r requirements.txt
```

This installs:
- **flask** – The web framework (your server)
- **flask-cors** – Allows frontend to talk to backend
- **flask-mail** – Sends real emails via Gmail
- **flask-jwt-extended** – Handles login tokens
- **python-dotenv** – Reads your .env file
- **razorpay** – Payment gateway

---

## ✅ STEP 3 – Create Your .env File

1. Copy `.env.example` and rename the copy to `.env`
2. Open `.env` in Notepad and fill in your values:

```
JWT_SECRET=sigma-arena-change-this-2026

MAIL_USERNAME=yourgmail@gmail.com
MAIL_PASSWORD=your_gmail_app_password

RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXXXXX
RAZORPAY_KEY_SECRET=XXXXXXXXXXXXXXXXXXXXXXXX
```

### 📧 How to get Gmail App Password:
1. Go to https://myaccount.google.com
2. Click **Security** on the left
3. Turn ON **2-Step Verification**
4. Go to **App Passwords**
5. Select "Mail" → Generate
6. Copy the 16-character code → paste in `.env` as MAIL_PASSWORD

### 💳 How to get Razorpay Test Keys:
1. Go to https://dashboard.razorpay.com
2. Sign up for free (no real money needed for testing)
3. Go to **Settings → API Keys**
4. Click **Generate Test Key**
5. Copy Key ID and Key Secret → paste in `.env`

---

## ✅ STEP 4 – Run the Flask Server

In your project folder, run:

```bash
python app.py
```

You should see:
```
✅ Database initialized!
🚀 Sigma Arena Backend starting...
📍 Open: http://localhost:5000
 * Running on http://127.0.0.1:5000
```

**DO NOT close this terminal window while using the site!**

---

## ✅ STEP 5 – Open the Website

Open your browser and go to:
```
http://localhost:5000
```

The website will open! You should see **🟢 Backend Connected** in the bottom-left corner.

---

## 🛠️ STEP 6 – Create an Admin Account

1. Sign up on the website normally (e.g., admin@sigmaarena.com)
2. Open a **new terminal** in your project folder
3. Run:
```bash
python
```
4. Then type these commands one by one:
```python
import sqlite3
conn = sqlite3.connect('sigma_arena.db')
conn.execute("UPDATE users SET is_admin=1 WHERE email='admin@sigmaarena.com'")
conn.commit()
conn.close()
print("Admin created!")
exit()
```
5. Log out and log back in → you'll see the **Admin Dashboard** section

---

## 🔍 WHAT EACH API ROUTE DOES

| Route | Method | What it does |
|-------|--------|-------------|
| `/api/register` | POST | Create new user account |
| `/api/login` | POST | Login, get JWT token |
| `/api/slots?date=YYYY-MM-DD` | GET | Check which slots are booked |
| `/api/payment/create-order` | POST | Create Razorpay order |
| `/api/payment/verify` | POST | Verify payment + save booking |
| `/api/payment/offline` | POST | Book with cash/UPI (no Razorpay) |
| `/api/bookings/my` | GET | Get your own bookings |
| `/api/bookings/<id>` | DELETE | Cancel your booking |
| `/api/admin/stats` | GET | Dashboard numbers |
| `/api/admin/bookings` | GET | All bookings (admin only) |
| `/api/admin/users` | GET | All users (admin only) |
| `/api/contact` | POST | Send contact email |

---

## 💾 WHERE IS DATA STORED?

Everything is saved in **sigma_arena.db** (SQLite database file).

You can view this database using:
- **DB Browser for SQLite** (free): https://sqlitebrowser.org
- Just open the .db file and see all your tables!

### Tables:
- **users** – name, email, password (hashed), is_admin
- **bookings** – all booking details, Razorpay IDs, status

---

## ⚠️ COMMON ERRORS & FIXES

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install -r requirements.txt` again |
| `Address already in use` | Another program is using port 5000. Close it or change port in app.py |
| `🔴 Backend Offline` on website | Make sure `python app.py` is running in terminal |
| Email not sending | Check Gmail App Password in .env, not your regular Gmail password |
| Payment not working | Make sure Razorpay test keys are correct in .env |
| `401 Unauthorized` | Your session expired. Logout and login again |

---

## 🧪 TESTING WITHOUT REAL PAYMENT

For Razorpay test mode, use these test card details:
- **Card Number:** 4111 1111 1111 1111
- **Expiry:** Any future date (e.g., 12/29)
- **CVV:** Any 3 digits (e.g., 123)
- **OTP:** 1234 (test OTP)

No real money is charged in test mode!

---

## 📦 TECH STACK SUMMARY

| Layer | Technology |
|-------|-----------|
| Frontend | HTML + CSS + Vanilla JS |
| Backend | Python + Flask |
| Database | SQLite (sigma_arena.db) |
| Auth | JWT (JSON Web Tokens) |
| Email | Flask-Mail + Gmail SMTP |
| Payment | Razorpay API |
| API Style | REST API |

---

## 🎓 This is a full-stack mini project!

**Frontend** → HTML/CSS/JS sends requests to Flask  
**Backend** → Flask receives requests, talks to SQLite database  
**Database** → SQLite stores users, bookings permanently  
**Email** → Flask-Mail sends real confirmation emails  
**Payment** → Razorpay handles secure payments  

---

*© 2026 Sigma Arena | Designed by Bhuvaneshware JK*
