# MotionCare v2 — Холболтын хүснэгт

ESP32-C3 SuperMini · OLED SSD1306 · MPU9250 (10 pin) · TP4056 модуль · C1 470µF

## Сүлжээ (net) бүрээр

| Сүлжээ | Хүчдэл | Холбогдох цэгүүд | Утасны өргөн |
|---|---|---|---|
| VBAT | 3.0–4.2V | TP4056 **OUT+** → J1 OUT+ → C1 «+» → ESP32-C3 **5V** | 80 mil |
| GND | 0V | TP4056 **OUT−** → J1 OUT− → C1 «−» → ESP32-C3 **GND** → OLED GND → MPU9250 GND | 80 mil |
| 3V3 | 3.3V | ESP32-C3 **3V3** → OLED VCC → MPU9250 VCC | 80 mil |
| SDA | I2C | ESP32-C3 **GPIO6** → OLED SDA → MPU9250 SDA | 60 mil |
| SCL | I2C | ESP32-C3 **GPIO7** → OLED SCL → MPU9250 SCL | 60 mil |

Платан дээр замгүй (утсаар): 18650 батерей «+» → TP4056 **B+**, «−» → TP4056 **B−**.

## Эд анги тус бүрээр

| Ref | Эд анги | Зүү → холболт |
|---|---|---|
| U1 | ESP32-C3 SuperMini | 5V ← VBAT · GND · 3V3 → OLED, MPU · GPIO6 = SDA · GPIO7 = SCL · бусад зүү холбогдохгүй |
| J1 | TP4056-ийн гаралтын 2 дэвсгэр | OUT− = GND · OUT+ = VBAT |
| C1 | 470µF электролит (≥10V, Ø8 мм) | «+» = VBAT · «−» = GND |
| J2 | OLED SSD1306 0.96" | GND · VCC = 3V3 · SCL = GPIO7 · SDA = GPIO6 |
| J3 | MPU9250 (нил ягаан, 10 pin) | VCC = 3V3 · GND · SCL = GPIO7 · SDA = GPIO6 · EDA, ECL, AD0, INT, NCS, FSYNC холбогдохгүй |
| — | TP4056 модуль (наана) | B+/B− ← 18650 · OUT+/OUT− → J1 · USB-C-ээр цэнэглэнэ |

## Анхаарах зүйлс

- **B− ба OUT− нь нэг цэг биш.** Хамгаалалттай TP4056 модульд тэдгээрийн хооронд хамгаалалтын транзистор байдаг тул B−-г GND-д бүү холбо.
- Батерей ESP32-C3-ийн **5V** зүүгээр орно. **3V3 зүүнд шууд бүү холбо.**
- I2C хаяг: OLED 0x3C, MPU9250 0x68 (AD0 модуль дээрээ GND рүү татагдсан). Firmware: `Wire.begin(6, 7)`.
- MPU9250-ийн VCC нь модуль доторх тогтворжуулагчаар ордог тул 3.3V-оор тэжээхэд ажиллана.
