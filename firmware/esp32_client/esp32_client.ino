/*
 * MotionCare — ESP32-S3 төхөөрөмжийн жишээ код
 *
 * Үүрэг:
 *   1) MPU6050-аас ~50 Hz давтамжтай уншина
 *   2) 0.5 сек тутам 25 хэмжилтийг GPS-ийн хамт серверийн /api/ingest руу илгээнэ
 *   3) Серверийн хариу (ангиллын үр дүн)-г OLED дээр харуулж, уналтын үед buzzer дуугаргана
 *
 * Сангууд (Arduino Library Manager):
 *   - Adafruit MPU6050, Adafruit Unified Sensor
 *   - Adafruit SSD1306, Adafruit GFX
 *   - TinyGPSPlus
 *   - ArduinoJson (v7)
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_SSD1306.h>
#include <TinyGPSPlus.h>
#include <ArduinoJson.h>

// ---------- Тохиргоо ----------
const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
// Компьютерийн LAN IP хаяг (localhost биш!), жишээ: http://192.168.1.20:3000
const char* SERVER_URL = "http://192.168.1.20:3000/api/ingest";
const char* DEVICE_KEY = "dev-secret-key";
const char* DEVICE_ID = "esp32-01";

const int SAMPLE_HZ = 50;
const int BATCH = 25;          // 0.5 сек
const int BUZZER_PIN = 4;
const int GPS_RX = 18, GPS_TX = 17;

Adafruit_MPU6050 mpu;
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
TinyGPSPlus gps;
HardwareSerial GPSSerial(1);

struct Sample { uint32_t t; float ax, ay, az, gx, gy, gz; };
Sample buf[BATCH];
int bufN = 0;
uint32_t lastSample = 0;

void showOled(const char* l1, const char* l2, const char* l3) {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1); oled.setCursor(22, 4);  oled.print(l1);
  oled.setTextSize(2); oled.setCursor(10, 24); oled.print(l2);
  oled.setTextSize(1); oled.setCursor(10, 50); oled.print(l3);
  oled.display();
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  Wire.begin();
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  showOled("MOTIONCARE", "Booting", "");

  if (!mpu.begin()) { showOled("ERROR", "MPU6050", "not found"); while (true) delay(1000); }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  showOled("MOTIONCARE", "Wi-Fi...", WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) delay(300);
  showOled("MOTIONCARE", "Online", WiFi.localIP().toString().c_str());
}

void sendBatch() {
  if (WiFi.status() != WL_CONNECTED) { showOled("NO WI-FI", "Offline", "reconnecting"); WiFi.reconnect(); return; }

  JsonDocument doc;
  doc["deviceId"] = DEVICE_ID;
  doc["rssi"] = WiFi.RSSI();
  if (gps.location.isValid()) {
    JsonObject g = doc["gps"].to<JsonObject>();
    g["lat"] = gps.location.lat();
    g["lng"] = gps.location.lng();
    g["accuracy"] = gps.hdop.hdop() * 2.5;
  }
  JsonArray arr = doc["samples"].to<JsonArray>();
  for (int i = 0; i < bufN; i++) {
    JsonObject s = arr.add<JsonObject>();
    s["t"] = buf[i].t;  // millis(); сервер өөрийн цагт шилжүүлнэ
    s["ax"] = buf[i].ax; s["ay"] = buf[i].ay; s["az"] = buf[i].az;
    s["gx"] = buf[i].gx; s["gy"] = buf[i].gy; s["gz"] = buf[i].gz;
  }
  String body; serializeJson(doc, body);

  HTTPClient http;
  http.begin(SERVER_URL);
  http.setTimeout(1500);
  http.addHeader("content-type", "application/json");
  http.addHeader("x-device-key", DEVICE_KEY);
  int code = http.POST(body);
  if (code == 200) {
    JsonDocument res;
    if (!deserializeJson(res, http.getString()) && !res["label"].isNull()) {
      bool alert = res["alert"] | false;
      char conf[24];
      snprintf(conf, sizeof(conf), "Confidence: %d%%", (int)((res["confidence"] | 0.0) * 100));
      if (alert) {
        showOled("WARNING!", "FALL", "DETECTED");
        for (int i = 0; i < 3; i++) { digitalWrite(BUZZER_PIN, HIGH); delay(120); digitalWrite(BUZZER_PIN, LOW); delay(80); }
      } else {
        showOled("MOTION STATUS", res["label"] | "---", conf);
      }
    }
  } else {
    Serial.printf("HTTP %d\n", code);
  }
  http.end();
}

void loop() {
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  uint32_t now = millis();
  if (now - lastSample >= 1000 / SAMPLE_HZ) {
    lastSample = now;
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    // m/s² → g, rad/s → °/s. Y тэнхлэг босоо байхаар бүсэлхийд зүүнэ.
    buf[bufN++] = { now, a.acceleration.x / 9.80665f, a.acceleration.y / 9.80665f, a.acceleration.z / 9.80665f,
                    g.gyro.x * 57.2958f, g.gyro.y * 57.2958f, g.gyro.z * 57.2958f };
    if (bufN >= BATCH) { sendBatch(); bufN = 0; }
  }
}
