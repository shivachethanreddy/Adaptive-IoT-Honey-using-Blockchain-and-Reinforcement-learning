from flask import Flask, request, jsonify
import datetime

app = Flask(__name__)
logs      = []
blocked_ips = set()
ip_times  = {}
ip_vals   = {}
KNOWN_IPS = {"esp32": "172.20.10.3"}  # real ESP32 IP

@app.route('/data', methods=['POST'])
def receive():
    ip  = request.remote_addr
    if ip in blocked_ips:
        return jsonify({"status": "blocked"}), 403

    data = request.get_json(force=True)
    dist = data.get("distance", 0)
    dev  = data.get("device", "unknown")
    now  = datetime.datetime.now()

    # Attack 1 — flood
    t = ip_times.get(ip, [])
    t = [x for x in t if now.timestamp() - x < 10]
    t.append(now.timestamp())
    ip_times[ip] = t
    is_flood = len(t) > 10

    # Attack 2 — false data
    is_false = dist < 2 or dist > 400

    # Attack 3 — replay
    v = ip_vals.get(ip, [])
    v.append(round(dist, 1))
    ip_vals[ip] = v[-10:]
    is_replay = v.count(round(dist, 1)) >= 5

    # Attack 4 — spoofing
    expected = KNOWN_IPS.get(dev)
    is_spoof = expected is not None and expected != ip

    atk = ("FLOOD"      if is_flood  else
           "FALSE_DATA"  if is_false  else
           "REPLAY"      if is_replay else
           "SPOOFING"    if is_spoof  else None)

    entry = {
        "ip": ip, "device": dev,
        "distance": dist, "time": str(now),
        "attack": atk
    }
    logs.append(entry)

    if atk:
        print(f"[ATTACK DETECTED] {atk} from {ip} | distance={dist}")

    return jsonify({"status": "ok", "attack": atk})

@app.route('/block/<ip>', methods=['POST'])
def block(ip):
    blocked_ips.add(ip)
    print(f"[MANUAL BLOCK] {ip} is now blocked")
    return jsonify({"blocked": ip})

@app.route('/logs')
def show_logs():
    return jsonify(logs[-50:])

@app.route('/dashboard')
def dashboard():
    html = """
    <html><head>
    <title>ESP32 Monitor</title>
    <meta http-equiv="refresh" content="3">
    <style>
      body{font-family:monospace;padding:20px;background:#0d1117;color:#c9d1d9}
      h2{color:#58a6ff}
      table{width:100%;border-collapse:collapse;margin-top:10px}
      th{background:#161b22;color:#8b949e;padding:8px;text-align:left;border:1px solid #30363d}
      td{padding:8px;border:1px solid #30363d}
      .attack{color:#f85149;font-weight:bold}
      .ok{color:#56d364}
    </style></head><body>
    <h2>ESP32 IoT Security Monitor — Month 1</h2>
    <p>Auto-refreshes every 3 seconds</p>
    <table>
      <tr><th>Time</th><th>IP</th><th>Device</th><th>Distance</th><th>Attack</th></tr>
    """
    for log in reversed(logs[-30:]):
        atk   = log.get("attack")
        color = "attack" if atk else "ok"
        html += f"""<tr>
          <td>{log['time'][:19]}</td>
          <td>{log['ip']}</td>
          <td>{log['device']}</td>
          <td>{log['distance']} cm</td>
          <td class="{color}">{atk if atk else "normal"}</td>
        </tr>"""
    html += "</table></body></html>"
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)