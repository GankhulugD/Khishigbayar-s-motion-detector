"""MotionCare v4 (ESP32-S3-Zero) — 2 давхар (stack) PCB, бугуйн цагны хэмжээ.
Самбар бүр 2 давхаргатай (нийт 4 давхарга зэс). Координат: мм, дээрээс харсан (top view),
зүүн дээд булан (0,0), y доошоо. Доод талд суурилуулсан модулийн зүүг толин тусгалаар (x) эргүүлнэ."""

MIL = 0.0254
W_SIG, W_PWR = 60 * MIL, 80 * MIL
BOARD = (36.0, 34.0)
CLEARANCE = 0.30
P = 2.54
VIA_PAD, VIA_DRILL = 1.4, 0.7
MOUNT = [(1.6, 1.6), (34.4, 1.6)]
MOUNT_D = 2.2
NET_W = {"VBAT": W_PWR, "VSYS": W_PWR, "GND": W_PWR, "3V3": W_PWR, "SDA": W_SIG, "SCL": W_SIG}

# ------------------------------------------------------------ модулиуд (өөрийн нүүрэн талаас харсан)
# (нэр, u, v) — u баруун тийш, v доош; модулийн хүрээ (fw, fh)
# Waveshare ESP32-S3-Zero, 18 × 23.5 мм, дээрээс (элементийн талаас) харсан, USB-C дээшээ.
# Зүүн эгнээ x=1.38, баруун эгнээ x=16.62 (хоорондоо 15.24), эхний зүү дээд ирмэгээс 1.59, алхам 2.54.
# Эх сурвалж: Waveshare ESP32-S3-Zero pinout + хэмжээсийн зураг (docs.waveshare.com/ESP32-S3-Zero)
S3ZERO = (18.0, 23.5, [(n, 1.38, 1.59 + i * P) for i, n in enumerate(
    ["5V", "GND", "3V3", "GP1", "GP2", "GP3", "GP4", "GP5", "GP6"])] +
    [(n, 16.62, 1.59 + i * P) for i, n in enumerate(["TX", "RX", "GP13", "GP12", "GP11", "GP10", "GP9", "GP8", "GP7"])])
# SS34 Шоттки диод, SMA (DO-214AC) корпус: дэвсгэр 2.5 × 1.7 мм, төв хоорондын зай 4.0 мм
SMA_PAD = (2.5, 1.7)
OLED = (27.3, 27.8, [(n, 9.84 + i * P, 1.5) for i, n in enumerate(["GND", "VCC", "SCL", "SDA"])])
MPU9250 = (26.0, 16.0, [(n, 1.57 + i * P, 14.7) for i, n in enumerate(
    ["VCC", "GND", "SCL", "SDA", "EDA", "ECL", "AD0", "INT", "NCS", "FSYNC"])])


def place(module, side, rot, X0, Y0):
    """Модулийн зүүг самбарын координат руу. side='bottom' бол толин тусгал (x),
    rot ∈ {0,180} самбарын хавтгайд эргүүлэлт. Буцаана: [(name,x,y)], (x0,y0,x1,y1)"""
    fw, fh, pins = module
    out = []
    for n, u, v in pins:
        if side == "bottom":
            u = fw - u
        if rot == 180:
            u, v = fw - u, fh - v
        out.append((n, X0 + u, Y0 + v))
    return out, (X0, Y0, X0 + fw, Y0 + fh)


def pads_of(ref, placed, netmap, d=1.8, drill=1.0):
    return [(n, x, y, d, drill, netmap.get(n)) for n, x, y in placed]


# J4 самбар хоорондын холбогч (A доод тал: эрэгтэй, B дээд тал: эм) — 2 самбар дээр ижил байрлал
J4_NAMES = ["VBAT", "SDA", "3V3", "GND", "SCL"]
J4_XY = [(21.0 + i * P, 5.6) for i in range(5)]
J4 = [(n, x, y, 1.8, 1.0, n) for n, (x, y) in zip(J4_NAMES, J4_XY)]

# ============================================================ Самбар A (дэлгэц + ESP32-S3-Zero + TP4056)
# Дээд тал: OLED (зүү дээшээ, текст босоо → firmware OLED_ROTATE_180 = 0)
# Доод тал: ESP32-S3-Zero (180° эргүүлсэн, USB-C доод ирмэгт), TP4056 (зүүн талд, USB-C доод ирмэгт),
#           D1, J4 (дээд зурвас)
A = {"name": "A", "parts": {}, "areas": [], "text": [], "keepouts": []}
oled_p, oled_box = place(OLED, "top", 0, 0.5, 5.7)
A["parts"]["J2"] = {"side": "top", "pads": pads_of("J2", oled_p, {"GND": "GND", "VCC": "3V3", "SCL": "SCL", "SDA": "SDA"}),
                    "box": oled_box, "label": "J2 OLED", "body_label": "OLED (дээд тал)"}
U1_X0, U1_Y0 = 17.6, 10.3
esp_p, esp_box = place(S3ZERO, "bottom", 180, U1_X0, U1_Y0)
A["parts"]["U1"] = {"side": "bottom", "pads": pads_of("U1", esp_p, {"5V": "VSYS", "GND": "GND", "3V3": "3V3", "GP6": "SDA", "GP7": "SCL"}),
                    "box": esp_box, "label": "U1 ESP32-S3-Zero", "body_label": "ESP32-S3-Zero\n(доод тал, USB-C ↓)"}
A["parts"]["J1"] = {"side": "bottom", "pads": [("OUT-", 4.8, 2.6, 1.8, 1.0, "GND"), ("OUT+", 7.34, 2.6, 1.8, 1.0, "VBAT")],
                    "box": None, "label": None}
# D1: батерей (OUT+) → ESP32-S3-Zero 5V. USB-C залгахад 5V батерей руу буцаж орохоос хамгаална.
# drill = 0 → гадаргуун (SMD) дэвсгэр, зөвхөн тухайн талын зэс дээр.
A["parts"]["D1"] = {"side": "bottom", "pads": [("A", 10.4, 2.6, SMA_PAD, 0, "VBAT"), ("K", 14.4, 2.6, SMA_PAD, 0, "VSYS")],
                    "box": (11.2, 1.3, 13.6, 3.9), "label": "D1 SS34"}
A["parts"]["J4"] = {"side": "bottom", "pads": J4, "box": None, "label": "J4 → B"}
TP_BOX = (0.3, 4.6, 17.3, 33.8)
A["areas"].append(("bottom", TP_BOX, "TP4056 (наана)\nUSB-C ↓"))
# TP4056 модулийг самбарт шууд наадаг тул түүний доор доод давхаргын зэс хориглоно.
# ESP32-S3-Zero нь 2.54 мм-ийн pin header-ийн хуванцар (≈2.5 мм) дээр өргөгдөж суух тул доор нь зэс зөвшөөрнө (маскаар бүрхэгдсэн).
A["keepouts"] += [(1, TP_BOX)]
A["spec"] = {
    "VBAT": {"J1.OUT+", "D1.A", "J4.VBAT"},
    "VSYS": {"D1.K", "U1.5V"},
    "GND": {"J1.OUT-", "U1.GND", "J2.GND", "J4.GND"},
    "3V3": {"U1.3V3", "J2.VCC", "J4.3V3"},
    "SDA": {"U1.GP6", "J2.SDA", "J4.SDA"},
    "SCL": {"U1.GP7", "J2.SCL", "J4.SCL"},
}

# ============================================================ Самбар B (MPU9250 + C1)
B = {"name": "B", "parts": {}, "areas": [], "text": [], "keepouts": []}
B["parts"]["J4"] = {"side": "top", "pads": J4, "box": None, "label": "J4 → A"}
mpu_p, mpu_box = place(MPU9250, "bottom", 0, 5.0, 17.0)
B["parts"]["J3"] = {"side": "bottom", "pads": pads_of("J3", mpu_p, {"VCC": "3V3", "GND": "GND", "SCL": "SCL", "SDA": "SDA"}),
                    "box": mpu_box, "label": "J3 MPU9250", "body_label": "MPU9250 (доод тал)"}
# C1 470µF Ø6.3 мм, хэвтүүлж суулгана (2.5 мм алхам)
B["parts"]["C1"] = {"side": "bottom", "pads": [("+", 4.0, 7.5, 1.8, 0.9, "VBAT"), ("-", 4.0, 10.0, 1.8, 0.9, "GND")],
                    "box": (5.3, 5.6, 16.3, 11.9), "label": "C1 470µF", "body_label": "C1 (хэвтээ)"}
B["spec"] = {
    "VBAT": {"J4.VBAT", "C1.+"},
    "GND": {"J4.GND", "C1.-", "J3.GND"},
    "3V3": {"J4.3V3", "J3.VCC"},
    "SDA": {"J4.SDA", "J3.SDA"},
    "SCL": {"J4.SCL", "J3.SCL"},
}
BOARDS = [A, B]
