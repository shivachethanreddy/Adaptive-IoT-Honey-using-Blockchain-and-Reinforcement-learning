import hashlib, json, datetime, os
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
# ETHEREUM SETUP (YOUR DATA)
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
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "attacks",
        "outputs": [
            {"internalType": "string", "name": "ip", "type": "string"},
            {"internalType": "string", "name": "attackType", "type": "string"},
            {"internalType": "string", "name": "dataHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# =============================
# ETH LOG FUNCTION
# =============================
def log_to_eth(ip, attack_type, data):
    try:
        data_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

        nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

        tx = contract.functions.logAttack(
            ip,
            attack_type,
            data_hash
        ).build_transaction({
            'from': ACCOUNT_ADDRESS,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.to_wei('10', 'gwei'),
            'chainId': 11155111  # Sepolia
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
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()

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
# ATTACK DETECTION
# =============================
def detect_attack(ip, dist, dev):
    now = datetime.datetime.now()

    t = ip_times.get(ip, [])
    t = [x for x in t if now.timestamp() - x < 10]
    t.append(now.timestamp())
    ip_times[ip] = t

    if len(t) > 10:
        return "FLOOD"
    if dist < 2 or dist > 400:
        return "FALSE_DATA"

    v = ip_vals.get(ip, [])
    v.append(round(dist,1))
    ip_vals[ip] = v[-10:]

    if v.count(round(dist,1)) >= 5:
        return "REPLAY"

    return None

# =============================
# ROUTES
# =============================
@app.route('/data', methods=['POST'])
def real():
    ip = request.remote_addr
    data = request.get_json()

    add_block("SENSOR", data)
    return jsonify({"ok": True})

@app.route('/honeypot', methods=['POST'])
def honeypot():
    ip = request.args.get("attacker_ip", request.remote_addr)
    data = request.get_json()

    atk = detect_attack(ip, data.get("distance", 0), data.get("device", ""))

    if atk:
        attack_data = {
            "ip": ip,
            "attack": atk,
            "data": data
        }

        add_block("ATTACK", attack_data)

        # 🔥 ETH LOGGING
        log_to_eth(ip, atk, attack_data)

    return jsonify({"attack": atk})

@app.route('/chain')
def get_chain():
    return jsonify(chain)

# =============================
# RUN
# =============================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

