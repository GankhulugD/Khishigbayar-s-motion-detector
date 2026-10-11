"""Gerber (RS-274X) + Excellon drill + PNG preview үүсгэх."""
import math, os, zipfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
from layout import parts, traces, BOARD, MOUNT, MOUNT_D, TP_AREA

W, H = BOARD
OUT = "out"
os.makedirs(OUT, exist_ok=True)
FONT = FontProperties(family="DejaVu Sans", weight="bold")

# ---------------------------------------------------------------- silkscreen
def text_poly(s, x, y, size, anchor="center"):
    """Текстийг shapely polygon болгох (y доошоо координатад)."""
    polys = []
    lines = s.split("\n")
    for li, line in enumerate(lines):
        tp = TextPath((0, 0), line, size=size, prop=FONT)
        bb = tp.get_extents()
        dx = {"center": -bb.width / 2 - bb.x0, "left": -bb.x0, "right": -bb.x1}[anchor]
        dy = (li - (len(lines) - 1) / 2) * size * 1.25
        rings = tp.to_polygons(closed_only=True)
        shapes = []
        for r in rings:
            if len(r) < 3:
                continue
            pts = [(x + px + dx, y - (py - size * 0.36) + dy) for px, py in r]
            shapes.append(Polygon(pts).buffer(0))
        # even-odd: том хүрээнээс доторхыг хасах
        shapes.sort(key=lambda p: -p.area)
        glyph = None
        for sh in shapes:
            if glyph is None:
                glyph = sh
            elif glyph.contains(sh.representative_point()) and glyph.intersects(sh):
                glyph = glyph.difference(sh) if glyph.contains(sh) else glyph.union(sh)
            else:
                glyph = glyph.union(sh)
        if glyph is not None:
            polys.append(glyph)
    return unary_union(polys) if polys else None

silk_lines = []   # list of polylines
silk_text = []    # shapely geometries
def circle_pts(cx, cy, r, a0=0, a1=360, n=72):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

for ref, p in parts.items():
    for s in p["silk"]:
        if s[0] == "rect":
            _, x0, y0, x1, y1 = s
            silk_lines.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
        elif s[0] == "circle":
            silk_lines.append(circle_pts(s[1], s[2], s[3]))
        elif s[0] == "arc":  # TO-92: доод талдаа хавтгай
            cx, cy, r = s[1:]
            # хавтгай тал нь дээшээ (C-B-E зүүнээс баруун тийш)
            silk_lines.append(circle_pts(cx, cy, r, 20, 160, 60))
            silk_lines.append([(cx - r * 0.94, cy - 1.0), (cx + r * 0.94, cy - 1.0)])
    if p["label"]:
        lx, ly = p["label"]
        t = f"{ref} {p['value']}" if "\n" not in p["value"] else f"{ref}\n{p['value']}"
        silk_text.append(text_poly(t, lx, ly, 1.25))

# Зүүний нэрс
for name, x, y, *_ in parts["U1"]["pads"]:
    silk_text.append(text_poly(name, x + 1.35, y, 0.8, "left") if x < 40 else text_poly(name, x - 1.35, y, 0.8, "right"))
for name, x, y, *_ in parts["J2"]["pads"]:
    silk_text.append(text_poly(name, x, y + 2.1, 0.7))
for name, x, y, *_ in parts["J3"]["pads"]:
    silk_text.append(text_poly(name, x, y - 2.1, 0.62))
for name, x, y, *_ in parts["J1"]["pads"]:
    silk_text.append(text_poly(name, x, y + 2.1, 0.75))
silk_text.append(text_poly("+", 55.3, 10.4, 1.1))
silk_text.append(text_poly("USB ↑", 38.5, 1.4, 0.85))
# TP4056 модулийн наах талбай
x0, y0, x1, y1 = TP_AREA
silk_lines.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
silk_text.append(text_poly("TP4056 модуль (наана)", (x0 + x1) / 2, 36.2, 1.1))
silk_text.append(text_poly("OUT+/OUT- → J1 утсаар", (x0 + x1) / 2, 39.4, 0.85))
silk_text.append(text_poly("B+/B- → 18650 батерей", (x0 + x1) / 2, 41.6, 0.85))
silk_text.append(text_poly("USB-C →", 50.5, 45.0, 0.85))

silk_text = [g for g in silk_text if g is not None]

# ---------------------------------------------------------------- Gerber
def fmt(v):
    return f"{int(round(v * 1e6))}"

def gy(y):  # y доошоо → Gerber y дээшээ
    return H - y

class Gerber:
    def __init__(self, func):
        self.lines = ["%FSLAX46Y46*%", "%MOMM*%", f"%TF.FileFunction,{func}*%", "%LPD*%"]
        self.ap = {}
    def aperture(self, d):
        key = round(d, 4)
        if key not in self.ap:
            code = 10 + len(self.ap)
            self.ap[key] = code
            self.lines.insert(3, f"%ADD{code}C,{key:.4f}*%")
        return self.ap[key]
    def use(self, d):
        self.lines.append(f"D{self.aperture(d)}*")
    def flash(self, x, y, d):
        self.use(d); self.lines.append(f"X{fmt(x)}Y{fmt(gy(y))}D03*")
    def path(self, pts, d):
        self.use(d)
        x, y = pts[0]; self.lines.append(f"X{fmt(x)}Y{fmt(gy(y))}D02*")
        for x, y in pts[1:]:
            self.lines.append(f"X{fmt(x)}Y{fmt(gy(y))}D01*")
    def region(self, ring, clear=False):
        if clear: self.lines.append("%LPC*%")
        self.lines.append("G36*")
        x, y = ring[0]; self.lines.append(f"X{fmt(x)}Y{fmt(gy(y))}D02*")
        for x, y in ring[1:]:
            self.lines.append(f"X{fmt(x)}Y{fmt(gy(y))}D01*")
        self.lines.append("G37*")
        if clear: self.lines.append("%LPD*%")
    def save(self, name):
        self.lines.append("M02*")
        open(os.path.join(OUT, name), "w").write("\n".join(self.lines) + "\n")

def all_pads():
    for ref, p in parts.items():
        for pad in p["pads"]:
            yield ref, pad

for layer, ext, func in (("F", "GTL", "Copper,L1,Top"), ("B", "GBL", "Copper,L2,Bot")):
    g = Gerber(func)
    g.lines.append("G01*")
    for ref, (name, x, y, d, drill, net) in all_pads():
        g.flash(x, y, d)
    for net, ly, w, pts in traces:
        if ly == layer:
            g.path(pts, w)
    g.save(f"MotionCare.{ext}")

for ext, func in (("GTS", "Soldermask,Top"), ("GBS", "Soldermask,Bot")):
    g = Gerber(func)
    for ref, (name, x, y, d, drill, net) in all_pads():
        g.flash(x, y, d + 0.1)
    g.save(f"MotionCare.{ext}")

g = Gerber("Legend,Top"); g.lines.append("G01*")
for pl in silk_lines:
    g.path(pl, 0.15)
def emit_poly(poly):
    polys = poly.geoms if isinstance(poly, MultiPolygon) else [poly]
    for pg in polys:
        g.region(list(pg.exterior.coords))
        for hole in pg.interiors:
            g.region(list(hole.coords), clear=True)
for t in silk_text:
    emit_poly(t)
g.save("MotionCare.GTO")

g = Gerber("Profile,NP"); g.lines.append("G01*")
g.path([(0, 0), (W, 0), (W, H), (0, H), (0, 0)], 0.1)
g.save("MotionCare.GKO")

# Excellon drill (PTH + NPTH)
def drill_file(name, holes, plated):
    tools = sorted({round(d, 2) for _, _, d in holes})
    out = ["M48", "METRIC,TZ", f";TYPE={'PLATED' if plated else 'NON_PLATED'}"]
    for i, d in enumerate(tools, 1):
        out.append(f"T{i}C{d:.3f}")
    out.append("%")
    out.append("G90"); out.append("G05")
    for i, d in enumerate(tools, 1):
        out.append(f"T{i}")
        for x, y, hd in holes:
            if round(hd, 2) == d:
                out.append(f"X{x:.3f}Y{gy(y):.3f}")
    out.append("M30")
    open(os.path.join(OUT, name), "w").write("\n".join(out) + "\n")

drill_file("MotionCare-PTH.DRL", [(x, y, dr) for _, (n, x, y, d, dr, net) in all_pads()], True)
drill_file("MotionCare-NPTH.DRL", [(x, y, MOUNT_D) for x, y in MOUNT], False)

with zipfile.ZipFile(os.path.join(OUT, "MotionCare_gerber.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(OUT)):
        if f.startswith("MotionCare") and not f.endswith(".zip") and not f.endswith(".png"):
            z.write(os.path.join(OUT, f), f)

# ---------------------------------------------------------------- PNG preview
NET_COL = {"VBAT": "#e03131", "GND": "#212529", "3V3": "#f08c00", "SDA": "#1971c2", "SCL": "#0c8599",
           "BUZ_B": "#6741d9", "BUZ_Q": "#6741d9", "BUZ_N": "#c2255c"}

def draw(ax, show, title):
    ax.add_patch(plt.Rectangle((0, 0), W, H, fc="#1f5e3a", ec="#c9d6cd", lw=1.5, zorder=0))
    for net, ly, w, pts in traces:
        if ly not in show:
            continue
        xs, ys = zip(*pts)
        col = "#d9480f" if ly == "F" else "#1c7ed6"
        if show == "FB":
            alpha = 1.0 if ly == "F" else 0.75
        else:
            alpha = 1.0
        ax.plot(xs, ys, color=col, lw=w * ppm, solid_capstyle="round", solid_joinstyle="round", alpha=alpha, zorder=2 if ly == "F" else 1)
    for ref, (name, x, y, d, dr, net) in all_pads():
        ax.add_patch(plt.Circle((x, y), d / 2, fc="#d4a017", ec="none", zorder=3))
        ax.add_patch(plt.Circle((x, y), dr / 2, fc="#111", ec="none", zorder=4))
    for x, y in MOUNT:
        ax.add_patch(plt.Circle((x, y), MOUNT_D / 2, fc="#111", ec="#ddd", lw=0.8, zorder=4))
    if show == "FB":
        for ref, p in parts.items():
            if p.get("body") and ref in ("J2", "J3"):
                bx0, by0, bx1, by1 = p["body"]
                ax.add_patch(plt.Rectangle((bx0, by0), bx1 - bx0, by1 - by0, fc="none", ec="#ffe066", lw=1.0, ls=(0, (4, 3)), zorder=7))
                ax.text(bx0 + 0.6, by1 - 0.6 if ref == "J2" else by0 + 1.6, ("OLED модулийн бие" if ref == "J2" else "MPU9250 модулийн бие"),
                        color="#ffe066", fontsize=7, zorder=7)
    for pl in silk_lines:
        xs, ys = zip(*pl); ax.plot(xs, ys, color="white", lw=0.15 * ppm, zorder=5)
    for t in silk_text:
        polys = t.geoms if isinstance(t, MultiPolygon) else [t]
        for pg in polys:
            xs, ys = pg.exterior.xy
            ax.fill(xs, ys, color="white", zorder=6, lw=0)
            for h in pg.interiors:
                xs, ys = h.xy; ax.fill(xs, ys, color="#1f5e3a", zorder=6, lw=0)
    ax.set_xlim(-2, W + 2); ax.set_ylim(H + 2, -2); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=13, pad=10)

DPI = 200
fig_w = 9
ppm = fig_w * 72 / (W + 4)  # 1 мм = ppm pt
for show, name, title in (("FB", "pcb_combined.png", "MotionCare v2 — PCB (дээд: улбар шар, доод: цэнхэр)"),
                          ("F", "pcb_top.png", "Дээд давхарга (F.Cu)"),
                          ("B", "pcb_bottom.png", "Доод давхарга (B.Cu) — дээрээс харсан")):
    fig, ax = plt.subplots(figsize=(fig_w, fig_w * (H + 4) / (W + 4) + 0.5), dpi=DPI)
    draw(ax, show, title)
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor="white")
    plt.close(fig)
print("exported:", sorted(os.listdir(OUT)))
