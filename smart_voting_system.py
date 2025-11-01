#!/usr/bin/env python3
"""
smart_voting_system.py
Single-file prototype: Smart Voting Machine + Admin UI to add and manage voters.

This version includes QR, Fingerprint, and Face Recognition verification.
NEW FEATURE: Image Upload option added to Admin Add/Edit Voter pages for Face Data.

Run:
  1) python3 -m venv venv
  2) source venv/bin/activate  (Unix)  or  venv\Scripts\activate (Windows)
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

# --- NOTE: The original HTML/CSS/JS strings are defined right here in the actual file.
# --- For clarity in this response, they are shown in separate blocks below.

# App and DB config
APP = Flask(__name__)
# The HTML templates (e.g., ADMIN_LOGIN_HTML) would normally be imported or read here.
# Since it's a single file, they are defined as constants above the Flask logic.

APP.secret_key = os.environ.get("SVM_SECRET_KEY", "svm_demo_secret_key_change_me")
BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "svm_admin.db"


# Admin credentials
ADMIN_USER = "poomalai005"
ADMIN_PASS = "Poomalai2005@"
VOTED_STATUS_PASSWORD = "989464"
# ***Reset Votes Password***
RESET_VOTES_PASSWORD = "Poomalai@989464"


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
    # MODIFICATION: Added 'face_data' column to voters table
    c.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT UNIQUE,
            name TEXT,
            dob TEXT,
            phone TEXT,
            fingerprint TEXT,
            face_data TEXT,  
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

def get_vote_counts():
    """Calculates and returns the total votes for each candidate."""
    conn = get_conn()
    # Use GROUP BY and COUNT() to get the totals for each candidate
    votes = conn.execute("""
        SELECT candidate, COUNT(id) as total_votes  
        FROM votes  
        GROUP BY candidate  
        ORDER BY total_votes DESC
    """).fetchall()
    total_votes_cast = conn.execute("SELECT COUNT(id) FROM votes").fetchone()[0]
    conn.close()
    
    # Convert results to a list of dictionaries for easier use
    results = [{'candidate': row['candidate'], 'count': row['total_votes']} for row in votes]
    
    return results, total_votes_cast


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


# --- Flask Routes (The Python logic continues with the routes) ---

@APP.route("/")
def index():
    """Renders the main voting machine UI."""
    # This would use the INDEX_HTML string defined in the full file
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
        return jsonify(ok=False, error="underage", age=age, detail="You are Not eligible for voting (Under 18)."), 403
    
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
    # Simulation: payload must match the stored fingerprint (which is voter_id in this demo)
    ok = (fp_payload == stored) 
    return jsonify(ok=bool(ok))


@APP.route("/api/verify_face", methods=["POST"])
def api_verify_face():
    """
    API endpoint for face recognition verification.
    """
    data = request.get_json(force=True)
    voter_id = data.get("voter_id", "").strip()
    face_payload = data.get("face_payload")
    if not voter_id or face_payload is None:
        return jsonify(ok=False, error="missing_data"), 400
    conn = get_conn()
    r = conn.execute("SELECT face_data FROM voters WHERE voter_id=?", (voter_id,)).fetchone()
    conn.close()
    if not r:
        return jsonify(ok=False, error="voter_not_found"), 404
    
    stored = r["face_data"] or ""
    # Simulation: payload must match the stored face_data (which is voter_id in this demo)
    ok = (face_payload == stored) 
    
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
        return jsonify(ok=False, error="already_voted", detail="This voter has already cast a vote and cannot vote again."), 403


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
    # This would use the ADMIN_LOGIN_HTML string
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
    # This would use the ADMIN_LIST_HTML string
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
        # Get face_data from hidden input (captured by JS)
        face_data = request.form.get("face_data")  
        conn = get_conn()
        try:
            # MODIFIED: Insert face_data into the database
            conn.execute(
                "INSERT INTO voters (voter_id, name, dob, phone, fingerprint, face_data, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (voter_id, name, dob, phone, fingerprint, face_data, datetime.utcnow().isoformat())
            )
            conn.commit()
            flash(f"Voter {name} added successfully!", "success")
        except sqlite3.IntegrityError:
            flash("Error: Voter ID already exists.", "error")
        finally:
            conn.close()
        return redirect(url_for("admin_add"))
    # This would use the ADMIN_ADD_HTML string
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
        # Get face_data from hidden input (captured by JS)
        face_data = request.form.get("face_data")
        # MODIFIED: Update face_data in the database
        conn.execute(
            "UPDATE voters SET name=?, dob=?, phone=?, fingerprint=?, face_data=? WHERE voter_id=?",
            (name, dob, phone, fingerprint, face_data, voter_id)
        )
        conn.commit()
        flash(f"Voter {voter_id} updated successfully!", "success")
        conn.close()
        return redirect(url_for("admin_list"))
    conn.close()
    # This would use the ADMIN_EDIT_HTML string
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


@APP.route("/admin/analytics")
def admin_analytics():
    """Displays vote analytics and counts per candidate."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
        
    results, total_votes = get_vote_counts()
    
    # This would use the ADMIN_ANALYTICS_HTML string
    return render_template_string(ADMIN_ANALYTICS_HTML, 
                                  vote_results=results, 
                                  total_votes=total_votes)

# ***ROUTE: Handle Resetting Votes***
@APP.route("/admin/analytics/reset", methods=["POST"])
def admin_reset_votes():
    """Resets all votes and voter statuses based on password verification."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
        
    password = request.form.get("password")
    
    if password != RESET_VOTES_PASSWORD:
        flash("Incorrect password. Votes and voter statuses were NOT reset.", "error")
        return redirect(url_for("admin_analytics"))
        
    conn = get_conn()
    try:
        # 1. Delete all records from the 'votes' table
        conn.execute("DELETE FROM votes")
        
        # 2. Reset the 'has_voted' status for all voters
        conn.execute("UPDATE voters SET has_voted=0")
        
        conn.commit()
        
        logging.info("ALL VOTES AND VOTER STATUSES HAVE BEEN RESET.")
        flash("SUCCESS: All votes have been reset, and all voters can vote again.", "success")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error during vote reset: {e}")
        flash(f"Error resetting votes: {e}", "error")
    finally:
        conn.close()
        
    return redirect(url_for("admin_analytics"))


# Start
if __name__ == "__main__":
    print("Starting Smart Voting single-file (with admin).")
    print("DB path:", DB_PATH)
    APP.run(host="0.0.0.0", port=5000, debug=True)
