import os
import random
import smtplib
import json
from urllib.parse import urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib

app = Flask(__name__)
CORS(app)

# =========================
# LOAD MODEL
# =========================
model = joblib.load("models/model.pkl")
vectorizer = joblib.load("models/vectorizer.pkl")

# =========================
# EMAIL CONFIG  (single definition)
# =========================
EMAIL_ADDRESS = "EMAIL_ADDRESS"
EMAIL_PASSWORD = "APP_PASSWORD"   # App Password

# =========================
# OTP STORES
# =========================
otp_store = {}          # user OTPs  keyed by email
admin_otp_store = {}    # admin OTPs keyed by admin_id

# =========================
# STORE REPORTS
# =========================
REPORTS_FILE = 'reports.json'

if os.path.exists(REPORTS_FILE):
    try:
        with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
            reports = json.load(f)
    except Exception:
        reports = []
else:
    reports = []


def save_reports():
    try:
        with open(REPORTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(reports, f, indent=2)
    except Exception as e:
        print('Failed to persist reports:', e)

# =========================
# HOME
# =========================
@app.route('/')
def home():
    return "Backend is running"

# =========================
# SHARED EMAIL HELPER  (single definition)
# =========================
def send_otp_email(to_email, otp, subject="OTP Verification"):
    print(f"\n==== SENDING OTP ====  TO: {to_email}  OTP: {otp}")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        msg = MIMEMultipart()
        msg['From'] = "Army Welfare Security (Demo) <" + EMAIL_ADDRESS + ">"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(f"Your OTP is: {otp}\n\nValid for 4 minutes. Do not share with anyone.", 'plain'))

        server.send_message(msg)
        server.quit()
        print("==== OTP EMAIL SENT SUCCESSFULLY ====\n")
        return True
    except Exception as e:
        print(f"==== EMAIL ERROR: {e} ====\n")
        return False

# =========================
# ADMIN UTILS
# =========================
def get_admin_data(admin_id):
    """Load admin from admin_config.json. Falls back to hardcoded if file missing."""
    admin_id = str(admin_id or '').strip().upper()
    try:
        with open('admin_config.json', 'r') as f:
            data = json.load(f)
            for admin in data.get('administrators', []):
                if str(admin.get('admin_id', '')).strip().upper() == admin_id:
                    return admin
    except FileNotFoundError:
        # Fallback hardcoded admin if no config file exists
        HARDCODED = {
            "admin_id": "DCERT-ADMIN-001",
            "password": "ADMIN@1234",
            "email": "varshiniash29@gmail.com"   # Change to real admin email
        }
        if admin_id == HARDCODED["admin_id"]:
            return HARDCODED
    except Exception as e:
        print("admin_config.json error:", e)
    return None

# =========================
# SEND OTP — User
# =========================
@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    defence_id = data.get("defence_id", "").strip()

    if not email or not defence_id:
        return jsonify({"success": False, "message": "Defence ID and Email are both required"}), 400

    # Validate defence_id + email match in defence_dataset.json
    try:
        with open('defence_dataset.json', 'r') as f:
            defence_data = json.load(f)

        matched = any(
            person["service_id"] == defence_id and
            person["email"].strip().lower() == email
            for person in defence_data
        )

        if not matched:
            return jsonify({"success": False, "message": "Defence ID and Email do not match our records"}), 403

    except Exception as e:
        print("Failed to load defence_dataset.json:", repr(e))
        return jsonify({"success": False, "message": "Server error validating credentials"}), 500

    otp = str(random.randint(100000, 999999))
    otp_store[email] = otp

    if send_otp_email(email, otp, subject="NCDP — OTP Verification"):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Failed to send OTP email. Check server logs."}), 500

# =========================
# VERIFY OTP — User
# =========================
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    otp = str(data.get("otp", "")).strip()

    if not email or not otp:
        return jsonify({"success": False}), 400

    if otp_store.get(email) == otp:
        del otp_store[email]   # consume OTP — one-time use
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid or expired OTP"})

# =========================
# ADMIN LOGIN — sends OTP to admin email  (SINGLE definition)
# =========================
@app.route('/admin-login', methods=['POST'])
def admin_login():
    print("ADMIN LOGIN API HIT")
    data = request.get_json() or {}
    admin_id = str(data.get("admin_id") or '').strip().upper()
    password = str(data.get("password") or '').strip()

    admin = get_admin_data(admin_id)

    if not admin or admin.get('password') != password:
        print("Admin login FAILED for:", admin_id)
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    otp = str(random.randint(100000, 999999))
    admin_otp_store[admin_id] = otp

    sent = send_otp_email(admin['email'], otp, subject="NCDP Admin — OTP Verification")
    if not sent:
        return jsonify({"success": False, "message": "Failed to send OTP to admin email"}), 500

    print(f"Admin OTP sent for {admin_id} → {admin['email']}")
    return jsonify({"success": True, "message": "OTP sent to registered admin email."})

# =========================
# VERIFY ADMIN OTP  (SINGLE definition — both old names handled)
# =========================
@app.route('/admin-verify', methods=['POST'])
@app.route('/verify-admin-otp', methods=['POST'])
def admin_verify():
    data = request.get_json() or {}
    admin_id = str(data.get("admin_id") or '').strip().upper()
    otp = str(data.get("otp") or '').strip()

    if admin_otp_store.get(admin_id) == otp:
        del admin_otp_store[admin_id]   # consume OTP
        return jsonify({"success": True, "message": "Authentication successful"})
    return jsonify({"success": False, "message": "Invalid OTP"}), 401

# =========================
# PREDICT
# =========================
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    text = data.get("text")
    incident_type = data.get("type")
    platform = data.get("platform")
    impact = data.get("impact")
    description = data.get("description")
    incident_date = data.get("incidentDate")
    evidence_file = data.get("evidenceFile")

    if not text:
        return jsonify({"error": "Text required"}), 400

    vect = vectorizer.transform([text])
    prediction = model.predict(vect)[0]
    confidence = max(model.predict_proba(vect)[0])

    if prediction == "fraud":
        risk = "HIGH" if confidence >= 0.70 else "MEDIUM"
    elif prediction == "social_engineering":
        risk = "HIGH" if confidence >= 0.65 else "MEDIUM"
    elif prediction == "phishing":
        if confidence >= 0.70:
            risk = "HIGH"
        elif confidence >= 0.40:
            risk = "MEDIUM"
        else:
            risk = "LOW"
    else:
        risk = "LOW"

    high_impact_types = {"data", "financial", "access", "device", "official"}
    if incident_type in {"image", "document", "audio", "video"} and impact in high_impact_types and evidence_file:
        if confidence >= 0.65:
            risk = "HIGH"
        elif risk == "LOW":
            risk = "MEDIUM"

    ref_date = incident_date.replace('-', '').replace(':', '').replace('T', '') if incident_date else str(random.randint(10000000, 99999999))
    ref = f"NCDP-{ref_date}-{random.randint(100, 999)}"

    reporter_name = data.get('reporterName') or 'Authenticated Reporter'
    personnel_id = data.get('personnelId') or 'NCDP-USER'
    evidence_image = data.get('evidenceImage', '')

    reports.append({
        "ref": ref,
        "name": reporter_name,
        "pid": personnel_id,
        "type": incident_type or "Unknown",
        "risk": risk,
        "status": "Open",
        "date": incident_date.split('T')[0] if incident_date else "Unknown",
        "platform": platform or "Unknown",
        "fraudScore": f"{round(confidence * 100)}%",
        "reportedText": text,
        "evidence": evidence_file or "Evidence uploaded.",
        "evidenceImage": evidence_image,
        "note": description or "No additional description provided.",
        "aiPercentage": f"{round(confidence * 100)}%"
    })
    save_reports()

    return jsonify({
        "prediction": prediction,
        "confidence": round(confidence, 2),
        "risk": risk,
        "ref": ref,
        "name": reporter_name,
        "pid": personnel_id,
        "type": incident_type,
        "platform": platform,
        "date": incident_date,
        "description": description,
        "reportedText": text,
        "evidence": evidence_file
    })

# =========================
# ANALYZE URL
# =========================
@app.route('/analyze-url', methods=['POST'])
def analyze_url():
    data = request.get_json(silent=True) or {}
    url = data.get('url')
    print('Analyze URL request:', url)

    if not url or not isinstance(url, str):
        return jsonify({"error": "URL required"}), 400

    try:
        vect = vectorizer.transform([url])
        probs = model.predict_proba(vect)[0]
        ml_score = round(max(probs) * 100)
    except Exception as error:
        print('Analyze URL failed:', error)
        return jsonify({"risk_score": 0, "risk_level": "LOW"})

    lower_url = url.lower()
    trusted_domains = {"google.com", "github.com", "microsoft.com", "amazon.com", "apple.com", "cloudflare.com"}

    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ''
    except Exception:
        domain = ''

    rule_score = 0
    if domain not in trusted_domains:
        suspicious_keywords = ["login", "verify", "bank", "secure", "update", "otp"]
        rule_score = sum(15 for kw in suspicious_keywords if kw in lower_url)
        if len(domain) > 25:
            rule_score += 10
        if domain.count('-') > 2:
            rule_score += 15
        if domain.endswith(('.xyz', '.top', '.tk')):
            rule_score += 20

    rule_score = min(rule_score, 100)
    final_score = round((0.6 * ml_score) + (0.4 * rule_score))

    if domain in trusted_domains and rule_score == 0:
        final_score = min(final_score, 35)

    if final_score > 70:
        risk = 'HIGH'
    elif final_score >= 40:
        risk = 'MEDIUM'
    else:
        risk = 'LOW'

    return jsonify({"risk_score": final_score, "risk_level": risk})

# =========================
# GET REPORTS
# =========================
@app.route('/reports', methods=['GET'])
def get_reports():
    return jsonify(reports)

# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)
