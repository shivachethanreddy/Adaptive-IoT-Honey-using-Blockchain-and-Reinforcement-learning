import hashlib, json, datetime, os, pickle
import numpy as np
from flask import Flask, request, jsonify
from web3 import Web3
from dotenv import load_dotenv

# =============================
# LOAD ENV
# =============================
load_dotenv()
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# =============================
# FLASK INIT
# =============================
app = Flask(__name__)

logs = []
blocked_ips = set()
ip_times = {}
ip_vals = {}

# =============================
# RL MODEL LOAD
# =============================
if os.path.exists("q_table.pkl"):
    Q = pickle.load(open("q_table.pkl", "rb"))
    print("RL agent loaded")
else:
    Q = np.zeros((16,3))
    print("WARNING: q_table.pkl not found")

# =============================
# ETHEREUM SETUP
# =============================
INFURA_URL = "https://sepolia.infura.io/v3/df3b7e3cb59d490d89f0c591ecb1c514"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0x89885880af3d9948854A67Bb67D04E5929EE944d"
)

ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_ip", "type": "string"},
            {"internalType": "string", "name": "_type", "type": "string"},
            {"internalType": "string", "name": "_hash", "type": "string"}
        ],
        "name": "logAttack",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# =============================
# ETH LOG FUNCTION
# =============================
def log_to_eth(ip, attack_type, data):
    try:
        data_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

        nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

        tx = contract.functions.logAttack(
            ip, attack_type, data_hash
        ).build_transaction({
            'from': ACCOUNT_ADDRESS,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.to_wei('10', 'gwei'),
            'chainId': 11155111
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"[ETH] Logged → {tx_hash.hex()[:20]}...")

    except Exception as e:
        print("[ETH ERROR]", e)

# =============================
# LOCAL BLOCKCHAIN
# =============================
chain = []

def compute_hash(block):
    record = {k: v for k, v in block.items() if k != "hash"}
    return hashlib.sha256(
        json.dumps(record, sort_keys=True).encode()
    ).hexdigest()

def add_block(event, data):
    prev_hash = chain[-1]["hash"] if chain else "0"*64
    block = {
        "index": len(chain),
        "time": str(datetime.datetime.now()),
        "event": event,
        "data": data,
        "prev_hash": prev_hash,
        "hash": ""
    }
    block["hash"] = compute_hash(block)
    chain.append(block)

# =============================
# RL STATE + ACTION
# =============================
def get_state(ip, dist, dev):
    now = datetime.datetime.now().timestamp()

    t = ip_times.get(ip, [])
    t = [x for x in t if now - x < 10]
    t.append(now)
    ip_times[ip] = t
    rate = len(t)

    anomaly = int(dist < 2 or dist > 400)
    known = int(dev == "esp32")

    v = ip_vals.get(ip, [])
    v.append(round(dist,1))
    ip_vals[ip] = v[-10:]
    repeat = int(v.count(round(dist,1)) >= 5)

    state = int(f"{int(rate>10)}{anomaly}{int(not known)}{repeat}", 2)
    return state, rate, anomaly, known, repeat

def rl_action(ip, dist, dev):
    s, rate, anomaly, known, repeat = get_state(ip, dist, dev)
    action = int(np.argmax(Q[s]))
    labels = ["allow", "warn", "block"]
    return labels[action], s, rate, anomaly, known, repeat

# =============================
# RULE ENGINE (IMPROVED)
# =============================
def rule_engine(ip, dist, dev):
    now = datetime.datetime.now().timestamp()

    # RATE → FLOOD
    t = ip_times.get(ip, [])
    t = [x for x in t if now - x < 10]
    t.append(now)
    ip_times[ip] = t
    rate = len(t)

    if rate > 12:
        return "block", "FLOOD", rate, 0, 0, 1

    # ANOMALY → FALSE DATA
    anomaly = int(dist < 2 or dist > 400)
    if anomaly:
        return "block", "FALSE_DATA", rate, anomaly, 0, 0

    # REPLAY
    v = ip_vals.get(ip, [])
    v.append(round(dist,1))
    ip_vals[ip] = v[-10:]
    repeat = int(v.count(round(dist,1)) >= 5)

    if repeat:
        return "block", "REPLAY", rate, anomaly, repeat, 0

    # SPOOF
    known = int(dev == "esp32")
    if not known:
        return "warn", "SPOOF", rate, anomaly, repeat, known

    return "allow", None, rate, anomaly, repeat, known

# =============================
# ROUTES
# =============================

@app.route('/data', methods=['POST'])
def real():
    data = request.get_json()
    add_block("SENSOR", data)
    return jsonify({"ok": True})

@app.route('/honeypot', methods=['POST'])
def honeypot():
    ip = request.args.get("attacker_ip", request.remote_addr)

    if ip in blocked_ips:
        return jsonify({"status": "blocked"}), 403

    data = request.get_json()
    dist = data.get("distance", 0)
    dev  = data.get("device", "")

    # RULE ENGINE
    rule_dec, attack_type, rate, anomaly, repeat, known = rule_engine(ip, dist, dev)

    # RL AGENT
    rl_dec, state, _, _, _, _ = rl_action(ip, dist, dev)

    # FINAL DECISION
    if rule_dec == "block":
        final = "block"
        reason = attack_type or "RULE_BASED"

    elif rl_dec == "block":
        final = "block"
        reason = "RL_DETECTED"

    elif rule_dec == "warn" or rl_dec == "warn":
        final = "warn"
        reason = attack_type or "SUSPICIOUS"

    else:
        final = "allow"
        reason = None

    print(f"[HYBRID] {ip} → Rule={rule_dec}, RL={rl_dec} → FINAL={final}")

    log_data = {
        "ip": ip,
        "distance": dist,
        "device": dev,
        "rule": rule_dec,
        "rl": rl_dec,
        "final": final,
        "reason": reason,
        "state": state,
        "rate": rate,
        "anomaly": anomaly,
        "repeat": repeat,
        "known": known
    }

    add_block("HYBRID_DECISION", log_data)

    # BLOCK + ETH
    if final == "block":
        blocked_ips.add(ip)

        add_block("IP_BLOCKED", {
            "ip": ip,
            "reason": reason
        })

        log_to_eth(ip, reason or "HYBRID", log_data)

        return jsonify({"status": "blocked"}), 403

    return jsonify({
        "status": "ok",
        "rule": rule_dec,
        "rl": rl_dec,
        "final": final
    })

@app.route('/chain')
def get_chain():
    return jsonify(chain)

# =============================
# RUN
# =============================
if __name__ == '__main__':
    print("🔥 FINAL HYBRID SYSTEM RUNNING")
    app.run(host='0.0.0.0', port=5000, debug=True)