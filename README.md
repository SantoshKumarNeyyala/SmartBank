# 🏦 SmartBank – Real World Banking System (Flask + SQL Server)

SmartBank is a production-style banking simulation system built using Flask and Microsoft SQL Server.  
It demonstrates secure transaction handling, fraud detection logic, OTP verification, audit logging, analytics APIs, PDF statement generation, and export features.

This project follows layered architecture (routes → services → models → utils) and includes unit testing and production server configuration.

---

# 🚀 Features

## 🔐 Authentication & Security
- User Registration & Login
- Account lock after failed login attempts
- Password hashing using Flask-Bcrypt
- CSRF protection (Flask-WTF)
- Rate limiting (Flask-Limiter)
- Secure session cookies
- Production logging with rotating log files

## 🏦 Banking Core
- Multiple bank accounts per user
- Account selection
- Create / Close account
- Deposit (Idempotency protected)
- Withdraw (Balance protected)
- Transfer with:
  - Fraud risk scoring
  - OTP verification
  - Step-up authentication
  - Daily & per-transaction limits

## 📊 Monitoring & Admin
- Fraud monitoring dashboard
- Audit logging system
- Transaction history view
- Last 7 days analytics API

## 📄 Reports & Export
- PDF statement download (ReportLab)
- Export transactions as CSV
- Export transactions as JSON

## 🧪 Testing
- Pytest test suite
- Coverage reporting
- Mock-based service testing (no DB dependency)

## 🖥 Production Setup
- App factory pattern
- Environment configuration (.env)
- Waitress production server
- Logging to file + console

---

# 🛠 Tech Stack

- Python 3.10+
- Flask
- SQL Server (SSMS) + pyodbc
- Flask-Bcrypt
- Flask-WTF (CSRF)
- Flask-Limiter
- ReportLab (PDF generation)
- Pytest + Coverage
- Waitress (Production WSGI server)

---

# 📂 Project Structure

```
SmartBank/
│
├── app.py
├── config.py
├── wsgi.py
├── extension.py
│
├── routes/
│   ├── auth_routes.py
│   └── bank_routes.py
│
├── services/
├── models/
├── database/
├── utils/
│
├── templates/
├── static/
│
├── tests/
├── logs/
└── README.md
```

---

# ⚙️ Setup Instructions (Windows)

## 1️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

## 3️⃣ Create .env File

Create a `.env` file in the project root:

```env
ENV=development
SECRET_KEY=dev-secret

DB_DRIVER=ODBC Driver 17 for SQL Server
DB_SERVER=DESKTOP-NS3OVRH\SQLEXPRESS
DB_NAME=SmartBank

MAX_TRANSFER_PER_TX=50000.00
MAX_TRANSFER_PER_DAY=500000.00
```

## 4️⃣ Run Application (Development)

```bash
python app.py
```

Open in browser:

```
http://127.0.0.1:5000
```

---

# 🏭 Run in Production Mode (Waitress)

Install Waitress:

```bash
pip install waitress
```

Run:

```bash
waitress-serve --host=127.0.0.1 --port=5000 wsgi:app
```

---

# 🧪 Run Tests

```bash
pytest
coverage run -m pytest
coverage report -m
```

---

# 📊 Example API Endpoint

Analytics (last 7 days):

```
GET /api/analytics/last7days
```

Returns JSON:

```json
{
  "labels": ["2026-02-18", "2026-02-19"],
  "deposits": [2000, 1500],
  "withdraws": [500, 300]
}
```

---

# 🔒 Security Concepts Implemented

- Idempotency keys to prevent duplicate transactions
- Fraud risk decision engine (allow / stepup / block)
- OTP session validation
- Audit logging for all sensitive actions
- Rate limiting to prevent abuse
- Account lock mechanism

---

# 📈 Future Enhancements

- Google Authenticator (TOTP based 2FA)
- Interest calculation engine
- Role-based admin authorization decorator
- Full REST API architecture with JWT
- React or Angular frontend integration
- Docker containerization

---

# 👨‍💻 Author

Santosh Kumar (Sandy)  
B.Tech – Information Technology  

Built as a real-world banking system simulation project to demonstrate:
- Backend development skills
- Secure banking workflow simulation
- SQL Server integration
- Production-ready Flask application design
- Unit testing and deployment practices 

---

# 📜 License

This project is for educational and demonstration purposes.