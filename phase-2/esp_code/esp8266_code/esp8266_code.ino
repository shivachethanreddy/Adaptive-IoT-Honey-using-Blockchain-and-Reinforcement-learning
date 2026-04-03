#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

const char* ssid     = "iPhone";
const char* password = "shiva1234";
const char* flaskURL = "http://172.20.10.6:5000/honeypot";

ESP8266WebServer server(80);  // port 80 OPEN — attacker finds this

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nHoneypot IP: " + WiFi.localIP().toString());
  Serial.println("Port 80 OPEN — waiting for attacker...");

  // /data — looks identical to real ESP32 endpoint
  server.on("/data", HTTP_POST, []() {
    String attackerIP = server.client().remoteIP().toString();
    String body       = server.arg("plain");

    Serial.println("=== HONEYPOT HIT ===");
    Serial.println("Attacker IP : " + attackerIP);
    Serial.println("Payload     : " + body);

    // Forward to Flask with attacker IP
    WiFiClient wifiClient;
    HTTPClient http;
    String url = String(flaskURL) + "?attacker_ip=" + attackerIP;
    http.begin(wifiClient, url);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(body);
    Serial.println("Flask response: " + String(code));
    http.end();

    // Reply OK to attacker — they think attack worked
    server.send(200, "application/json", "{\"status\":\"ok\"}");
  });

  // /info — fake ESP32 identity page
  server.on("/info", HTTP_GET, []() {
    server.send(200, "application/json",
      "{\"device\":\"ESP32\","
      "\"sensor\":\"HC-SR04\","
      "\"firmware\":\"1.0.2\","
      "\"status\":\"active\"}");
  });

  // / — root page so it shows up convincingly in browser
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/plain", "ESP32 sensor online");
  });

  server.begin();
}

void loop() {
  server.handleClient();
}