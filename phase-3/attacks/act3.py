import requests, time, random

# Same 4 attacks — only TARGET changes to ESP8266 IP
TARGET = "http://172.20.10.2/data"   # your ESP8266 IP

def false_data():
    print("\n[ATTACK 2] FALSE DATA — RL will block on first hit")
    for v in [-99, -1, 9999, 5000, 0.0001, 450]:
        try:
            r = requests.post(TARGET,
                json={"device":"esp32","distance":v}, timeout=5)
            print(f"  Injected {v} → {r.status_code}")
            if r.status_code == 403:
                print("  RL AGENT BLOCKED ME")
                return
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.5)

def replay():
    print("\n[ATTACK 3] REPLAY — RL will block after 5 repeats")
    pkt = {"device":"esp32","distance":24.5}
    for i in range(20):
        try:
            r = requests.post(TARGET, json=pkt, timeout=5)
            print(f"  Replay {i+1} → {r.status_code}")
            if r.status_code == 403:
                print("  RL AGENT BLOCKED ME")
                return
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.2)

def spoof():
    print("\n[ATTACK 4] SPOOFING — RL will block immediately")
    for dev in ["esp32_trusted","admin_sensor","sensor_01"]:
        for _ in range(5):
            try:
                r = requests.post(TARGET,
                    json={"device":dev,
                          "distance":round(random.uniform(5,30),1)},
                    timeout=5)
                print(f"  Spoof '{dev}' → {r.status_code}")
                if r.status_code == 403:
                    print("  RL AGENT BLOCKED ME")
                    return
            except Exception as e:
                print(f"  Failed: {e}")
            time.sleep(0.3)

def flood():
    print("\n[ATTACK 1] FLOOD — RL will block after 10+ requests")
    for i in range(100):
        try:
            r = requests.post(TARGET,
                json={"device":"esp32",
                      "distance":round(random.uniform(10,50),1)},
                timeout=5)
            print(f"  Flood {i+1} → {r.status_code}")
            if r.status_code == 403:
                print(f"  RL AGENT BLOCKED ME at request {i+1}")
                return
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.05)

if __name__ == "__main__":
    print(f"Month 3 — attacking honeypot at {TARGET}")
    print("Watch Flask terminal for RL decisions\n")
    false_data(); time.sleep(3)
    replay();     time.sleep(3)
    spoof();      time.sleep(3)
    flood()
    print("\nAll attacks done.")