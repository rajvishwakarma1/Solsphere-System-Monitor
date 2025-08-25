from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import ast
import os

API_KEY = "StrongInterviewKey"  # Shared secret used for API authentication

app = Flask(__name__)
CORS(app)


# SQLite path in local folder
DB_PATH = os.path.join(os.path.dirname(__file__), 'systems.db')

# Initialize the SQLite database and create the systems table if it doesn't exist
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS systems (
            machine_id TEXT PRIMARY KEY,
            os TEXT,
            disk_encryption INTEGER,
            os_update TEXT,
            antivirus TEXT,
            sleep_settings TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

# Execute a query and return results (for both read/write operations)
def query_db(sql, args=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(sql, args)
    rows = c.fetchall()
    conn.commit()
    conn.close()
    return rows

# Verify that the incoming request contains the correct API key
def check_api_key(req):
    return req.headers.get("X-API-Key") == API_KEY

# Endpoint to receive machine status reports (creates or updates records)
@app.route("/report", methods=["POST"])
def report():
    if not check_api_key(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    query_db("""
        INSERT OR REPLACE INTO systems 
        (machine_id, os, disk_encryption, os_update, antivirus, sleep_settings, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["machine_id"],
        data["os"],
        int(data["disk_encryption"]),
        str(data["os_update"]),
        str(data["antivirus"]),
        str(data["sleep_settings"]),
        data["timestamp"]
    ))

    return jsonify({"status": "ok"})

# Endpoint to retrieve machine records with optional filtering by OS and issue type
@app.route("/machines", methods=["GET"])
def machines():
    os_filter = request.args.get("os")
    issue_filter = request.args.get("issue")
    sql = "SELECT * FROM systems"
    args = []

    # Build dynamic WHERE clause based on query parameters
    if os_filter or issue_filter:
        clauses = []

        if os_filter:
            clauses.append("os = ?")
            args.append(os_filter)

        if issue_filter == "disk":
            clauses.append("disk_encryption = 0")
        elif issue_filter == "update":
            clauses.append("os_update LIKE '%Update Available%'")
        elif issue_filter == "antivirus":
            clauses.append("antivirus LIKE '%False%'")
        elif issue_filter == "sleep":
            clauses.append("sleep_settings NOT LIKE '%10%' AND sleep_settings NOT LIKE '%less%'")

        sql += " WHERE " + " AND ".join(clauses)

    rows = query_db(sql, args)
    results = []

    # Convert stringified dict fields back to Python dicts
    def parse_literal(s):
        try:
            return ast.literal_eval(s) if isinstance(s, str) else s
        except Exception:
            return {}

    # Structure and parse each row into a well-defined JSON object
    for row in rows:
        machine_id, os_name, disk_enc_int, os_update_str, av_str, sleep_str, ts = row

        os_update = parse_literal(os_update_str) or {}
        antivirus = parse_literal(av_str) or {}
        sleep_settings = parse_literal(sleep_str) or {}

        results.append({
            "machine_id": machine_id,
            "os": os_name,
            "disk_encryption": bool(disk_enc_int),
            "os_update": {
                "current": os_update.get("current"),
                "latest": os_update.get("latest"),
            },
            "antivirus": {
                "installed": bool(antivirus.get("installed")) if isinstance(antivirus.get("installed"), (bool, int)) else antivirus.get("installed"),
                "active": bool(antivirus.get("active")) if isinstance(antivirus.get("active"), (bool, int)) else antivirus.get("active"),
            },
            "sleep_settings": {
                "timeout_minutes": sleep_settings.get("timeout_minutes"),
            },
            "timestamp": ts,
        })

    return jsonify(results)

# Entry point of the application
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
