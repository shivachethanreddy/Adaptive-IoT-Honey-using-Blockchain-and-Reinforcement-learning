#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>

const char* ssid     = "iPhone";
const char* password = "shiva1234";
const char* flaskURL = "http://172.20.10.6:5000/data";  // fixed: added :5000

#define TRIG 5
#define ECHO 18

WebServer espServer(80);

void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nESP32 IP: " + WiFi.localIP().toString());

  espServer.on("/", HTTP_GET, []() {
    espServer.send(200, "text/plain", "ESP32 sensor online");
  });

  espServer.on("/data", HTTP_POST, []() {
    String attackerIP = espServer.client().remoteIP().toString();
    String body       = espServer.arg("plain");
    Serial.println(">>> ATTACK HIT from " + attackerIP + " : " + body);
    espServer.send(200, "application/json", "{\"status\":\"ok\"}");
  });

  espServer.begin();
  Serial.println("Port 80 OPEN — attackers can hit this");
  Serial.println("Flask URL: " + String(flaskURL));
}

float getDistance() {
  digitalWrite(TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long d = pulseIn(ECHO, HIGH, 30000);
  return (d == 0) ? -1 : d * 0.034 / 2;
}

void loop() {
  espServer.handleClient();  // handles attacker requests

  float dist = getDistance();
  Serial.println("Distance: " + String(dist) + " cm");

  HTTPClient http;
  http.begin(flaskURL);
  http.addHeader("Content-Type", "application/json");
  String body = "{\"device\":\"esp32\",\"distance\":" + String(dist) + "}";
  int code = http.POST(body);
  Serial.println("Flask response: " + String(code));
  http.end();
  delay(3000);
}