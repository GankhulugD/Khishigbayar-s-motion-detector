/*
 * =====================================================================
 *  MotionCare — ESP32-C3 SuperMini firmware (нэг файл, нэмэлт сан ХЭРЭГГҮЙ)
 * =====================================================================
 *  Төхөөрөмж : ESP32-C3 SuperMini / ESP32-S3-Zero + MPU9250 + OLED SSD1306 128x64 (I2C)
 *  Холболт   : SDA = GPIO6, SCL = GPIO7  (OLED 0x3C, MPU9250 0x68 )
 *
 *  ХЭРХЭН UPLOAD ХИЙХ ВЭ:
 *   1. Arduino IDE → Boards Manager → "esp32 by Espressif Systems" суулгана.
 *   2. Tools → Board → "ESP32C3 Dev Module"  (ESP32-S3-Zero бол "ESP32S3 Dev Module")
 *      Tools → USB CDC On Boot → "Enabled"   (Serial Monitor-д хэрэгтэй)
 *   3. Доорх "ТОХИРГОО" хэсэгт Wi-Fi нэр, нууц үг, компьютерийн IP-г бичнэ.
 *   4. Upload. Serial Monitor (115200) дээр явцыг харна.
 *
 *  Өөр ямар ч library суулгах шаардлагагүй — OLED драйвер энэ файлд байгаа.
 *
 *  Ажиллах зарчим:
 *   MPU9250-аас 50 Hz уншина → 250 мс тутам Wi-Fi-аар POST /api/ingest →
 *   сервер ML-ээр ангилж хариу буцаана.
 *   OLED: дээд мөрөнд ангилал, доор нь мэдрэгчийн 6 утга (Ax Ay Az, Gx Gy Gz) шууд.
 *   Веб самбар (http://<компьютер>:3000) бодит хугацаанд шинэчлэгдэнэ.
 * =====================================================================
 */

// ============================== ТОХИРГОО ==============================
#define WIFI_SSID      "YOUR_WIFI_NAME"       // Wi-Fi нэр (зөвхөн 2.4 GHz)
#define WIFI_PASSWORD  "YOUR_WIFI_PASSWORD"   // Wi-Fi нууц үг
#define SERVER_HOST    "192.168.1.20"         // Компьютерийн IP (macOS: ipconfig getifaddr en0)
#define SERVER_PORT    3000                   // Next.js порт
#define DEVICE_KEY     "dev-secret-key"       // .env.local доторх DEVICE_API_KEY
#define DEVICE_ID      "esp32c3-01"           // Төхөөрөмжийн нэр (веб дээр харагдана)
#define OLED_ROTATE_180  1                    // 1 = PCB дээр OLED доошоо харсан (180°), 0 = энгийн
// =====================================================================

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>

static const int      PIN_SDA       = 6;
static const int      PIN_SCL       = 7;
static const uint32_t SAMPLE_HZ     = 50;    // мэдрэгч унших давтамж
static const uint32_t SEND_EVERY_MS = 100;   // сервер рүү (ML) илгээх давтамж
static const uint16_t WS_PORT       = 81;    // веб шууд холбогдох WebSocket порт (ws://<IP>:81)
static const uint16_t MAX_PER_POST  = 50;    // нэг илгээлтэд хамгийн их хэмжилт
static const uint16_t RING_SIZE     = 256;   // сүлжээ тасарсан үеийн буфер (~5 сек)
static const uint8_t  MPU_ADDR      = 0x68;
static const uint8_t  OLED_ADDR     = 0x3C;

// WebSocket клиент (веб хөтөч)
static const int WS_MAX = 3;
struct WsClient { WiFiClient c; bool open; uint32_t since; String req; };

// Хэмжилтийн бүтэц — функцүүдээс ӨМНӨ тодорхойлох ёстой (Arduino prototype дүрэм)
struct Sample {
  uint32_t t;          // millis()
  float ax, ay, az;    // g
  float gx, gy, gz;    // °/s
};

// Функцийн урьдчилсан зарлалт (Arduino IDE-ийн автомат prototype-оос хамааралгүй болгоно)
static bool i2cWrite(uint8_t addr, uint8_t reg, uint8_t val);
static bool i2cRead(uint8_t addr, uint8_t reg, uint8_t* buf, uint8_t len);
static void fbClear();
static void fbPixel(int x, int y, bool on);
static void fbFill(int x, int y, int w, int h, bool on);
static int fbText(int x, int y, const char* s, int scale = 1, bool on = true);
static void oledCmd(uint8_t c);
static bool oledInit();
static void oledFlush();
static bool mpuInit();
static bool mpuRead(Sample& s);
static void sensorTask(void*);
static uint16_t takeSamples(Sample* out, uint16_t maxN);
static void putBack(const Sample* in, uint16_t n);
static void drawScreen();
static void parseResponse(const String& r);
static void ensureWifi();
static void sendBatch();
static void netTask(void*);
static void sha1digest(const uint8_t* msg, size_t len, uint8_t out[20]);
static String b64enc(const uint8_t* d, size_t n);
static void wsSendText(WsClient& k, const char* p, size_t n);
static void wsService();

SemaphoreHandle_t i2cMutex;

// ---------------------------------------------------------------- I2C туслах
static bool i2cWrite(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

static bool i2cRead(uint8_t addr, uint8_t reg, uint8_t* buf, uint8_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, len) != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

// ==== OLED BEGIN ======================================================
// SSD1306 128x64 драйвер (нэмэлт сан хэрэггүй). 6x10 пикселийн фонт.
static const uint16_t FONT6x10[95][6] = {
  {0x000,0x000,0x000,0x000,0x000,0x000},  // ' '
  {0x000,0x0BC,0x0BC,0x000,0x000,0x000},  // '!'
  {0x000,0x01C,0x000,0x01C,0x000,0x000},  // '"'
  {0x048,0x1FE,0x048,0x1FE,0x048,0x000},  // '#'
  {0x0CC,0x0DE,0x19B,0x0FA,0x076,0x000},  // '$'
  {0x04E,0x02A,0x0FE,0x0A8,0x0E4,0x000},  // '%'
  {0x0E8,0x0BC,0x0F4,0x0E4,0x0A0,0x000},  // '&'
  {0x000,0x008,0x006,0x002,0x000,0x000},  // '''
  {0x000,0x078,0x0FC,0x102,0x000,0x000},  // '('
  {0x000,0x102,0x0FC,0x078,0x000,0x000},  // ')'
  {0x014,0x00C,0x00E,0x014,0x000,0x000},  // '*'
  {0x010,0x010,0x07C,0x010,0x010,0x000},  // '+'
  {0x000,0x200,0x180,0x080,0x000,0x000},  // ','
  {0x010,0x010,0x010,0x010,0x010,0x000},  // '-'
  {0x000,0x080,0x080,0x000,0x000,0x000},  // '.'
  {0x000,0x180,0x060,0x018,0x006,0x000},  // '/'
  {0x07C,0x0FE,0x082,0x0FE,0x07C,0x000},  // '0'
  {0x084,0x084,0x0FE,0x0FE,0x080,0x080},  // '1'
  {0x0C4,0x0E6,0x0B2,0x0DE,0x0CC,0x000},  // '2'
  {0x044,0x0D6,0x092,0x0FE,0x06C,0x000},  // '3'
  {0x030,0x038,0x024,0x0FE,0x0FE,0x020},  // '4'
  {0x0DE,0x09E,0x08A,0x0FA,0x072,0x000},  // '5'
  {0x07C,0x0FE,0x092,0x0F6,0x064,0x000},  // '6'
  {0x006,0x0C6,0x0F2,0x03E,0x00E,0x000},  // '7'
  {0x06C,0x0FE,0x092,0x0FE,0x06C,0x000},  // '8'
  {0x04C,0x0DE,0x092,0x0FE,0x07C,0x000},  // '9'
  {0x000,0x090,0x090,0x000,0x000,0x000},  // ':'
  {0x200,0x190,0x090,0x000,0x000,0x000},  // ';'
  {0x010,0x038,0x06C,0x044,0x000,0x000},  // '<'
  {0x028,0x028,0x028,0x028,0x000,0x000},  // '='
  {0x000,0x044,0x06C,0x038,0x010,0x000},  // '>'
  {0x008,0x0A4,0x0B4,0x01C,0x008,0x000},  // '?'
  {0x0FC,0x186,0x132,0x14A,0x07C,0x040},  // '@'
  {0x0E4,0x0FC,0x02C,0x0FC,0x0E0,0x080},  // 'A'
  {0x0FC,0x0FC,0x094,0x0FC,0x068,0x000},  // 'B'
  {0x078,0x0FC,0x084,0x0CC,0x04C,0x000},  // 'C'
  {0x0FC,0x0FC,0x084,0x0FC,0x078,0x000},  // 'D'
  {0x0FC,0x0FC,0x094,0x0D4,0x0C4,0x000},  // 'E'
  {0x0FC,0x0FC,0x094,0x014,0x004,0x000},  // 'F'
  {0x078,0x0FC,0x0A4,0x0EC,0x0E8,0x000},  // 'G'
  {0x0FC,0x0FC,0x010,0x0FC,0x0FC,0x084},  // 'H'
  {0x084,0x0FC,0x0FC,0x084,0x000,0x000},  // 'I'
  {0x0E0,0x084,0x0FC,0x07C,0x004,0x000},  // 'J'
  {0x0FC,0x0FC,0x0B0,0x06C,0x0C4,0x080},  // 'K'
  {0x0FC,0x0FC,0x084,0x0C0,0x0C0,0x000},  // 'L'
  {0x0FC,0x038,0x0E0,0x038,0x0FC,0x000},  // 'M'
  {0x0FC,0x0FC,0x018,0x064,0x0FC,0x004},  // 'N'
  {0x078,0x0FC,0x084,0x0FC,0x078,0x000},  // 'O'
  {0x0FC,0x0FC,0x0A4,0x03C,0x018,0x000},  // 'P'
  {0x078,0x0FC,0x084,0x1FC,0x178,0x000},  // 'Q'
  {0x0FC,0x0FC,0x0A4,0x07C,0x0D8,0x080},  // 'R'
  {0x0D8,0x09C,0x0B4,0x0F4,0x06C,0x000},  // 'S'
  {0x084,0x0FC,0x0FC,0x084,0x00C,0x000},  // 'T'
  {0x07C,0x0FC,0x080,0x0FC,0x07C,0x004},  // 'U'
  {0x00C,0x07C,0x0E0,0x07C,0x00C,0x004},  // 'V'
  {0x03C,0x0E0,0x07C,0x0E0,0x03C,0x004},  // 'W'
  {0x084,0x0CC,0x078,0x078,0x0CC,0x084},  // 'X'
  {0x00C,0x09C,0x0F0,0x0F0,0x09C,0x00C},  // 'Y'
  {0x0CC,0x0EC,0x0B4,0x0DC,0x0CC,0x000},  // 'Z'
  {0x000,0x1FE,0x1FE,0x102,0x000,0x000},  // '['
  {0x006,0x018,0x060,0x180,0x000,0x000},  // 'backslash'
  {0x000,0x102,0x1FE,0x1FE,0x000,0x000},  // ']'
  {0x008,0x00C,0x006,0x00C,0x008,0x000},  // '^'
  {0x200,0x200,0x200,0x200,0x200,0x200},  // '_'
  {0x000,0x002,0x006,0x008,0x000,0x000},  // '`'
  {0x0D0,0x0F8,0x0A8,0x0F8,0x0F0,0x080},  // 'a'
  {0x0FE,0x0FE,0x088,0x0F8,0x070,0x000},  // 'b'
  {0x070,0x0F8,0x088,0x0D8,0x050,0x000},  // 'c'
  {0x070,0x0F8,0x08A,0x0FE,0x0FE,0x080},  // 'd'
  {0x070,0x0F8,0x0A8,0x0B8,0x0B0,0x000},  // 'e'
  {0x088,0x0FC,0x0FE,0x08A,0x08A,0x000},  // 'f'
  {0x270,0x2F8,0x288,0x3F0,0x1F8,0x008},  // 'g'
  {0x0FE,0x0FE,0x008,0x0F8,0x0F0,0x000},  // 'h'
  {0x088,0x088,0x0FA,0x0FA,0x080,0x080},  // 'i'
  {0x208,0x208,0x3FA,0x1FA,0x000,0x000},  // 'j'
  {0x0FE,0x0FE,0x070,0x0D8,0x088,0x080},  // 'k'
  {0x082,0x082,0x0FE,0x0FE,0x080,0x080},  // 'l'
  {0x0F8,0x018,0x0F8,0x018,0x0F0,0x000},  // 'm'
  {0x0F8,0x0F0,0x008,0x0F8,0x0F0,0x000},  // 'n'
  {0x070,0x0F8,0x088,0x0F8,0x070,0x000},  // 'o'
  {0x3F8,0x3F8,0x288,0x0F8,0x070,0x000},  // 'p'
  {0x070,0x0F8,0x288,0x3F0,0x3F8,0x208},  // 'q'
  {0x088,0x0F8,0x0F0,0x098,0x008,0x018},  // 'r'
  {0x090,0x0B8,0x0B8,0x0E8,0x0E8,0x040},  // 's'
  {0x008,0x07E,0x0FE,0x088,0x0C8,0x040},  // 't'
  {0x078,0x0F8,0x080,0x0F8,0x0F8,0x080},  // 'u'
  {0x018,0x078,0x0E0,0x078,0x018,0x000},  // 'v'
  {0x038,0x0E0,0x078,0x0E0,0x078,0x008},  // 'w'
  {0x088,0x0D8,0x078,0x0F0,0x0D8,0x088},  // 'x'
  {0x238,0x3F8,0x180,0x0F8,0x038,0x008},  // 'y'
  {0x0D8,0x0E8,0x0B8,0x0D8,0x0C8,0x000},  // 'z'
  {0x000,0x010,0x0FC,0x1EE,0x102,0x000},  // '{'
  {0x000,0x000,0x1FC,0x000,0x000,0x000},  // '|'
  {0x102,0x1EE,0x0FC,0x010,0x000,0x000},  // '}'
  {0x010,0x008,0x018,0x010,0x008,0x000},  // '~'
};

static uint8_t fb[128 * 64 / 8];

static void fbClear() { memset(fb, 0, sizeof(fb)); }

static void fbPixel(int x, int y, bool on) {
  if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
  if (on) fb[x + (y >> 3) * 128] |= (1 << (y & 7));
  else    fb[x + (y >> 3) * 128] &= ~(1 << (y & 7));
}

static void fbFill(int x, int y, int w, int h, bool on) {
  for (int j = y; j < y + h; j++)
    for (int i = x; i < x + w; i++) fbPixel(i, j, on);
}

// Текст зурах. scale = 1 (6x10) эсвэл 2 (12x20). Буцаах утга: дараагийн x
static int fbText(int x, int y, const char* s, int scale, bool on) {
  for (; *s; s++) {
    char c = *s;
    if (c < 32 || c > 126) c = '?';
    const uint16_t* g = FONT6x10[c - 32];
    for (int col = 0; col < 6; col++)
      for (int row = 0; row < 10; row++)
        if (g[col] & (1 << row)) fbFill(x + col * scale, y + row * scale, scale, scale, on);
    x += 6 * scale;
  }
  return x;
}

static void oledCmd(uint8_t c) {
  Wire.beginTransmission(OLED_ADDR);
  Wire.write(0x00);
  Wire.write(c);
  Wire.endTransmission();
}

static bool oledInit() {
  Wire.beginTransmission(OLED_ADDR);
  if (Wire.endTransmission() != 0) return false;
  const uint8_t seq[] = {
    0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0x8D, 0x14, 0x20, 0x00,
    (uint8_t)(OLED_ROTATE_180 ? 0xA0 : 0xA1),   // сегментийн чиглэл
    (uint8_t)(OLED_ROTATE_180 ? 0xC0 : 0xC8 ),   // мөрийн чиглэл
    0xDA, 0x12, 0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0x2E, 0xAF
  };
  for (uint8_t c : seq) oledCmd(c);
  return true;
}

static void oledFlush() {
  oledCmd(0x21); oledCmd(0); oledCmd(127);   // баганын хүрээ
  oledCmd(0x22); oledCmd(0); oledCmd(7);     // хуудасны хүрээ
  for (size_t i = 0; i < sizeof(fb); i += 16) {
    Wire.beginTransmission(OLED_ADDR);
    Wire.write(0x40);
    Wire.write(fb + i, 16);
    Wire.endTransmission();
  }
}
// ==== OLED END ========================================================

// ---------------------------------------------------------------- MPU9250
static const float ACCEL_LSB_PER_G  = 8192.0f;  // ±4 g
static const float GYRO_LSB_PER_DPS = 65.5f;    // ±500 °/s

static bool mpuInit() {
  uint8_t who = 0;
  if (!i2cRead(MPU_ADDR, 0x75, &who, 1)) {
    Serial.println("[MPU] I2C хариу алга — SDA=6, SCL=7 холболтоо шалга");
    return false;
  }
  // 0x71 = MPU9250, 0x73 = MPU9255, 0x70 = MPU6500, 0x68 = MPU6050
  Serial.printf("[MPU] WHO_AM_I = 0x%02X\n", who);
  i2cWrite(MPU_ADDR, 0x6B, 0x80);   // reset
  delay(100);
  i2cWrite(MPU_ADDR, 0x6B, 0x01);   // PLL цаг
  i2cWrite(MPU_ADDR, 0x6C, 0x00);   // бүх тэнхлэг идэвхтэй
  delay(10);
  i2cWrite(MPU_ADDR, 0x1A, 0x03);   // gyro шүүлтүүр 41 Hz
  i2cWrite(MPU_ADDR, 0x19, 19);     // 1 kHz / 20 = 50 Hz
  i2cWrite(MPU_ADDR, 0x1B, 0x08 );   // gyro ±500 °/s
  i2cWrite(MPU_ADDR, 0x1C, 0x08 );   // accel ±4 g
  i2cWrite(MPU_ADDR, 0x1D, 0x03);   // accel шүүлтүүр 41 Hz
  return true;
}

static bool mpuRead(Sample& s) {
  uint8_t b[14];
  if (!i2cRead(MPU_ADDR, 0x3B, b, 14)) return false;
  s.ax = (int16_t)(b[0] << 8 | b[1]) / ACCEL_LSB_PER_G;
  s.ay = (int16_t)(b[2] << 8 | b[3]) / ACCEL_LSB_PER_G;
  s.az = (int16_t)(b[4] << 8 | b[5]) / ACCEL_LSB_PER_G;
  s.gx = (int16_t)(b[8] << 8 | b[9]) / GYRO_LSB_PER_DPS;
  s.gy = (int16_t)(b[10] << 8 | b[11]) / GYRO_LSB_PER_DPS;
  s.gz = (int16_t)(b[12] << 8 | b[13]) / GYRO_LSB_PER_DPS;
  return true;
}

// ---------------------------------------------------------------- буфер (ring)
static Sample ring[RING_SIZE];
static volatile uint16_t ringHead = 0, ringCount = 0;
static volatile uint32_t droppedSamples = 0;
static portMUX_TYPE ringMux = portMUX_INITIALIZER_UNLOCKED;
static bool mpuOk = false, oledOk = false;
static Sample latest = {};             // OLED-д харуулах хамгийн сүүлийн хэмжилт
static volatile uint32_t sampleCounter = 0;
// Веб рүү шууд (WebSocket) илгээх тусдаа жижиг буфер
static const uint16_t WS_RING = 64;
static Sample wsRing[WS_RING];
static volatile uint16_t wsHead = 0, wsCount = 0;

// 50 Hz-ээр тогтмол уншиж буферт хийнэ (тусдаа task)
static void sensorTask(void*) {
  TickType_t last = xTaskGetTickCount();
  const TickType_t period = pdMS_TO_TICKS(1000 / SAMPLE_HZ);
  while (true) {
    vTaskDelayUntil(&last, period);
    if (!mpuOk) continue;
    Sample s;
    s.t = millis();
    bool ok = false;
    if (xSemaphoreTake(i2cMutex, pdMS_TO_TICKS(40)) == pdTRUE) {
      ok = mpuRead(s);
      xSemaphoreGive(i2cMutex);
    }
    if (!ok) continue;
    portENTER_CRITICAL(&ringMux);
    latest = s;
    sampleCounter++;
    wsRing[wsHead] = s;
    wsHead = (wsHead + 1) % WS_RING;
    if (wsCount < WS_RING) wsCount++;
    ring[ringHead] = s;
    ringHead = (ringHead + 1) % RING_SIZE;
    if (ringCount < RING_SIZE) ringCount++;
    else droppedSamples++;
    portEXIT_CRITICAL(&ringMux);
  }
}

static uint16_t takeSamples(Sample* out, uint16_t maxN) {
  portENTER_CRITICAL(&ringMux);
  uint16_t n = ringCount < maxN ? ringCount : maxN;
  uint16_t tail = (ringHead + RING_SIZE - ringCount) % RING_SIZE;
  for (uint16_t i = 0; i < n; i++) out[i] = ring[(tail + i) % RING_SIZE];
  ringCount -= n;
  portEXIT_CRITICAL(&ringMux);
  return n;
}

// Илгээж чадаагүй өгөгдлийг буферийн эхэнд буцаана
static void putBack(const Sample* in, uint16_t n) {
  portENTER_CRITICAL(&ringMux);
  uint16_t space = RING_SIZE - ringCount;
  uint16_t k = n < space ? n : space;
  uint16_t tail = (ringHead + RING_SIZE - ringCount) % RING_SIZE;
  for (uint16_t i = 0; i < k; i++) {
    tail = (tail + RING_SIZE - 1) % RING_SIZE;
    ring[tail] = in[n - 1 - i];
  }
  ringCount += k;
  portEXIT_CRITICAL(&ringMux);
}

// ---------------------------------------------------------------- дэлгэц
static char     lastLabel[16] = "---";
static int      lastConfidence = 0;
static bool     lastAlert = false;
static uint32_t lastOkResponse = 0;
static uint32_t postFailures = 0;
static portMUX_TYPE labelMux = portMUX_INITIALIZER_UNLOCKED;

static void drawScreen() {
  if (!oledOk) return;
  static uint32_t lastCount = 0, lastT = 0;
  static int hz = 0;
  char line[32];

  Sample s;
  portENTER_CRITICAL(&ringMux);
  s = latest;
  uint32_t cnt = sampleCounter;
  portEXIT_CRITICAL(&ringMux);
  uint32_t now = millis();
  if (now - lastT >= 1000) {             // бодит уншилтын давтамж (Hz)
    hz = (int)((cnt - lastCount) * 1000UL / (now - lastT));
    lastCount = cnt; lastT = now;
  }

  fbClear();
  if (lastAlert) {
    fbFill(0, 0, 128, 64, true);
    fbText(16, 10, "WARNING!", 2, false);
    fbText(25, 38, "FALL DETECTED", 1, false);
    if (xSemaphoreTake(i2cMutex, pdMS_TO_TICKS(100)) == pdTRUE) { oledFlush(); xSemaphoreGive(i2cMutex); }
    return;
  }

  // 1-р мөр: ангилал + холболт
  bool live = WiFi.status() == WL_CONNECTED && millis() - lastOkResponse < 3000;
  portENTER_CRITICAL(&labelMux);
  snprintf(line, sizeof(line), "%s %d%%", lastLabel, lastConfidence);
  portEXIT_CRITICAL(&labelMux);
  fbText(0, 0, live ? line : (WiFi.status() == WL_CONNECTED ? "server --" : "WiFi..."));
  fbText(live ? 98 : 104, 0, live ? "LIVE" : "OFF");
  fbFill(0, 11, 128, 1, true);

  if (!mpuOk) {
    fbText(0, 20, "MPU9250 error");
    fbText(0, 34, "Check SDA=6 SCL=7");
  } else {
    // Мэдрэгчийн утгууд: хурдатгал (g) | эргэлт (°/s)
    snprintf(line, sizeof(line), "Ax%+5.2f Gx%+6.1f", s.ax, s.gx); fbText(0, 14, line);
    snprintf(line, sizeof(line), "Ay%+5.2f Gy%+6.1f", s.ay, s.gy); fbText(0, 26, line);
    snprintf(line, sizeof(line), "Az%+5.2f Gz%+6.1f", s.az, s.gz); fbText(0, 38, line);
    float mag = sqrtf(s.ax * s.ax + s.ay * s.ay + s.az * s.az);
    snprintf(line, sizeof(line), "|a| %.2fg   %dHz", mag, hz);     fbText(0, 52, line);
  }
  if (xSemaphoreTake(i2cMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
    oledFlush();
    xSemaphoreGive(i2cMutex);
  }
}

// ---------------------------------------------------------------- серверийн хариу
// Хариу: {"ok":true,"activity":"walking","label":"Walking","confidence":0.94,"alert":false}
static void parseResponse(const String& r) {
  char label[16] = "";
  int conf = -1;
  int i = r.indexOf("\"label\":" "\"");
  if (i >= 0) {
    i += 9;
    int j = r.indexOf('"', i);
    if (j > i) r.substring(i, j).toCharArray(label, sizeof(label));
  }
  i = r.indexOf("\"confidence\":");
  if (i >= 0) conf = (int)lroundf(r.substring(i + 13).toFloat() * 100.0f);
  bool alert = r.indexOf("\"alert\":true") >= 0;
  portENTER_CRITICAL(&labelMux);
  if (label[0]) memcpy(lastLabel, label, sizeof(lastLabel));
  if (conf >= 0) lastConfidence = conf;
  lastAlert = alert;
  portEXIT_CRITICAL(&labelMux);
}

// ---------------------------------------------------------------- Wi-Fi + HTTP
static void ensureWifi() {
  static uint32_t lastTry = 0;
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastTry < 5000) return;
  lastTry = millis();
  Serial.println("[WiFi] холбогдож байна...");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

static Sample batch[MAX_PER_POST];
static WiFiClient tcp;
static HTTPClient http;

static void sendBatch() {
  if (WiFi.status() != WL_CONNECTED) return;
  uint16_t n = takeSamples(batch, MAX_PER_POST);
  if (n == 0) return;

  String body;
  body.reserve(120 + n * 85);
  body += "{\"deviceId\":" "\"" DEVICE_ID "\",\"rssi\":";
  body += String((int)WiFi.RSSI());
  body += ",\"ip\":" "\"";
  body += WiFi.localIP().toString();
  body += "\"";
  body += ",\"samples\":[";
  char buf[120];
  for (uint16_t i = 0; i < n; i++) {
    const Sample& s = batch[i];
    snprintf(buf, sizeof(buf), "%s{\"t\":%lu,\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,\"gx\":%.2f,\"gy\":%.2f,\"gz\":%.2f}",
             i ? "," : "", (unsigned long)s.t, s.ax, s.ay, s.az, s.gx, s.gy, s.gz);
    body += buf;
  }
  body += "]}";

  static const String url = String("http://") + SERVER_HOST + ":" + String(SERVER_PORT) + "/api/ingest";
  http.begin(tcp, url);
  http.setReuse(true);
  http.setTimeout(1500);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-device-key", DEVICE_KEY);
  int code = http.POST(body);

  if (code == 200) {
    parseResponse(http.getString());
    lastOkResponse = millis();
    postFailures = 0;
  } else {
    postFailures++;
    if (code < 0) {
      Serial.printf("[HTTP] сервертэй холбогдсонгүй (%s) — SERVER_HOST, порт, firewall шалга\n",
                    HTTPClient::errorToString(code).c_str());
      putBack(batch, n);   // өгөгдлийг алдахгүй, дараа дахин илгээнэ
    } else if (code == 401) {
      Serial.println("[HTTP] 401 — DEVICE_KEY нь .env.local-ийн DEVICE_API_KEY-тэй таарахгүй байна");
    } else {
      Serial.printf("[HTTP] серверийн алдаа %d\n", code);
    }
  }
  http.end();
}

// ---------------------------------------------------------------- сервер рүү илгээх task
// HTTP хүсэлт 50–500 мс блоклодог тул тусдаа task-д ажиллуулна → OLED болон веб саатахгүй
static void netTask(void*) {
  uint32_t last = 0;
  while (true) {
    uint32_t now = millis();
    if (now - last >= SEND_EVERY_MS) { last = now; sendBatch(); }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// ---------------------------------------------------------------- WebSocket сервер (сангүй)
// Хөтөч ws://<ESP32 IP>:81 руу шууд холбогдож, хэмжилт бүрийг (50 Hz) хоцролтгүй авна.
// SHA-1 + base64 нь зөвхөн handshake-д хэрэгтэй.
static void sha1digest(const uint8_t* msg, size_t len, uint8_t out[20]) {
  uint32_t h[5] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0};
  size_t total = (len + 72) / 64 * 64;
  uint8_t blk[64];
  for (size_t off = 0; off < total; off += 64) {
    for (int i = 0; i < 64; i++) {
      size_t k = off + i;
      if (k < len) blk[i] = msg[k];
      else if (k == len) blk[i] = 0x80;
      else if (k + 8 >= total) blk[i] = (uint8_t)(((uint64_t)len << 3) >> ((total - 1 - k) << 3));
      else blk[i] = 0;
    }
    uint32_t w[80];
    for (int i = 0; i < 16; i++) w[i] = (uint32_t)blk[i * 4] << 24 | (uint32_t)blk[i * 4 + 1] << 16 | (uint32_t)blk[i * 4 + 2] << 8 | blk[i * 4 + 3];
    for (int i = 16; i < 80; i++) { uint32_t x = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]; w[i] = x << 1 | x >> 31; }
    uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4];
    for (int i = 0; i < 80; i++) {
      uint32_t f, k;
      if (i < 20)      { f = (b & c) | (~b & d);          k = 0x5A827999; }
      else if (i < 40) { f = b ^ c ^ d;                   k = 0x6ED9EBA1; }
      else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
      else             { f = b ^ c ^ d;                   k = 0xCA62C1D6; }
      uint32_t t = (a << 5 | a >> 27) + f + e + k + w[i];
      e = d; d = c; c = b << 30 | b >> 2; b = a; a = t;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e;
  }
  for (int i = 0; i < 20; i++) out[i] = (uint8_t)(h[i / 4] >> (24 - 8 * (i % 4)));
}

static String b64enc(const uint8_t* d, size_t n) {
  static const char* T = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  String o;
  for (size_t i = 0; i < n; i += 3) {
    uint32_t v = (uint32_t)d[i] << 16 | (i + 1 < n ? (uint32_t)d[i + 1] << 8 : 0) | (i + 2 < n ? d[i + 2] : 0);
    o += T[v >> 18 & 63];
    o += T[v >> 12 & 63];
    o += i + 1 < n ? T[v >> 6 & 63] : '=';
    o += i + 2 < n ? T[v & 63] : '=';
  }
  return o;
}

static WiFiServer wsServer(WS_PORT);
static WsClient wsc[WS_MAX];

static void wsSendText(WsClient& k, const char* p, size_t n) {
  uint8_t hdr[4];
  size_t h = 0;
  hdr[h++] = 0x81;                                   // FIN + text
  if (n < 126) hdr[h++] = (uint8_t)n;
  else { hdr[h++] = 126; hdr[h++] = (uint8_t)(n >> 8 & 0xFF); hdr[h++] = (uint8_t)n; }
  if (k.c.write(hdr, h) != h || k.c.write((const uint8_t*)p, n) != n) { k.c.stop(); k.open = false; }
}

static void wsService() {
  static bool started = false;
  if (WiFi.status() != WL_CONNECTED) return;
  if (!started) { wsServer.begin(); wsServer.setNoDelay(true); started = true; }

  // шинэ холболт
  WiFiClient nc = wsServer.available();
  if (nc) {
    int slot = -1;
    for (int i = 0; i < WS_MAX; i++) if (!wsc[i].c.connected()) { slot = i; break; }
    if (slot < 0) nc.stop();
    else { wsc[slot].c = nc; wsc[slot].c.setNoDelay(true); wsc[slot].open = false; wsc[slot].since = millis(); wsc[slot].req = ""; }
  }

  for (int i = 0; i < WS_MAX; i++) {
    WsClient& k = wsc[i];
    if (!k.c.connected()) { k.open = false; continue; }
    if (!k.open) {                                   // HTTP → WebSocket handshake
      while (k.c.available() && k.req.length() < 1024) k.req += (char)k.c.read();
      int end = k.req.indexOf("\r\n\r\n");
      if (end < 0) { if (millis() - k.since > 2000) k.c.stop(); continue; }
      int p = k.req.indexOf("Sec-WebSocket-Key" ":");
      if (p < 0) { k.c.stop(); continue; }
      p += 18;
      int q = k.req.indexOf('\r', p);
      String key = k.req.substring(p, q);
      key.trim();
      key += "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
      uint8_t dig[20];
      sha1digest((const uint8_t*)key.c_str(), key.length(), dig);
      String resp = "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept" ": ";
      resp += b64enc(dig, 20);
      resp += "\r\n\r\n";
      k.c.print(resp);
      k.open = true;
      k.req = "";
      Serial.printf("[WS] веб холбогдлоо (%s)\n", k.c.remoteIP().toString().c_str());
    } else {                                         // хөтчөөс ирэх (close/ping) фреймүүд
      while (k.c.available()) {
        int b = k.c.read();
        if ((b & 0x0F) == 0x08 && (b & 0x80)) { k.c.stop(); k.open = false; break; }
      }
    }
  }

  // буферт байгаа хэмжилтүүдийг нэг фреймд (JSON массив) бүх холбогдсон хөтөч рүү
  Sample out[WS_RING];
  uint16_t n;
  portENTER_CRITICAL(&ringMux);
  n = wsCount;
  uint16_t tail = (wsHead + WS_RING - wsCount) % WS_RING;
  for (uint16_t i = 0; i < n; i++) out[i] = wsRing[(tail + i) % WS_RING];
  wsCount = 0;
  portEXIT_CRITICAL(&ringMux);
  if (n == 0) return;
  bool any = false;
  for (int i = 0; i < WS_MAX; i++) any |= wsc[i].open;
  if (!any) return;
  if (n > 10) { memmove(out, out + (n - 10), 10 * sizeof(Sample)); n = 10; }   // хоцорвол зөвхөн сүүлийн 10-ыг
  char buf[1024];
  size_t len = 0;
  buf[len++] = '[';
  for (uint16_t i = 0; i < n; i++) {
    const Sample& s = out[i];
    len += snprintf(buf + len, sizeof(buf) - len, "%s{\"t\":%lu,\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,\"gx\":%.2f,\"gy\":%.2f,\"gz\":%.2f}",
                    i ? "," : "", (unsigned long)s.t, s.ax, s.ay, s.az, s.gx, s.gy, s.gz);
    if (len > sizeof(buf) - 120) break;
  }
  buf[len++] = ']';
  for (int i = 0; i < WS_MAX; i++) if (wsc[i].open) wsSendText(wsc[i], buf, len);
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== MotionCare ESP32-C3 ===");

  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);
  i2cMutex = xSemaphoreCreateMutex();

  oledOk = oledInit();
  if (oledOk) {
    fbClear();
    fbText(4, 18, "MotionCare", 2);
    fbText(22, 46, "starting...", 1);
    oledFlush();
  } else {
    Serial.println("[OLED] олдсонгүй (0x3C) — холболтоо шалга");
  }

  mpuOk = mpuInit();

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[WiFi] \"%s\" руу холбогдож байна...\n", WIFI_SSID);

  xTaskCreate(sensorTask, "sensor", 4096, nullptr, 5, nullptr);
  xTaskCreate(netTask, "net", 8192, nullptr, 2, nullptr);
}

void loop() {
  static uint32_t lastDraw = 0, lastLog = 0;
  static bool wasConnected = false;

  ensureWifi();
  bool connected = WiFi.status() == WL_CONNECTED;
  if (connected && !wasConnected) {
    Serial.printf("[WiFi] холбогдлоо: IP %s → сервер http://%s:%d, веб шууд ws://%s:%u\n",
                  WiFi.localIP().toString().c_str(), SERVER_HOST, SERVER_PORT,
                  WiFi.localIP().toString().c_str(), (unsigned)WS_PORT);
  }
  wasConnected = connected;

  uint32_t now = millis();
  wsService();                                                              // веб рүү шууд (~50 Hz)
  if (now - lastDraw >= 100) { lastDraw = now; drawScreen(); }             // OLED 10 удаа/сек
  if (now - lastLog >= 5000) {
    lastLog = now;
    Serial.printf("[STAT] buffer=%u dropped=%lu label=%s %d%% fails=%lu\n",
                  (unsigned)ringCount, (unsigned long)droppedSamples, lastLabel, lastConfidence,
                  (unsigned long)postFailures);
  }
  delay(2);
}
