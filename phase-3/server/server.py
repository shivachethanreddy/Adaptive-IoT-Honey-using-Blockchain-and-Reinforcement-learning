import hashlib, json, datetime, pickle, os
import numpy as np
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

logs        = []
blocked_ips = set()
ip_times    = {}
ip_vals     = {}
KNOWN_IPS   = {"esp32": "172.20.10.3"}

# ══════════════════════════════════════
#  LOAD RL AGENT
# ══════════════════════════════════════
rl_decisions = []   # log of every RL decision

if os.path.exists("q_table.pkl"):
    Q = pickle.load(open("q_table.pkl", "rb"))
    print("RL agent loaded — q_table.pkl found")
else:
    Q = np.zeros((16, 3))
    print("WARNING: q_table.pkl not found — run train.py first")

def get_state(ip, dist, dev):
    # Feature 1 — request rate
    now = datetime.datetime.now().timestamp()
    t   = ip_times.get(ip, [])
    t   = [x for x in t if now - x < 10]
    t.append(now)
    ip_times[ip] = t
    rate = len(t)

    # Feature 2 — distance anomaly
    anomaly = int(dist < 2 or dist > 400)

    # Feature 3 — known IP
    known = int(ip == KNOWN_IPS.get(dev, ""))

    # Feature 4 — repeat payload
    v = ip_vals.get(ip, [])
    v.append(round(dist, 1))
    ip_vals[ip] = v[-10:]
    repeat = int(v.count(round(dist, 1)) >= 5)

    state_idx = int(f"{int(rate>10)}{anomaly}{int(not known)}{repeat}", 2)
    return state_idx, rate, anomaly, known, repeat

def rl_action(ip, dist, dev):
    s, rate, anomaly, known, repeat = get_state(ip, dist, dev)
    action = int(np.argmax(Q[s]))
    labels = ["allow", "warn", "block"]
    return labels[action], s, rate, anomaly, known, repeat

# ══════════════════════════════════════
#  BLOCKCHAIN
# ══════════════════════════════════════
CHAIN_FILE = "blockchain.json"
chain = []

def save_chain():
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain, f, indent=2)

def compute_hash(block):
    record = {k: v for k, v in block.items() if k != "hash"}
    return hashlib.sha256(
        json.dumps(record, sort_keys=True).encode()).hexdigest()

def add_block(event_type, data):
    prev_hash = chain[-1]["hash"] if chain else "0" * 64
    block = {
        "index"    : len(chain),
        "timestamp": str(datetime.datetime.now()),
        "event"    : event_type,
        "data"     : data,
        "prev_hash": prev_hash,
        "hash"     : ""
    }
    block["hash"] = compute_hash(block)
    chain.append(block)
    save_chain()
    print(f"[CHAIN] #{block['index']} {event_type} | {block['hash'][:16]}...")
    return block

def verify_chain():
    for i, block in enumerate(chain):
        if block["hash"] != compute_hash(block):
            return False, f"Block {i} tampered"
        if i > 0 and block["prev_hash"] != chain[i-1]["hash"]:
            return False, f"Block {i} broken link"
    return True, "Chain is valid"

add_block("GENESIS", {"message": "Month 3 — RL agent active"})

# ══════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════

# Real ESP32 data
@app.route('/data', methods=['POST'])
def real_data():
    ip   = request.remote_addr
    data = request.get_json(force=True)
    dist = data.get("distance", 0)
    dev  = data.get("device", "unknown")
    logs.append({"ip":ip,"device":dev,"distance":dist,
                 "time":str(datetime.datetime.now()),
                 "source":"ESP32","attack":None,"rl":None})
    add_block("SENSOR_DATA", {"ip":ip,"distance":dist,"device":dev})
    return jsonify({"status": "ok"})

# ESP8266 honeypot — RL agent makes decision here
@app.route('/honeypot', methods=['POST'])
def honeypot_data():
    attacker_ip = request.args.get("attacker_ip", request.remote_addr)

    if attacker_ip in blocked_ips:
        return jsonify({"status": "already_blocked"}), 403

    data = request.get_json(force=True)
    dist = data.get("distance", 0)
    dev  = data.get("device", "unknown")
    now  = str(datetime.datetime.now())

    # RL agent decides
    decision, state, rate, anomaly, known, repeat = rl_action(
        attacker_ip, dist, dev)

    print(f"[RL] IP={attacker_ip} state={state} "
          f"rate={rate} anomaly={anomaly} "
          f"known={known} repeat={repeat} "
          f"→ {decision.upper()}")

    rl_decisions.append({
        "ip"      : attacker_ip,
        "dist"    : dist,
        "state"   : state,
        "decision": decision,
        "time"    : now
    })

    logs.append({"ip":attacker_ip,"device":dev,"distance":dist,
                 "time":now,"source":"HONEYPOT",
                 "attack":decision,"rl":decision})

    # Write RL decision to blockchain
    add_block("RL_DECISION", {
        "attacker_ip": attacker_ip,
        "decision"   : decision,
        "state"      : state,
        "distance"   : dist
    })

    # Auto-block if RL says block
    if decision == "block":
        blocked_ips.add(attacker_ip)
        add_block("IP_BLOCKED", {
            "ip"    : attacker_ip,
            "reason": "rl_agent_auto_block",
            "time"  : now
        })
        print(f"[AUTO-BLOCK] {attacker_ip} blocked by RL agent")
        return jsonify({"status": "blocked_by_rl"}), 403

    return jsonify({"status": "ok", "rl_decision": decision})

# Manual block still available for comparison demo
@app.route('/block/<ip>', methods=['POST'])
def block_ip(ip):
    blocked_ips.add(ip)
    add_block("IP_BLOCKED", {"ip":ip,"reason":"manual_block"})
    return jsonify({"blocked": ip})

@app.route('/chain')
def show_chain():
    return jsonify(chain)

@app.route('/verify')
def verify():
    valid, message = verify_chain()
    return jsonify({"valid":valid,"message":message,"blocks":len(chain)})

@app.route('/logs')
def show_logs():
    return jsonify(logs[-50:])

@app.route('/rl_log')
def show_rl():
    return jsonify(rl_decisions[-50:])

# Dashboard
@app.route('/dashboard')
def dashboard():
    valid, vmsg = verify_chain()
    chain_color = "#56d364" if valid else "#f85149"
    chain_status = "VALID" if valid else "TAMPERED"

    auto_blocks  = sum(1 for b in chain if b["event"] == "IP_BLOCKED"
                      and b["data"].get("reason") == "rl_agent_auto_block")
    total_hits   = sum(1 for l in logs if l["source"] == "HONEYPOT")
    total_blocks = len(blocked_ips)

    html = f"""<html><head>
    <title>IoT Security — Month 3 RL</title>
    <meta http-equiv="refresh" content="3">
    <style>
      body{{font-family:monospace;padding:20px;background:#0d1117;color:#c9d1d9;margin:0}}
      h2{{color:#58a6ff;margin-bottom:4px}}
      .sub{{color:#8b949e;font-size:13px;margin-bottom:20px}}
      .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
      .stat{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;text-align:center}}
      .stat-num{{font-size:24px;font-weight:bold}}
      .stat-label{{font-size:11px;color:#8b949e;margin-top:4px}}
      .chain-bar{{background:#161b22;border:1px solid #30363d;border-radius:8px;
                  padding:10px 16px;margin-bottom:16px;font-size:13px}}
      table{{width:100%;border-collapse:collapse;margin-bottom:16px}}
      th{{background:#161b22;color:#8b949e;padding:8px;text-align:left;
          border:1px solid #30363d;font-size:11px}}
      td{{padding:7px 8px;border:1px solid #30363d;font-size:12px}}
      .block{{color:#f85149;font-weight:bold}}
      .warn{{color:#e3b341}}
      .allow{{color:#56d364}}
      .esp32{{color:#58a6ff}}
      .honeypot{{color:#e3b341}}
      .section{{color:#8b949e;font-size:12px;margin:14px 0 6px;font-weight:bold}}
      .brow{{font-size:11px;padding:5px 8px;border-bottom:1px solid #21262d;font-family:monospace}}
      .brow:last-child{{border-bottom:none}}
    </style></head><body>
    <h2>IoT Security Monitor — Month 3 (RL Agent)</h2>
    <div class="sub">Auto-refresh every 3s | RL auto-blocking active</div>

    <div class="stats">
      <div class="stat">
        <div class="stat-num" style="color:#58a6ff">
          {len([l for l in logs if l['source']=='ESP32'])}</div>
        <div class="stat-label">Real readings (ESP32)</div>
      </div>
      <div class="stat">
        <div class="stat-num" style="color:#e3b341">{total_hits}</div>
        <div class="stat-label">Honeypot hits</div>
      </div>
      <div class="stat">
        <div class="stat-num" style="color:#f85149">{auto_blocks}</div>
        <div class="stat-label">RL auto-blocks</div>
      </div>
      <div class="stat">
        <div class="stat-num" style="color:#56d364">{len(chain)}</div>
        <div class="stat-label">Blockchain blocks</div>
      </div>
    </div>

    <div class="chain-bar">
      Chain: <span style="color:{chain_color};font-weight:bold">{chain_status}</span>
      &nbsp;|&nbsp; {len(chain)} blocks &nbsp;|&nbsp; {vmsg}
      &nbsp;&nbsp;
      <a href="/verify" style="color:#58a6ff">verify</a> |
      <a href="/chain" style="color:#58a6ff">chain</a> |
      <a href="/rl_log" style="color:#58a6ff">rl log</a>
    </div>

    <div class="section">LIVE REQUEST LOG</div>
    <table>
      <tr><th>TIME</th><th>SOURCE</th><th>IP</th>
          <th>DISTANCE</th><th>RL DECISION</th></tr>"""

    for log in reversed(logs[-15:]):
        src  = log["source"]
        rl   = log.get("rl") or "—"
        scls = "honeypot" if src == "HONEYPOT" else "esp32"
        rcls = rl if rl in ("allow","warn","block") else ""
        html += f"""<tr>
          <td>{log['time'][:19]}</td>
          <td><span class="{scls}">{src}</span></td>
          <td>{log['ip']}</td>
          <td>{log['distance']} cm</td>
          <td><span class="{rcls}">{rl.upper()}</span></td></tr>"""

    html += """</table>
    <div class="section">LATEST BLOCKCHAIN BLOCKS</div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:8px">"""

    for block in reversed(chain[-10:]):
        ecolor = ("#f85149" if "BLOCK" in block['event']
                  else "#e3b341" if "ATTACK" in block['event']
                  else "#56d364" if "SENSOR" in block['event']
                  else "#8b949e")
        html += f"""<div class="brow">
          <span style="color:#8b949e">#{block['index']}</span>
          &nbsp;<span style="color:{ecolor}">{block['event']}</span>
          &nbsp;<span style="color:#8b949e">{block['timestamp'][:19]}</span>
          &nbsp;<span style="color:#3fb950">{block['hash'][:20]}...</span>
        </div>"""

    html += "</div></body></html>"
    return html

if __name__ == '__main__':
    print("Month 3 Flask — RL Agent active")
    print("Dashboard : http://localhost:5000/dashboard")
    print("Chain     : http://localhost:5000/chain")
    print("Verify    : http://localhost:5000/verify")
    print("RL Log    : http://localhost:5000/rl_log")
    app.run(host='0.0.0.0', port=5000, debug=True)