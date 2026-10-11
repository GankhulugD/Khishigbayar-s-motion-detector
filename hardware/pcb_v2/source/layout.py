"""MotionCare v2 — ESP32-C3 SuperMini + OLED + MPU9250 + TP4056 модуль (2 давхарга, THT).
Координат: мм, зүүн дээд булан (0,0), y доошоо.  Дамжуулагч: дохио 60 mil, тэжээл 80 mil."""

MIL = 0.0254
W_SIG = 60 * MIL      # 1.524 мм
W_PWR = 80 * MIL      # 2.032 мм
BOARD = (58.0, 49.0)
CLEARANCE = 0.30
P = 2.54

parts = {}
def add(ref, pads, silk=None, label=None, value="", body=None):
    parts[ref] = {"pads": pads, "silk": silk or [], "label": label, "value": value, "body": body}

# U1 ESP32-C3 SuperMini — USB дээш, чип талаас харахад (хэрэглэгч баталгаажуулсан):
#   баруун багана: 5V, GND, 3V3, IO4, IO3, IO2, IO1, IO0   зүүн багана: IO5 … IO21
UL, UR, UY = 30.88, 46.12, 2.67
left = ["IO5", "IO6", "IO7", "IO8", "IO9", "IO10", "IO20", "IO21"]
right = ["5V", "GND", "3V3", "IO4", "IO3", "IO2", "IO1", "IO0"]
lnet = {"IO6": "SDA", "IO7": "SCL"}
rnet = {"5V": "VBAT", "GND": "GND", "3V3": "3V3"}
add("U1", [(n, UL, UY + i * P, 1.8, 1.0, lnet.get(n)) for i, n in enumerate(left)] +
          [(n, UR, UY + i * P, 1.8, 1.0, rnet.get(n)) for i, n in enumerate(right)],
    silk=[("rect", 29.5, 0.3, 47.5, 22.8)], label=(38.5, 14.5), value="ESP32-C3\nSuperMini",
    body=(29.5, 0.3, 47.5, 22.8))

# J2 OLED SSD1306 0.96" — дэлгэц талаас: GND VCC SCL SDA, толгой дээд ирмэгт, дэлгэц доошоо
ox = [10.64, 13.18, 15.72, 18.26]
add("J2", [(n, x, 2.4, 1.8, 1.0, net) for n, x, net in
           zip(["GND", "VCC", "SCL", "SDA"], ox, ["GND", "3V3", "SCL", "SDA"])],
    silk=[("rect", 9.24, 1.0, 19.66, 3.8)], label=(14.45, 20.5), value="OLED 0.96\"",
    body=(0.8, 0.8, 28.1, 28.6))

# J3 MPU9250 (нил ягаан, 10 pin) — бичээс талаас: VCC GND SCL SDA EDA ECL AD0 INT NCS FSYNC,
#   толгой доод ирмэгт, модулийн бие дээшээ
mnames = ["VCC", "GND", "SCL", "SDA", "EDA", "ECL", "AD0", "INT", "NCS", "FSYNC"]
mnet = {"VCC": "3V3", "GND": "GND", "SCL": "SCL", "SDA": "SDA"}
add("J3", [(n, 2.37 + i * P, 47.3, 1.8, 1.0, mnet.get(n)) for i, n in enumerate(mnames)],
    silk=[("rect", 0.97, 45.9, 26.63, 48.7)], label=(13.8, 38.0), value="MPU9250",
    body=(0.8, 32.3, 26.8, 48.3))

# J1 TP4056 модулийн гаралт → платан (2 богино утас)
add("J1", [("OUT-", 30.5, 27.0, 1.8, 1.0, "GND"), ("OUT+", 33.04, 27.0, 1.8, 1.0, "VBAT")],
    silk=[], label=None, value="")

# C1 470µF электролит, 8 мм, 3.5 мм алхам
add("C1", [("+", 55.3, 13.0, 1.8, 0.9, "VBAT"), ("-", 51.8, 13.0, 1.8, 0.9, "GND")],
    silk=[("circle", 53.55, 13.0, 4.0)], label=(53.55, 19.3), value="470µF")

# TP4056 модуль (наах талбай, USB-C баруун ирмэгт)
TP_AREA = (28.8, 30.8, 56.8, 47.8)
MOUNT = [(2.5, 2.5), (27.7, 29.9)]   # M2, NPTH 2.2 мм
MOUNT_D = 2.2

T, B = "F", "B"
traces = [
    # I2C → OLED (дээд)
    ("SDA", T, W_SIG, [(30.88, 5.21), (18.26, 5.21), (18.26, 2.4)]),
    ("SCL", T, W_SIG, [(30.88, 7.75), (15.72, 7.75), (15.72, 2.4)]),
    # I2C + 3V3: OLED-оос MPU9250 руу (доод)
    ("3V3", B, W_PWR, [(13.18, 2.4), (13.18, 9.0), (2.37, 9.0), (2.37, 47.3)]),
    ("SCL", B, W_SIG, [(15.72, 2.4), (15.72, 12.0), (7.45, 12.0), (7.45, 47.3)]),
    ("SDA", B, W_SIG, [(18.26, 2.4), (18.26, 15.0), (9.99, 15.0), (9.99, 47.3)]),
    # 3V3: ESP → OLED (дээд)
    ("3V3", T, W_PWR, [(46.12, 7.75), (43.0, 7.75), (43.0, 23.0), (13.18, 23.0), (13.18, 2.4)]),
    # GND (дээд): OLED → MPU, TP4056 OUT-
    ("GND", T, W_PWR, [(10.64, 2.4), (10.64, 25.8), (30.5, 25.8), (30.5, 27.0)]),
    ("GND", T, W_PWR, [(10.64, 25.8), (4.91, 25.8), (4.91, 47.3)]),
    # GND (доод): TP4056 OUT- → ESP GND
    ("GND", B, W_PWR, [(30.5, 27.0), (30.5, 24.3), (37.0, 24.3), (37.0, 5.21), (46.12, 5.21)]),
    # GND (дээд): ESP GND → C1-
    ("GND", T, W_PWR, [(46.12, 5.21), (49.0, 5.21), (49.0, 13.0), (51.8, 13.0)]),
    # VBAT (дээд): TP4056 OUT+ → C1+ → ESP 5V
    ("VBAT", T, W_PWR, [(33.04, 27.0), (55.3, 27.0), (55.3, 2.67), (46.12, 2.67)]),
]
