from flask import Flask, render_template, request, jsonify
import datetime as dt
import os

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

app = Flask(__name__, template_folder="template")  # name template folder "template"

TIME_FORMAT = "%m/%d/%Y %H:%M"

load_dotenv()

DB_HOST = os.environ.get("MYSQL_HOST", "localhost")
DB_PORT = int(os.environ.get("MYSQL_PORT", 3306))
DB_USER = os.environ.get("MYSQL_USER", "env_user")
DB_PASS = os.environ.get("MYSQL_PASS", "env_pass")
DB_NAME = os.environ.get("MYSQL_DB", "envmon")
DEVICE_ID = os.environ.get("DEVICE_ID")  # optional filter by device/sensor

def get_conn():
    """Create and return a new MySQL connection."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
    )

def load_data_from_db(start_dt=None, end_dt=None):
    """
    Query readings from the database between start_dt and end_dt.

    Returns a list of dicts with keys: Time (datetime), Temperature, Humidity.
    """
    rows = []
    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        # Base query
        query = """
            SELECT ts, temperature_c, humidity_pct
            FROM readings
            WHERE 1=1
        """
        params = []

        # Optional filter by device/sensor
        if DEVICE_ID:
            query += " AND device_id = %s"
            params.append(DEVICE_ID)

        # Optional time filters
        if start_dt is not None:
            query += " AND ts >= %s"
            params.append(start_dt)

        if end_dt is not None:
            query += " AND ts <= %s"
            params.append(end_dt)

        query += " ORDER BY ts"

        cur.execute(query, params)

        for row in cur:
            # row['ts'] is a datetime object from MySQL
            rows.append({
                "Time": row["ts"],
                "Temperature": float(row["temperature_c"]),
                "Humidity": float(row["humidity_pct"]),
            })

        cur.close()
        conn.close()
    except Error as e:
        print("DB error while loading data:", e)

    return rows


@app.route("/")
def index():
    return render_template("index.html")   # name the file within template folder "index.html"


@app.route("/data")
def get_data():
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    start_dt = None
    end_dt = None
    try:
        if start_str:
            start_dt = dt.datetime.strptime(start_str, TIME_FORMAT)
        if end_str:
            end_dt = dt.datetime.strptime(end_str, TIME_FORMAT)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    #load data from database
    all_rows = load_data_from_db(start_dt=start_dt, end_dt=end_dt)
    if not all_rows:
        return jsonify([])

    output = []
    for r in all_rows:
        output.append({
            "Time": r["Time"].strftime(TIME_FORMAT),
            "Temperature": r["Temperature"],
            "Humidity": r["Humidity"]
        })

    return jsonify(output)


if __name__ == "__main__":
    app.run(debug=True)