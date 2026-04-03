import json, requests

# Fetch logs from Month 2 Flask server
# Make sure Month 2 app.py is still running when you run this
response = requests.get("http://localhost:5000/logs")
logs = response.json()

dataset = []
ip_times = {}
ip_vals  = {}

for log in logs:
    ip   = log["ip"]
    dist = log.get("distance", 0)
    dev  = log.get("device", "unknown")
    src  = log.get("source", "")
    atk  = log.get("attack")

    # Feature 1 — request rate (simplified from log)
    ip_times[ip] = ip_times.get(ip, 0) + 1
    rate = ip_times[ip]

    # Feature 2 — distance anomaly
    anomaly = int(dist < 2 or dist > 400)

    # Feature 3 — repeat payload
    vals = ip_vals.get(ip, [])
    vals.append(round(dist, 1))
    ip_vals[ip] = vals[-10:]
    repeat = int(vals.count(round(dist, 1)) >= 5)

    # Feature 4 — known IP (ESP32 IP)
    known = int(ip == "172.20.10.3")

    # Label
    is_attack = int(atk is not None or src == "HONEYPOT")

    dataset.append({
        "ip"       : ip,
        "rate"     : rate,
        "anomaly"  : anomaly,
        "repeat"   : repeat,
        "known"    : known,
        "is_attack": is_attack,
        "attack"   : atk
    })

with open("attack_dataset.json", "w") as f:
    json.dump(dataset, f, indent=2)

print(f"Dataset exported: {len(dataset)} rows")
print(f"  Attacks : {sum(1 for d in dataset if d['is_attack'])}")
print(f"  Normal  : {sum(1 for d in dataset if not d['is_attack'])}")
print("Saved to attack_dataset.json")