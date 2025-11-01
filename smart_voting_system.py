#!/usr/bin/env python3
"""
smart_voting_system.py
Single-file prototype: Smart Voting Machine + Admin UI to add and manage voters.


This version is streamlined to only include QR and fingerprint verification,
with all face recognition concepts removed.


Run:
  1) python3 -m venv venv
  2) source venv/bin/activate  (Unix)  or  venv\\Scripts\\activate (Windows)
  3) pip install Flask numpy
  4) python smart_voting_system.py
  5) Open http://127.0.0.1:5000  and http://127.0.0.1:5000/admin


This is a demo. NOT secure for production.
"""
import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path


from flask import (Flask, flash, redirect, render_template_string, request,
                   send_file, session, url_for, jsonify)


# App and DB config
APP = Flask(__name__)
APP.secret_key = os.environ.get("SVM_SECRET_KEY", "svm_demo_secret_key_change_me")
BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "svm_admin.db"


# Admin credentials
ADMIN_USER = "poomalai005"
ADMIN_PASS = "Poomalai2005@"
VOTED_STATUS_PASSWORD = "989464"


# Set up basic logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


# Ensure DB
def get_conn():
    """Returns a new database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite database tables if they don't exist."""
    created = not DB_PATH.exists()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT UNIQUE,
            name TEXT,
            dob TEXT,
            phone TEXT,
            fingerprint TEXT,
            has_voted INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT,
            candidate TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()
    return created


init_db()


# Utility functions
def calculate_age(dob_str):
    """Calculates age in years from a YYYY-MM-DD date string."""
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except Exception:
        return -1
    today = datetime.utcnow().date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age


def send_sms(to_number, message):
    """
    Simulates sending an SMS notification.
    In a real-world scenario, this would use a service like Twilio or Vonage.
    For this demo, we'll log the message to the console.
    """
    logging.info(f"Simulating SMS to {to_number}: {message}")


# --------------------
# Admin pages (using render_template_string)
# --------------------
ADMIN_LOGIN_HTML = """
<!doctype html>
<title>Admin Login</title>
<style>
body{font-family: Arial; max-width: 500px; margin: 20px auto; padding: 15px; background-color: #000; color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(255,255,255,0.1);}
h2{color: #fff; text-align: center;}
form{display: flex; flex-direction: column; gap: 10px;}
input{padding: 10px; border-radius: 5px; border: 1px solid #555; background-color: #333; color: #fff;}
button{padding: 10px; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;}
a{color: #3498db;}
</style>
<h2>Admin login</h2>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <ul>
    {% for cat, msg in messages %}
      <li><strong>{{ cat }}:</strong> {{ msg }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
<form method="post">
  <label>Username: <input name="username" required></label>
  <label>Password: <input name="password" type="password" required></label>
  <button type="submit">Login</button>
</form>
<p><a href="{{ url_for('index') }}">Back to Voting</a></p>
"""


ADMIN_ADD_HTML = """
<!doctype html>
<title>Add Voter</title>
<style>
body{font-family: Arial; max-width: 700px; margin: 20px auto; padding: 15px; background-color: #000; color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(255,255,255,0.1);}
h2{color: #fff; text-align: center;}
p a{color: #3498db;}
form{display: flex; flex-direction: column; gap: 10px;}
label{font-weight: bold;}
input{padding: 10px; border-radius: 5px; border: 1px solid #555; background-color: #333; color: #fff;}
button{padding: 10px; background-color: #28a745; color: white; border: none; cursor: pointer;}
</style>
<h2>Admin — Add Voter</h2>
<p><a href="{{ url_for('admin_list') }}">List voters</a> | <a href="{{ url_for('admin_logout') }}">Logout</a></p>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <ul>
    {% for cat, msg in messages %}
      <li><strong>{{ cat }}:</strong> {{ msg }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
<form method="post">
  <label>Voter QR ID (unique): <input name="voter_id" required></label>
  <label>Name: <input name="name" required></label>
  <label>DOB (YYYY-MM-DD): <input name="dob" required></label>
  <label>Phone: <input name="phone"></label>
  <label>Fingerprint template (text placeholder): <input name="fingerprint"></label>
  <br>
  <button type="submit">Add Voter</button>
</form>
"""


ADMIN_EDIT_HTML = """
<!doctype html>
<title>Edit Voter</title>
<style>
body{font-family: Arial; max-width: 700px; margin: 20px auto; padding: 15px; background-color: #000; color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(255,255,255,0.1);}
h2{color: #fff; text-align: center;}
p a{color: #3498db;}
form{display: flex; flex-direction: column; gap: 10px;}
label{font-weight: bold;}
input{padding: 10px; border-radius: 5px; border: 1px solid #555; background-color: #333; color: #fff;}
button{padding: 10px; background-color: #28a745; color: white; border: none; cursor: pointer;}
</style>
<h2>Admin — Edit Voter</h2>
<p><a href="{{ url_for('admin_list') }}">List voters</a> | <a href="{{ url_for('admin_add') }}">Add voter</a> | <a href="{{ url_for('admin_logout') }}">Logout</a></p>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <ul>
    {% for cat, msg in messages %}
      <li><strong>{{ cat }}:</strong> {{ msg }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
<form method="post">
  <label>Voter QR ID: <input name="voter_id" value="{{ voter.voter_id }}" readonly></label>
  <label>Name: <input name="name" value="{{ voter.name }}" required></label>
  <label>DOB (YYYY-MM-DD): <input name="dob" value="{{ voter.dob }}" required></label>
  <label>Phone: <input name="phone" value="{{ voter.phone }}"></label>
  <label>Fingerprint template (text placeholder): <input name="fingerprint" value="{{ voter.fingerprint }}"></label>
  <br>
  <button type="submit">Update Voter</button>
</form>
"""


ADMIN_LIST_HTML = """
<!doctype html>
<title>Voters</title>
<style>
body{font-family: Arial; max-width: 900px; margin: 20px auto; padding: 15px; background-color: #000; color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(255,255,255,0.1);}
h2{color: #fff; text-align: center;}
p a{color: #3498db;}
table{width: 100%; border-collapse: collapse; margin-top: 15px;}
th, td{border: 1px solid #555; padding: 8px; text-align: left;}
th{background-color: #333;}
button{padding: 5px 10px; color: white; border: none; border-radius: 4px; cursor: pointer;}
button.edit { background-color: #3498db; }
button.delete { background-color: #dc3545; margin-left: 5px; }
button.toggle { background-color: #555; margin-left: 5px; }
.toggle-form { display: inline-flex; align-items: center; gap: 5px; }
</style>
<h2>Registered Voters</h2>
<p><a href="{{ url_for('admin_add') }}">Add voter</a> | <a href="{{ url_for('admin_logout') }}">Logout</a></p>
<table border="1" cellpadding="6">
<tr><th>ID</th><th>Voter QR ID</th><th>Name</th><th>DOB</th><th>Phone</th><th>Has Voted</th><th>Actions</th></tr>
{% for v in voters %}
  <tr>
    <td>{{ v.id }}</td>
    <td>{{ v.voter_id }}</td>
    <td>{{ v.name }}</td>
    <td>{{ v.dob }}</td>
    <td>{{ v.phone }}</td>
    <td>{{ 'Yes' if v.has_voted else 'No' }}</td>
    <td>
      <a href="{{ url_for('admin_edit', voter_id=v.voter_id) }}"><button class="edit">Edit</button></a>
      <form method="post" action="{{ url_for('admin_delete', voter_id=v.voter_id) }}" style="display:inline" onsubmit="return confirm('Delete voter?');">
          <button class="delete" type="submit">Delete</button>
      </form>
      <form method="post" action="{{ url_for('admin_update_voted_status', voter_id=v.voter_id) }}" class="toggle-form" onsubmit="return confirm('Change voted status for {{ v.voter_id }}?');">
          <input type="password" name="password" placeholder="Password" style="width: 80px;" required>
          <button class="toggle" type="submit">Toggle Voted</button>
      </form>
    </td>
  </tr>
{% endfor %}
</table>
"""


# --------------------
# Voting UI & API
# --------------------
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Smart Voting</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    
    body {
        font-family: 'Roboto', sans-serif;
        max-width: 900px;
        margin: 20px auto;
        padding: 15px;
        color: #fff;
        line-height: 1.6;
        background-color: #000;
        border-radius: 12px;
    }
    .container {
        background-color: #1a1a1a;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(255, 255, 255, 0.1);
        transition: transform 0.3s ease;
    }
    .container:hover {
        transform: translateY(-5px);
    }
    h1, h2, h3 {
        color: #fff;
        border-bottom: 2px solid #3498db;
        padding-bottom: 5px;
        margin-top: 20px;
    }
    h1 {
        font-size: 3em;
        color: #e6e9f0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    p {
        color: #ccc;
    }
    .status-message {
        font-weight: 700;
        margin-top: 10px;
        padding: 8px 12px;
        border-radius: 5px;
        border: 1px solid transparent;
        transition: all 0.3s ease;
        animation: fade-in 0.5s ease;
    }
    .status-message.success {
        color: #2ecc71;
        background-color: rgba(46, 204, 113, 0.2);
        border-color: #2ecc71;
    }
    .status-message.error {
        color: #e74c3c;
        background-color: rgba(231, 76, 60, 0.2);
        border-color: #e74c3c;
    }
    input, button {
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #555;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    input {
        flex-grow: 1;
        margin-right: 10px;
        background-color: #333;
        color: #fff;
    }
    button {
        background-color: #3498db;
        color: white;
        border: none;
        cursor: pointer;
        padding: 12px 25px;
        box-shadow: 0 4px 6px rgba(52, 152, 219, 0.3);
    }
    button:hover {
        background-color: #2980b9;
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 15px rgba(52, 152, 219, 0.4);
    }
    button.candidate {
        background-color: #e74c3c; /* Red for candidates */
    }
    button.candidate:hover {
        background-color: #c0392b;
        transform: translateY(-3px) scale(1.02);
    }
    .step-section {
        margin-bottom: 25px;
        padding: 20px;
        border: 1px dashed #555;
        border-radius: 10px;
        transition: opacity 0.5s ease;
    }
    .flex-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    #reader {
        width: 100%;
        max-width: 500px;
        margin: 0 auto;
    }
    
    /* Custom Modal CSS */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s ease, visibility 0.3s ease;
    }
    .modal-overlay.visible {
        opacity: 1;
        visibility: visible;
    }
    .modal-content {
        background: #1a1a1a;
        padding: 30px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        max-width: 400px;
        width: 90%;
        transform: translateY(-20px);
        transition: transform 0.3s ease;
    }
    .modal-overlay.visible .modal-content {
        transform: translateY(0);
    }
    .modal-content h3 {
        margin-top: 0;
        border-bottom: none;
    }
    .modal-buttons {
        margin-top: 20px;
        display: flex;
        justify-content: center;
        gap: 15px;
    }
    .modal-buttons button {
        padding: 10px 20px;
        font-weight: bold;
    }
    .modal-buttons button.confirm {
        background-color: #3498db;
    }
    .modal-buttons button.cancel {
        background-color: #e74c3c;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Smart Voting Machine</h1>
    <p>Admin: <a href="{{ url_for('admin_login') }}">/admin</a></p>
    <p>Admin should add voters first (with QR ID). You may also type a QR ID directly below for testing.</p>


    <div id="voting-area">
      <div id="step1" class="step-section">
        <h3>1) Scan QR ID or Enter Manually</h3>
        <div id="reader-container">
            <p>Scan your voter QR code with the camera:</p>
            <div id="reader"></div>
        </div>
        <br>
        <p>Alternatively, enter the ID manually:</p>
        <div class="flex-row">
            <input id="qr-input" placeholder="Type Voter QR ID here" />
            <button id="verify-qr-btn">Verify QR</button>
        </div>
        <p id="qr-status" class="status-message"></p>
      </div>


      <div id="details" class="step-section" style="display:none;">
        <h3>Voter Details</h3>
        <div id="voter-info"></div>
        <button id="start-fp-btn">Proceed to Fingerprint</button>
      </div>


      <div id="fp" class="step-section" style="display:none;">
        <h3>2) Fingerprint (Simulated)</h3>
        <p>Please place your finger on the scanner.</p>
        <div class="flex-row">
            <input id="fp-input" placeholder="Type fingerprint payload" />
            <button id="verify-fp-btn">Verify Fingerprint</button>
        </div>
        <p id="fp-status" class="status-message"></p>
      </div>


      <div id="voting" class="step-section" style="display:none;">
        <h3>3) Select Candidate</h3>
        <p>Please select your preferred candidate.</p>
        <button class="candidate" data-name="Candidate A">Candidate A</button>
        <button class="candidate" data-name="Candidate B">Candidate B</button>
        <button class="candidate" data-name="Candidate C">Candidate C</button>
        <p id="vote-status" class="status-message"></p>
      </div>
    </div>
  </div>


  <div id="custom-modal-overlay" class="modal-overlay">
    <div class="modal-content">
        <h3 id="modal-message"></h3>
        <div class="modal-buttons">
            <button id="modal-confirm-btn" class="confirm">Confirm</button>
            <button id="modal-cancel-btn" class="cancel">Cancel</button>
        </div>
    </div>
  </div>


<script src="https://unpkg.com/html5-qrcode"></script>
<script>
// Basic flow variables
let currentVoter = null;
let html5QrcodeScanner = null;


// Helper to set status message with style
function setStatus(elementId, message, type = 'info') {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.className = 'status-message ' + type;
    el.style.display = 'block';
}


// Custom modal functions
const modalOverlay = document.getElementById('custom-modal-overlay');
const modalMessageEl = document.getElementById('modal-message');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');


function showConfirmModal(message, onConfirmCallback) {
    modalMessageEl.textContent = message;
    modalOverlay.classList.add('visible');
    
    // Clear previous event listeners
    modalConfirmBtn.onclick = null;
    modalCancelBtn.onclick = null;


    modalConfirmBtn.onclick = () => {
        onConfirmCallback();
        modalOverlay.classList.remove('visible');
    };
    modalCancelBtn.onclick = () => {
        modalOverlay.classList.remove('visible');
    };
}




// Function to handle QR scan success
function onScanSuccess(decodedText, decodedResult) {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear();
    }
    document.getElementById('qr-input').value = decodedText;
    verifyQrCode(decodedText);
}


// Function to handle QR scan failure
function onScanFailure(error) {
    console.warn(`Code scan error = ${error}`);
}


// Initialize QR code scanner
function startQrScanner() {
    html5QrcodeScanner = new Html5QrcodeScanner("reader", {
        fps: 10,
        qrbox: { width: 250, height: 250 }
    }, false);
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}


window.addEventListener('load', startQrScanner);


async function verifyQrCode(qr) {
    if (!qr) { setStatus('qr-status', 'Error: Enter a QR ID.', 'error'); return; }
    const res = await fetch('/api/verify_qr', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({voter_id: qr})});
    const j = await res.json();
    if (j.ok) {
        currentVoter = j.voter;
        setStatus('qr-status', `QR OK. Welcome, ${currentVoter.name}.`, 'success');
        document.getElementById('voter-info').innerHTML = `<strong>Name:</strong> ${currentVoter.name}<br><strong>DOB:</strong> ${currentVoter.dob}<br><strong>Phone:</strong> ${currentVoter.phone}`;
        document.getElementById('details').style.display = 'block';
        document.getElementById('step1').style.display = 'none';
    } else {
        setStatus('qr-status', 'Error: ' + (j.detail || 'unknown error'), 'error');
        // Auto-refresh on error
        setTimeout(() => { window.location.reload(); }, 3000);
    }
}


// Verify QR ID by server for manual input
document.getElementById('verify-qr-btn').onclick = () => {
    const qr = document.getElementById('qr-input').value.trim();
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear();
    }
    verifyQrCode(qr);
}


// Fingerprint stage (simulated string match)
document.getElementById('start-fp-btn').onclick = () => {
    document.getElementById('fp').style.display = 'block';
    document.getElementById('details').style.display = 'none';
}


document.getElementById('verify-fp-btn').onclick = async () => {
    const payload = document.getElementById('fp-input').value.trim();
    if (!payload) { setStatus('fp-status', 'Error: Enter fingerprint payload.', 'error'); return; }
    const res = await fetch('/api/verify_fingerprint', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({voter_id: currentVoter.voter_id, fp_payload: payload})});
    const j = await res.json();
    if (j.ok) {
        setStatus('fp-status', 'Fingerprint OK!', 'success');
        document.getElementById('voting').style.display = 'block';
        document.getElementById('fp').style.display = 'none';
    } else {
        setStatus('fp-status', 'Fingerprint verification failed.', 'error');
        setTimeout(() => { window.location.reload(); }, 3000);
    }
}


// Voting
Array.from(document.getElementsByClassName('candidate')).forEach(btn => {
    btn.onclick = () => {
        showConfirmModal(`Confirm vote for ${btn.dataset.name}?`, async () => {
            const res = await fetch('/api/cast_vote', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({voter_id: currentVoter.voter_id, candidate: btn.dataset.name})});
            const j = await res.json();
            if (j.ok) {
                setStatus('vote-status', `Vote for ${btn.dataset.name} has been cast!`, 'success');
                setTimeout(() => { window.location.reload(); }, 3000); // Reload after 3s
            } else {
                setStatus('vote-status', 'Error: ' + (j.error || j.detail || 'unknown'), 'error');
                // Auto-refresh on error
                setTimeout(() => { window.location.reload(); }, 3000);
            }
        });
    }
});
</script>
</body>
</html>
"""


@APP.route("/")
def index():
    """Renders the main voting machine UI."""
    return render_template_string(INDEX_HTML)


# --- API endpoints used by frontend ---
@APP.route("/api/verify_qr", methods=["POST"])
def api_verify_qr():
    """API endpoint for QR code verification."""
    data = request.get_json(force=True)
    voter_id = data.get("voter_id", "").strip()
    if not voter_id:
        return jsonify(ok=False, error="missing_voter_id"), 400
    conn = get_conn()
    r = conn.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,)).fetchone()
    conn.close()
    if not r:
        return jsonify(ok=False, error="not_registered", detail="Contact Admin or NOT Registered"), 404
    age = calculate_age(r["dob"])
    if age < 18:
        return jsonify(ok=False, error="underage", age=age), 403
    voter = {"voter_id": r["voter_id"], "name": r["name"], "dob": r["dob"], "phone": r["phone"], "has_voted": bool(r["has_voted"])}
    return jsonify(ok=True, voter=voter)


@APP.route("/api/verify_fingerprint", methods=["POST"])
def api_verify_fingerprint():
    """API endpoint for fingerprint verification."""
    data = request.get_json(force=True)
    voter_id = data.get("voter_id", "").strip()
    fp_payload = data.get("fp_payload")
    if not voter_id or fp_payload is None:
        return jsonify(ok=False, error="missing_data"), 400
    conn = get_conn()
    r = conn.execute("SELECT fingerprint FROM voters WHERE voter_id=?", (voter_id,)).fetchone()
    conn.close()
    if not r:
        return jsonify(ok=False, error="voter_not_found"), 404
    stored = r["fingerprint"] or ""
    ok = (fp_payload == stored)
    return jsonify(ok=bool(ok))


@APP.route("/api/cast_vote", methods=["POST"])
def api_cast_vote():
    """API endpoint to cast and record a vote."""
    data = request.get_json(force=True)
    voter_id = data.get("voter_id", "").strip()
    candidate = data.get("candidate", "").strip()
    if not voter_id or not candidate:
        return jsonify(ok=False, error="missing_data"), 400
    conn = get_conn()
    r = conn.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,)).fetchone()
    if not r:
        conn.close()
        return jsonify(ok=False, error="voter_not_found"), 404
    if r["has_voted"]:
        conn.close()
        return jsonify(ok=False, error="already_voted"), 403


    # Check for phone number before committing the vote
    phone_number = r["phone"]
    if not phone_number:
        logging.warning(f"Voter {voter_id} does not have a registered phone number. SMS will not be sent.")


    ts = datetime.utcnow().isoformat()
    conn.execute("INSERT INTO votes (voter_id, candidate, timestamp) VALUES (?,?,?)", (voter_id, candidate, ts))
    conn.execute("UPDATE voters SET has_voted=1 WHERE voter_id=?", (voter_id,))
    conn.commit()
    conn.close()


    # Send SMS notification if a phone number exists
    if phone_number:
        message = f"Your vote has been successfully cast for {candidate}."
        send_sms(phone_number, message)


    return jsonify(ok=True, message="vote_recorded", timestamp=ts)


# --- Admin routes ---
@APP.route("/admin")
def admin_login():
    """Admin login page."""
    if session.get("admin"):
        return redirect(url_for("admin_list"))
    return render_template_string(ADMIN_LOGIN_HTML)


@APP.route("/admin", methods=["POST"])
def admin_login_post():
    """Handles admin login form submission."""
    username = request.form.get("username")
    password = request.form.get("password")
    if username == ADMIN_USER and password == ADMIN_PASS:
        session["admin"] = True
        flash("Logged in successfully!", "success")
        return redirect(url_for("admin_list"))
    flash("Invalid credentials.", "error")
    return redirect(url_for("admin_login"))


@APP.route("/admin/logout")
def admin_logout():
    """Logs the admin out."""
    session.pop("admin", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("admin_login"))


@APP.route("/admin/list")
def admin_list():
    """Lists all registered voters."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_conn()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    return render_template_string(ADMIN_LIST_HTML, voters=voters)


@APP.route("/admin/add", methods=["GET", "POST"])
def admin_add():
    """Adds a new voter to the database."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        voter_id = request.form.get("voter_id")
        name = request.form.get("name")
        dob = request.form.get("dob")
        phone = request.form.get("phone")
        fingerprint = request.form.get("fingerprint")
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO voters (voter_id, name, dob, phone, fingerprint, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (voter_id, name, dob, phone, fingerprint, datetime.utcnow().isoformat())
            )
            conn.commit()
            flash(f"Voter {name} added successfully!", "success")
        except sqlite3.IntegrityError:
            flash("Error: Voter ID already exists.", "error")
        finally:
            conn.close()
        return redirect(url_for("admin_add"))
    return render_template_string(ADMIN_ADD_HTML)


@APP.route("/admin/edit/<voter_id>", methods=["GET", "POST"])
def admin_edit(voter_id):
    """Edits an existing voter."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_conn()
    voter = conn.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,)).fetchone()
    if not voter:
        conn.close()
        flash("Voter not found.", "error")
        return redirect(url_for("admin_list"))
    if request.method == "POST":
        name = request.form.get("name")
        dob = request.form.get("dob")
        phone = request.form.get("phone")
        fingerprint = request.form.get("fingerprint")
        conn.execute(
            "UPDATE voters SET name=?, dob=?, phone=?, fingerprint=? WHERE voter_id=?",
            (name, dob, phone, fingerprint, voter_id)
        )
        conn.commit()
        flash(f"Voter {voter_id} updated successfully!", "success")
        conn.close()
        return redirect(url_for("admin_list"))
    conn.close()
    return render_template_string(ADMIN_EDIT_HTML, voter=voter)


@APP.route("/admin/delete/<voter_id>", methods=["POST"])
def admin_delete(voter_id):
    """Deletes a voter from the database."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_conn()
    conn.execute("DELETE FROM voters WHERE voter_id=?", (voter_id,))
    conn.commit()
    conn.close()
    flash(f"Voter {voter_id} deleted.", "success")
    return redirect(url_for("admin_list"))


@APP.route("/admin/update_voted_status/<voter_id>", methods=["POST"])
def admin_update_voted_status(voter_id):
    """Toggles the has_voted status of a voter."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    password = request.form.get("password")
    if password != VOTED_STATUS_PASSWORD:
        flash("Incorrect password for status change.", "error")
        return redirect(url_for("admin_list"))
    conn = get_conn()
    r = conn.execute("SELECT has_voted FROM voters WHERE voter_id=?", (voter_id,)).fetchone()
    if r:
        current_status = r["has_voted"]
        new_status = 1 - current_status
        conn.execute("UPDATE voters SET has_voted=? WHERE voter_id=?", (new_status, voter_id))
        conn.commit()
        flash(f"Voted status for {voter_id} updated to {'Yes' if new_status else 'No'}.", "success")
    else:
        flash("Voter not found.", "error")
    conn.close()
    return redirect(url_for("admin_list"))


# Start
if __name__ == "__main__":
    print("Starting Smart Voting single-file (with admin).")
    print("DB path:", DB_PATH)
    APP.run(host="0.0.0.0", port=5000, debug=True)
