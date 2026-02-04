#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "iPhone";
const char* password = "shiva1234";
const char* serverURL = "http://172.20.10.2:5000/data";  // ✅ FIXED

#define TRIG_PIN 5
#define ECHO_PIN 18

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ WiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  long duration;
  float distance;

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH);
  distance = duration * 0.034 / 2;

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"distance\": " + String(distance) + "}";
    int httpCode = http.POST(payload);   // ✅ capture response

    Serial.print("Distance: ");
    Serial.print(distance);
    Serial.print(" cm | POST code: ");
    Serial.println(httpCode);

    http.end();
  }

  delay(2000);
}

