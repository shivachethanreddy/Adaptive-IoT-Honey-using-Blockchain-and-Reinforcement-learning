import hashlib, json, datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

logs        = []
blocked_ips = set()
ip_times    = {}
ip_vals     = {}
KNOWN_IPS   = {"esp32": "172.20.10.3"}   # real ESP32 IP

# ══════════════════════════════════════
#  BLOCKCHAIN
# ══════════════════════════════════════
CHAIN_FILE = "blockchain.json"
chain = []

def save_chain():
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain, f, indent=2)

def compute_hash(block):
    # Hash everything EXCEPT the hash field itself
    record = {k: v for k, v in block.items() if k != "hash"}
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()

def add_block(event_type, data):
    prev_hash = chain[-1]["hash"] if chain else "0" * 64
    block = {
        "index"    : len(chain),
        "timestamp": str(datetime.datetime.now()),
        "event"    : event_type,
        "data"     : data,
        "prev_hash": prev_hash,
        "hash"     : ""          # filled below
    }
    block["hash"] = compute_hash(block)
    chain.append(block)
    save_chain()
    print(f"[BLOCKCHAIN] Block {block['index']} | {event_type} | {block['hash'][:16]}...")
    return block

def verify_chain():
    for i, block in enumerate(chain):
        # Check own hash
        if block["hash"] != compute_hash(block):
            return False, f"Block {i} hash is invalid — data was tampered"
        # Check link to previous block
        if i > 0 and block["prev_hash"] != chain[i-1]["hash"]:
            return False, f"Block {i} prev_hash does not match Block {i-1}"
    return True, "Chain is valid"

# Genesis block — always first
add_block("GENESIS", {"message": "Blockchain started — Month 2"})

# ══════════════════════════════════════
#  ATTACK DETECTION (same 4 as Month 1)
# ══════════════════════════════════════
def detect_attack(ip, dist, dev):
    now = datetime.datetime.now()

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
    expected  = KNOWN_IPS.get(dev)
    is_spoof  = expected is not None and expected != ip

    return ("FLOOD"      if is_flood  else
            "FALSE_DATA"  if is_false  else
            "REPLAY"      if is_replay else
            "SPOOFING"    if is_spoof  else None)

# ══════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════

# ESP32 real data
@app.route('/data', methods=['POST'])
def real_data():
    ip   = request.remote_addr
    data = request.get_json(force=True)
    dist = data.get("distance", 0)
    dev  = data.get("device", "unknown")
    now  = str(datetime.datetime.now())

    entry = {"ip": ip, "device": dev, "distance": dist,
             "time": now, "source": "ESP32", "attack": None}
    logs.append(entry)

    # Write real sensor data to blockchain
    add_block("SENSOR_DATA", {"ip": ip, "distance": dist, "device": dev})
    return jsonify({"status": "ok"})

# ESP8266 honeypot data
@app.route('/honeypot', methods=['POST'])
def honeypot_data():
    attacker_ip = request.args.get("attacker_ip", request.remote_addr)
    if attacker_ip in blocked_ips:
        return jsonify({"status": "blocked"}), 403

    data = request.get_json(force=True)
    dist = data.get("distance", 0)
    dev  = data.get("device", "unknown")
    now  = str(datetime.datetime.now())

    atk = detect_attack(attacker_ip, dist, dev)

    entry = {"ip": attacker_ip, "device": dev, "distance": dist,
             "time": now, "source": "HONEYPOT", "attack": atk}
    logs.append(entry)

    if atk:
        print(f"[ATTACK] {atk} from {attacker_ip} | dist={dist}")
        add_block("ATTACK_DETECTED", {
            "attacker_ip": attacker_ip,
            "attack_type": atk,
            "distance"   : dist,
            "device"     : dev
        })

    return jsonify({"status": "ok", "attack": atk})

# Manual IP block
@app.route('/block/<ip>', methods=['POST'])
def block_ip(ip):
    blocked_ips.add(ip)
    add_block("IP_BLOCKED", {
        "ip"    : ip,
        "reason": "manual_block",
        "time"  : str(datetime.datetime.now())
    })
    print(f"[BLOCKED] {ip} added to deny list")
    return jsonify({"blocked": ip})

# View blockchain
@app.route('/chain')
def show_chain():
    return jsonify(chain)

# Verify blockchain integrity
@app.route('/verify')
def verify():
    valid, message = verify_chain()
    return jsonify({
        "valid"  : valid,
        "message": message,
        "blocks" : len(chain)
    })

# Raw logs
@app.route('/logs')
def show_logs():
    return jsonify(logs[-50:])

# Dashboard
@app.route('/dashboard')
def dashboard():
    valid, vmsg = verify_chain()
    chain_status = "VALID" if valid else "TAMPERED"
    chain_color  = "#56d364" if valid else "#f85149"

    html = f"""<html><head>
    <title>IoT Security Monitor — Month 2</title>
    <meta http-equiv="refresh" content="3">
    <style>
      body{{font-family:monospace;padding:20px;background:#0d1117;color:#c9d1d9;margin:0}}
      h2{{color:#58a6ff;margin-bottom:4px}}
      .sub{{color:#8b949e;font-size:13px;margin-bottom:20px}}
      .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
      .stat{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;text-align:center}}
      .stat-num{{font-size:24px;font-weight:bold;color:#58a6ff}}
      .stat-label{{font-size:11px;color:#8b949e;margin-top:4px}}
      .chain-status{{background:#161b22;border:1px solid #30363d;border-radius:8px;
                    padding:10px 16px;margin-bottom:16px;font-size:13px}}
      table{{width:100%;border-collapse:collapse}}
      th{{background:#161b22;color:#8b949e;padding:8px;text-align:left;
          border:1px solid #30363d;font-size:12px}}
      td{{padding:8px;border:1px solid #30363d;font-size:12px}}
      .attack{{color:#f85149;font-weight:bold}}
      .ok{{color:#56d364}}
      .honeypot{{color:#e3b341}}
      .esp32{{color:#58a6ff}}
      .section{{color:#8b949e;font-size:12px;margin:16px 0 8px}}
      .block-row{{font-size:11px;padding:6px 8px;border-bottom:1px solid #21262d;
                 font-family:monospace}}
      .block-row:last-child{{border-bottom:none}}
    </style></head><body>
    <h2>IoT Security Monitor — Month 2</h2>
    <div class="sub">Auto-refresh every 3s | Honeypot + Blockchain active</div>

    <div class="stats">
      <div class="stat">
        <div class="stat-num">{len([l for l in logs if l['source']=='ESP32'])}</div>
        <div class="stat-label">Real readings</div>
      </div>
      <div class="stat">
        <div class="stat-num">{len([l for l in logs if l['source']=='HONEYPOT'])}</div>
        <div class="stat-label">Honeypot hits</div>
      </div>
      <div class="stat">
        <div class="stat-num">{len([l for l in logs if l.get('attack')])}</div>
        <div class="stat-label">Attacks detected</div>
      </div>
      <div class="stat">
        <div class="stat-num">{len(blocked_ips)}</div>
        <div class="stat-label">IPs blocked</div>
      </div>
    </div>

    <div class="chain-status">
      Blockchain: <span style="color:{chain_color};font-weight:bold">{chain_status}</span>
      &nbsp;|&nbsp; {len(chain)} blocks
      &nbsp;|&nbsp; {vmsg}
      &nbsp;&nbsp;<a href="/verify" style="color:#58a6ff">verify</a>
      &nbsp;|&nbsp;<a href="/chain" style="color:#58a6ff">view chain</a>
    </div>

    <div class="section">LIVE SENSOR + ATTACK LOG</div>
    <table>
      <tr><th>Time</th><th>Source</th><th>IP</th>
          <th>Device</th><th>Distance</th><th>Status</th></tr>"""

    for log in reversed(logs[-20:]):
        src   = log['source']
        atk   = log.get('attack')
        scls  = 'honeypot' if src == 'HONEYPOT' else 'esp32'
        stxt  = f'<span class="{scls}">{src}</span>'
        atxt  = (f'<span class="attack">{atk}</span>'
                 if atk else '<span class="ok">normal</span>')
        html += f"""<tr>
          <td>{log['time'][:19]}</td>
          <td>{stxt}</td>
          <td>{log['ip']}</td>
          <td>{log['device']}</td>
          <td>{log['distance']} cm</td>
          <td>{atxt}</td></tr>"""

    html += """</table>

    <div class="section">LATEST BLOCKCHAIN BLOCKS</div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:8px">"""

    for block in reversed(chain[-8:]):
        html += f"""<div class="block-row">
          <span style="color:#8b949e">#{block['index']}</span>
          &nbsp;<span style="color:#e3b341">{block['event']}</span>
          &nbsp;<span style="color:#8b949e">{block['timestamp'][:19]}</span>
          &nbsp;<span style="color:#3fb950">{block['hash'][:24]}...</span>
        </div>"""

    html += "</div></body></html>"
    return html

if __name__ == '__main__':
    print("Month 2 Flask server starting...")
    print("Dashboard : http://localhost:5000/dashboard")
    print("Blockchain: http://localhost:5000/chain")
    print("Verify    : http://localhost:5000/verify")
    app.run(host='0.0.0.0', port=5000, debug=True)