"""MotionCare v3 — 2 давхар (stack) PCB, бугуйн цагны хэмжээ.
Самбар бүр 2 давхаргатай (нийт 4 давхарга зэс). Координат: мм, дээрээс харсан (top view),
зүүн дээд булан (0,0), y доошоо. Доод талд суурилуулсан модулийн зүүг толин тусгалаар (x) эргүүлнэ."""

MIL = 0.0254
W_SIG, W_PWR = 60 * MIL, 80 * MIL
BOARD = (36.0, 34.0)
CLEARANCE = 0.30
P = 2.54
VIA_PAD, VIA_DRILL = 1.4, 0.7
MOUNT = [(1.6, 1.6), (34.4, 32.4)]
MOUNT_D = 2.2
NET_W = {"VBAT": W_PWR, "GND": W_PWR, "3V3": W_PWR, "SDA": W_SIG, "SCL": W_SIG}

# ------------------------------------------------------------ модулиуд (өөрийн нүүрэн талаас харсан)
# (нэр, u, v) — u баруун тийш, v доош; модулийн хүрээ (fw, fh)
SUPERMINI = (18.0, 22.52, [(n, 1.38, 2.37 + i * P) for i, n in enumerate(
    ["IO5", "IO6", "IO7", "IO8", "IO9", "IO10", "IO20", "IO21"])] +
    [(n, 16.62, 2.37 + i * P) for i, n in enumerate(["5V", "GND", "3V3", "IO4", "IO3", "IO2", "IO1", "IO0"])])
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
J4_NAMES = ["SDA", "SCL", "GND", "3V3", "VBAT"]
J4_XY = [(22.0 + i * P, 30.0) for i in range(5)]
J4 = [(n, x, y, 1.8, 1.0, n) for n, (x, y) in zip(J4_NAMES, J4_XY)]

# ============================================================ Самбар A (дэлгэц + ESP32 + TP4056)
A = {"name": "A", "parts": {}, "areas": [], "text": []}
oled_p, oled_box = place(OLED, "top", 180, 0.5, 5.7)
A["parts"]["J2"] = {"side": "top", "pads": pads_of("J2", oled_p, {"GND": "GND", "VCC": "3V3", "SCL": "SCL", "SDA": "SDA"}),
                    "box": oled_box, "label": "J2 OLED", "body_label": "OLED (дээд тал)"}
esp_p, esp_box = place(SUPERMINI, "bottom", 0, 17.5, 0.3)
A["parts"]["U1"] = {"side": "bottom", "pads": pads_of("U1", esp_p, {"5V": "VBAT", "GND": "GND", "3V3": "3V3", "IO6": "SDA", "IO7": "SCL"}),
                    "box": esp_box, "label": "U1 ESP32-C3", "body_label": "ESP32-C3 SuperMini (доод тал, USB ↑)"}
A["parts"]["J1"] = {"side": "bottom", "pads": [("OUT-", 8.0, 2.4, 1.8, 1.0, "GND"), ("OUT+", 10.54, 2.4, 1.8, 1.0, "VBAT")],
                    "box": None, "label": None}
A["parts"]["J4"] = {"side": "bottom", "pads": J4, "box": None, "label": "J4 → B"}
A["areas"].append(("bottom", (0.2, 6.2, 17.2, 34.2), "TP4056 (наана)\nUSB-C ↓"))
A["spec"] = {
    "VBAT": {"J1.OUT+", "U1.5V", "J4.VBAT"},
    "GND": {"J1.OUT-", "U1.GND", "J2.GND", "J4.GND"},
    "3V3": {"U1.3V3", "J2.VCC", "J4.3V3"},
    "SDA": {"U1.IO6", "J2.SDA", "J4.SDA"},
    "SCL": {"U1.IO7", "J2.SCL", "J4.SCL"},
}

# ============================================================ Самбар B (MPU9250 + C1)
B = {"name": "B", "parts": {}, "areas": [], "text": []}
B["parts"]["J4"] = {"side": "top", "pads": J4, "box": None, "label": "J4 → A"}
mpu_p, mpu_box = place(MPU9250, "bottom", 0, 8.0, 1.0)
B["parts"]["J3"] = {"side": "bottom", "pads": pads_of("J3", mpu_p, {"VCC": "3V3", "GND": "GND", "SCL": "SCL", "SDA": "SDA"}),
                    "box": mpu_box, "label": "J3 MPU9250", "body_label": "MPU9250 (доод тал)"}
# C1 470µF Ø6.3 мм, хэвтүүлж суулгана (2.5 мм алхам)
B["parts"]["C1"] = {"side": "bottom", "pads": [("+", 4.0, 23.5, 1.8, 0.9, "VBAT"), ("-", 4.0, 21.0, 1.8, 0.9, "GND")],
                    "box": (5.3, 19.1, 16.3, 25.4), "label": "C1 470µF", "body_label": "C1 (хэвтээ)"}
B["spec"] = {
    "VBAT": {"J4.VBAT", "C1.+"},
    "GND": {"J4.GND", "C1.-", "J3.GND"},
    "3V3": {"J4.3V3", "J3.VCC"},
    "SDA": {"J4.SDA", "J3.SDA"},
    "SCL": {"J4.SCL", "J3.SCL"},
}
BOARDS = [A, B]
