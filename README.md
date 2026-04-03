# Adaptive-IoT-Honey-using-Blockchain-and-Reinforcement-learning


An end-to-end IoT security project that demonstrates how a **real IoT device can be hacked** and how a **honeypot + AI + blockchain** can detect, block, and log attacks in real time.

---

## 📌 Project Overview

IoT devices often lack strong security, making them vulnerable to cyberattacks. This project demonstrates:

1. Attacks on a real IoT device (ESP32 + Ultrasonic Sensor)  
2. Detection using a Honeypot Security Layer  
3. Intelligent blocking using Reinforcement Learning (Q-Learning)  
4. Tamper-proof attack logging using Blockchain (Hash Chain)

---

## 🎯 Objectives

- Demonstrate real IoT vulnerabilities  
- Build a honeypot to attract attackers  
- Use AI to learn malicious behavior  
- Securely store attack logs using blockchain  
- Compare **before vs after security**

---

## 🏗️ System Architecture

The system contains five layers:

1. IoT Device Layer  
2. Attack Simulation Layer  
3. Honeypot Server  
4. Reinforcement Learning Agent  
5. Blockchain Logger  

---

## 🧩 Hardware

| Component | Purpose |
|---|---|
| ESP32 | Real IoT device |
| HC-SR04 Ultrasonic Sensor | Generates real sensor data |
| Laptop/PC,ESP32 | Honeypot & Server |

---

## ⚙️ Software Stack

| Layer | Technology |
|---|---|
| Firmware | Arduino / C++ |
| Honeypot | Python |
| RL | Q-Learning |
| Blockchain | SHA-256 Hash Chain |
| Networking | TCP Sockets |

---

## 🚨 Attacks Demonstrated

- Unauthorized Access  
- Brute Force / Flood Attack  
- Data Manipulation  
- Denial of Service (DoS)

### Without Security
Device becomes slow, unstable, and compromised.

### With Honeypot
- Traffic diverted to honeypot  
- RL detects malicious behavior  
- Attacker IP blocked  
- Logs stored on blockchain  
- Device works normally

---

## 🧠 Reinforcement Learning

**Algorithm:** Q-Learning

**State**
- Request rate  
- Packet size  
- Command validity  

**Actions**
- Allow  
- Rate-limit  
- Redirect  
- Block

**Reward**
- +1 Correct block  
- −1 False positive  
- −2 Missed attack  

---

## ⛓️ Blockchain Logging

Each attack stored as:
Block = {
timestamp,
attacker_hash,
attack_type,
previous_hash,
current_hash
}
Ensures tamper-proof logs and traceability.

---


## 📊 Evaluation

- Detection accuracy  
- Response time  
- System stability  
- False positives  

---
## ⭐ Highlight
Real IoT hacking + Real-time AI defense using low-cost hardware.
