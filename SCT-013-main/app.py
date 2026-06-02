from flask import Flask, render_template, jsonify, request
import os
import db

app = Flask(__name__, template_folder="templates")

# Make sure db is initialized when server starts
db.init_db()

@app.route("/")
def index():
    """Serves the dashboard home page."""
    return render_template("index.html")

@app.route("/api/readings", methods=["GET"])
def get_readings_api():
    """API endpoint to get parsed readings."""
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    start_date = request.args.get("start", default=None, type=str)
    end_date = request.args.get("end", default=None, type=str)
    
    # Restrict limit to avoid memory issues
    limit = min(limit, 5000)
    
    try:
        readings = db.get_readings(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date
        )
        return jsonify({
            "status": "success",
            "count": len(readings),
            "data": readings
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/stats", methods=["GET"])
def get_stats_api():
    """API endpoint to retrieve aggregate statistical metrics."""
    try:
        stats = db.get_stats()
        return jsonify({
            "status": "success",
            "data": stats
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/reading", methods=["POST"])
def add_reading_api():
    """API endpoint to manually post a reading (alternative ingestion)."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
        
    timestamp = data.get("timestamp")
    current_rms = data.get("current_rms")
    apparent_power = data.get("apparent_power")
    
    if not all([timestamp, current_rms is not None, apparent_power is not None]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
    try:
        db.insert_reading(timestamp, float(current_rms), float(apparent_power))
        return jsonify({"status": "success", "message": "Reading added successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Run server locally on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
