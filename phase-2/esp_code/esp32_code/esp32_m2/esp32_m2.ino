#include <WiFi.h>
#include <HTTPClient.h>
// NO WebServer — no open ports — invisible to attacker

const char* ssid     = "iPhone";
const char* password = "shiva1234";
const char* flaskURL = "http://172.20.10.6:5000/data";

#define TRIG 5
#define ECHO 18

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
  Serial.println("No ports open — invisible to attacker scan");
}

float getDistance() {
  digitalWrite(TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long d = pulseIn(ECHO, HIGH, 30000);
  return (d == 0) ? -1 : d * 0.034 / 2;
}

void loop() {
  float dist = getDistance();
  Serial.println("Distance: " + String(dist) + " cm");

  HTTPClient http;
  http.begin(flaskURL);
  http.addHeader("Content-Type", "application/json");
  String body = "{\"device\":\"esp32\","
                "\"distance\":" + String(dist) + "}";
  int code = http.POST(body);
  Serial.println("Flask: " + String(code));
  http.end();
  delay(3000);
}