from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Store latest ultrasonic sensor value
latest_data = {
    "distance": None,
    "time": None
}

@app.route("/", methods=["GET"])
def home():
    return "Week-2 IoT Server Running (Ultrasonic Sensor)", 200


@app.route("/data", methods=["GET", "POST"])
def data():
    global latest_data

    # ESP32 sends ultrasonic data
    if request.method == "POST":
        data = request.get_json(force=True)

        latest_data["distance"] = data.get("distance")
        latest_data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[ESP32] Distance = {latest_data['distance']} cm")
        return jsonify({"status": "stored"}), 200

    # Client (browser) reads ultrasonic data
    return jsonify({
        "sensor": "HC-SR04 Ultrasonic",
        "distance_cm": latest_data["distance"],
        "last_updated": latest_data["time"]
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
