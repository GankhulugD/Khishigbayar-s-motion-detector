"""Gerber/Drill + PNG preview — 2 самбар (A, B)."""
import os, math, pickle, zipfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from design import BOARDS, BOARD, MOUNT, MOUNT_D, VIA_PAD, VIA_DRILL

W, H = BOARD
FONT = FontProperties(family="DejaVu Sans", weight="bold")
_raw = pickle.load(open("routed.pkl", "rb"))
routed = {k: v[:3] for k, v in _raw.items()}
PADLAYER = {k: v[3] for k, v in _raw.items()}


def on_layer(board, ref, name, dr, layer):
    """THT дэвсгэр хоёр талд, SMD (dr=0) зөвхөн өөрийн талд"""
    return bool(dr) or "FB"[PADLAYER[board][(ref, name)]] == layer


def text_poly(s, x, y, size, anchor="center", mirror=False):
    polys = []
    lines = s.split("\n")
    for li, line in enumerate(lines):
        tp = TextPath((0, 0), line, size=size, prop=FONT)
        bb = tp.get_extents()
        dx = {"center": -bb.width / 2 - bb.x0, "left": -bb.x0, "right": -bb.x1}[anchor]
        dy = (li - (len(lines) - 1) / 2) * size * 1.3
        shapes = [Polygon([(x + px + dx, y - (py - size * 0.36) + dy) for px, py in r]).buffer(0)
                  for r in tp.to_polygons(closed_only=True) if len(r) >= 3]
        shapes.sort(key=lambda p: -p.area)
        glyph = None
        for sh in shapes:
            if glyph is None:
                glyph = sh
            elif glyph.contains(sh):
                glyph = glyph.difference(sh)
            else:
                glyph = glyph.union(sh)
        if glyph is not None:
            polys.append(glyph)
    g = unary_union(polys)
    return affinity.scale(g, xfact=-1, origin=(x, y)) if mirror else g


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def silk_for(spec):
    """{'F': (lines, polys), 'B': (lines, polys)}"""
    S = {"F": ([], []), "B": ([], [])}
    for ref, p in spec["parts"].items():
        side = "F" if p["side"] == "top" else "B"
        mir = side == "B"
        L, T = S[side]
        if p.get("box") and ref in ("U1", "J3", "C1"):
            L.append(rect(*p["box"]))
        pads = p["pads"]
        xs = [q[1] for q in pads]; ys = [q[2] for q in pads]
        if ref in ("J2", "J3", "J4", "J1") and len(pads) > 1:
            L.append(rect(min(xs) - 1.3, min(ys) - 1.3, max(xs) + 1.3, max(ys) + 1.3))
        # зүүний нэрс
        for name, x, y, d, dr, net in pads:
            if ref == "U1":
                anchor = "left" if x < 26 else "right"
                dx = 1.25 if x < 26 else -1.25
                if mir:
                    anchor = {"left": "right", "right": "left"}[anchor]
                T.append(text_poly(name, x + dx, y, 0.7, anchor, mir))
            elif ref in ("J2",):
                T.append(text_poly(name, x, y - 2.0, 0.65, "center", mir))
            elif ref in ("J3", "J4", "J1"):
                T.append(text_poly(name, x, y + (2.0 if ref == "J1" else -2.0), 0.55 if ref == "J3" else 0.62, "center", mir))
        if ref == "D1":
            bx0, by0, bx1, by1 = p["box"]
            L.append(rect(bx0, by0, bx1, by1))
            kx = [q[1] for q in pads if q[0] == "K"][0]
            band = bx1 - 0.35 if kx > (bx0 + bx1) / 2 else bx0 + 0.35   # катодын судал (K тал)
            L.append([(band, by0), (band, by1)])
            L.append([(band - 0.2, by0), (band - 0.2, by1)])
            T.append(text_poly("D1", (bx0 + bx1) / 2 - 0.3, (by0 + by1) / 2, 0.8, "center", mir))
            T.append(text_poly("SS34  K", kx, by1 + 1.0, 0.6, "center", mir))
        if ref == "C1":
            T.append(text_poly("+", pads[0][1] - 1.7, pads[0][2], 1.0, "center", mir))
            bx0, by0, bx1, by1 = p["box"]
            T.append(text_poly("C1 470µF", (bx0 + bx1) / 2, (by0 + by1) / 2, 0.9, "center", mir))
        if ref == "U1":
            bx0, by0, bx1, by1 = p["box"]
            T.append(text_poly("U1 ESP32-S3-Zero\n(pin header дээр)\nUSB-C ↓", (bx0 + bx1) / 2, 21.0, 0.85, "center", mir))
        if ref == "J3":
            bx0, by0, bx1, by1 = p["box"]
            T.append(text_poly("J3 MPU9250", (bx0 + bx1) / 2, 23.5, 1.1, "center", mir))
    for side, box, label in spec["areas"]:
        s = "F" if side == "top" else "B"
        S[s][0].append(rect(*box))
        cx = (box[0] + box[2]) / 2
        S[s][1].append(text_poly(label, cx, 18.5, 1.0, "center", s == "B"))
        S[s][1].append(text_poly("J1: OUT+/OUT- утсаар\nB+/B- → LiPo батерей", cx, 23.5, 0.7, "center", s == "B"))
    if spec["name"] == "A":
        S["F"][1].append(text_poly("MotionCare v4 · A", 27.0, 2.4, 0.8))
        S["F"][1].append(text_poly("J2 OLED: зүү дээшээ\nfirmware OLED_ROTATE_180 = 0", 9.0, 20.0, 0.75))
        S["B"][1].append(text_poly("J4 → B (эрэгтэй)", 26.08, 8.4, 0.75, "center", True))
    else:
        S["F"][1].append(text_poly("MotionCare v4 · B", 12.0, 3.0, 0.9))
        S["F"][1].append(text_poly("J4 → A (эм)", 26.08, 8.4, 0.8))
    for k in S:
        S[k] = (S[k][0], [t for t in S[k][1] if t is not None and not t.is_empty])
    return S


def fmt(v):
    return str(int(round(v * 1e6)))


class Gerber:
    def __init__(self, func):
        self.head = ["%FSLAX46Y46*%", "%MOMM*%", f"%TF.FileFunction,{func}*%"]
        self.ap, self.body = {}, ["%LPD*%", "G01*"]

    def use(self, d):
        k = round(d, 4)
        if k not in self.ap:
            self.ap[k] = 10 + len(self.ap)
            self.head.append(f"%ADD{self.ap[k]}C,{k:.4f}*%")
        self.body.append(f"D{self.ap[k]}*")

    def xy(self, x, y):
        return f"X{fmt(x)}Y{fmt(H - y)}"

    def use_rect(self, w, h):
        k = ("R", round(w, 4), round(h, 4))
        if k not in self.ap:
            self.ap[k] = 10 + len(self.ap)
            self.head.append(f"%ADD{self.ap[k]}R,{w:.4f}X{h:.4f}*%")
        self.body.append(f"D{self.ap[k]}*")

    def flash(self, x, y, d, grow=0.0):
        if isinstance(d, tuple):
            self.use_rect(d[0] + grow, d[1] + grow)
        else:
            self.use(d + grow)
        self.body.append(self.xy(x, y) + "D03*")

    def path(self, pts, d):
        self.use(d)
        self.body.append(self.xy(*pts[0]) + "D02*")
        self.body += [self.xy(*p) + "D01*" for p in pts[1:]]

    def region(self, ring, clear=False):
        if clear: self.body.append("%LPC*%")
        self.body.append("G36*")
        self.body.append(self.xy(*ring[0]) + "D02*")
        self.body += [self.xy(*p) + "D01*" for p in ring[1:]]
        self.body.append("G37*")
        if clear: self.body.append("%LPD*%")

    def poly(self, g):
        for pg in (g.geoms if isinstance(g, MultiPolygon) else [g]):
            self.region(list(pg.exterior.coords))
            for h in pg.interiors:
                self.region(list(h.coords), clear=True)

    def save(self, path):
        open(path, "w").write("\n".join(self.head + self.body + ["M02*"]) + "\n")


def export_board(spec, outdir):
    os.makedirs(outdir, exist_ok=True)
    traces, vias, pads = routed[spec["name"]]
    nm = f"MotionCare_{spec['name']}"
    for layer, ext, func in (("F", "GTL", "Copper,L1,Top"), ("B", "GBL", "Copper,L2,Bot")):
        g = Gerber(func)
        for ref, name, x, y, d, dr, net in pads:
            if on_layer(spec["name"], ref, name, dr, layer):
                g.flash(x, y, d)
        for net, x, y in vias:
            g.flash(x, y, VIA_PAD)
        for net, ly, w, pts in traces:
            if ly == layer:
                g.path(pts, w)
        g.save(f"{outdir}/{nm}.{ext}")
    for layer, ext, func in (("F", "GTS", "Soldermask,Top"), ("B", "GBS", "Soldermask,Bot")):
        g = Gerber(func)
        for ref, name, x, y, d, dr, net in pads:
            if on_layer(spec["name"], ref, name, dr, layer):
                g.flash(x, y, d, 0.1)
        g.save(f"{outdir}/{nm}.{ext}")
    S = silk_for(spec)
    for side, ext, func in (("F", "GTO", "Legend,Top"), ("B", "GBO", "Legend,Bot")):
        g = Gerber(func)
        for pl in S[side][0]:
            g.path(pl, 0.15)
        for t in S[side][1]:
            g.poly(t)
        g.save(f"{outdir}/{nm}.{ext}")
    g = Gerber("Profile,NP")
    g.path(rect(0, 0, W, H), 0.1)
    g.save(f"{outdir}/{nm}.GKO")

    def drill(name, holes, plated):
        tools = sorted({round(d, 2) for _, _, d in holes})
        out = ["M48", "METRIC,TZ", f";TYPE={'PLATED' if plated else 'NON_PLATED'}"]
        out += [f"T{i}C{d:.3f}" for i, d in enumerate(tools, 1)] + ["%", "G90", "G05"]
        for i, d in enumerate(tools, 1):
            out.append(f"T{i}")
            out += [f"X{x:.3f}Y{H - y:.3f}" for x, y, hd in holes if round(hd, 2) == d]
        out.append("M30")
        open(f"{outdir}/{name}", "w").write("\n".join(out) + "\n")
    drill(f"{nm}-PTH.DRL", [(x, y, dr) for _, _, x, y, d, dr, n in pads if dr] + [(x, y, VIA_DRILL) for _, x, y in vias], True)
    drill(f"{nm}-NPTH.DRL", [(x, y, MOUNT_D) for x, y in MOUNT], False)
    with zipfile.ZipFile(f"{outdir}/{nm}_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(outdir)):
            if f.startswith(nm) and not f.endswith(".zip"):
                z.write(f"{outdir}/{f}", f)
    return S


# ------------------------------------------------------------------ preview
def draw(ax, spec, S, view):
    traces, vias, pads = routed[spec["name"]]
    mir = view == "bottom"
    X = (lambda x: W - x) if mir else (lambda x: x)
    ax.add_patch(plt.Rectangle((0, 0), W, H, fc="#1f5e3a", ec="#b8c9bd", lw=1.2, zorder=0))
    near, far = ("B", "F") if mir else ("F", "B")
    for net, ly, w, pts in traces:
        xs = [X(p[0]) for p in pts]; ys = [p[1] for p in pts]
        if ly == near:
            ax.plot(xs, ys, color="#d9480f" if ly == "F" else "#1c7ed6", lw=w * ppm, solid_capstyle="round", zorder=3)
        else:
            ax.plot(xs, ys, color="#1c7ed6" if ly == "B" else "#d9480f", lw=w * ppm, alpha=0.28, solid_capstyle="round", zorder=2)
    for ref, name, x, y, d, dr, net in pads:
        if isinstance(d, tuple):
            al = 1.0 if on_layer(spec["name"], ref, name, dr, near) else 0.3
            ax.add_patch(plt.Rectangle((X(x) - d[0] / 2, y - d[1] / 2), d[0], d[1], fc="#d4a017", alpha=al, zorder=4))
            continue
        ax.add_patch(plt.Circle((X(x), y), d / 2, fc="#d4a017", zorder=4))
        ax.add_patch(plt.Circle((X(x), y), dr / 2, fc="#111", zorder=5))
    for net, x, y in vias:
        ax.add_patch(plt.Circle((X(x), y), VIA_PAD / 2, fc="#c9a227", zorder=4))
        ax.add_patch(plt.Circle((X(x), y), VIA_DRILL / 2, fc="#111", zorder=5))
    for x, y in MOUNT:
        ax.add_patch(plt.Circle((X(x), y), MOUNT_D / 2, fc="#111", ec="#ddd", lw=0.6, zorder=5))
    side = "B" if mir else "F"
    for pl in S[side][0]:
        ax.plot([X(p[0]) for p in pl], [p[1] for p in pl], color="white", lw=0.15 * ppm, zorder=6)
    for t in S[side][1]:
        for pg in (t.geoms if isinstance(t, MultiPolygon) else [t]):
            xs, ys = pg.exterior.xy
            ax.fill([X(v) for v in xs], ys, color="white", lw=0, zorder=7)
            for h in pg.interiors:
                xs, ys = h.xy
                ax.fill([X(v) for v in xs], ys, color="#1f5e3a", lw=0, zorder=7)
    # модулийн бие (тасархай)
    for ref, p in spec["parts"].items():
        if p.get("box") and ((p["side"] == "top") != mir) and ref in ("J2", "U1", "J3"):
            x0, y0, x1, y1 = p["box"]
            xa, xb = sorted((X(x0), X(x1)))
            ax.add_patch(plt.Rectangle((xa, y0), xb - xa, y1 - y0, fc="none", ec="#ffe066", lw=1.0, ls=(0, (4, 3)), zorder=8))
    for s, box, label in spec["areas"]:
        if (s == "bottom") == mir:
            x0, y0, x1, y1 = box
            xa, xb = sorted((X(x0), X(x1)))
            ax.add_patch(plt.Rectangle((xa, y0), xb - xa, y1 - y0, fc="none", ec="#ffe066", lw=1.0, ls=(0, (4, 3)), zorder=8))
    ax.set_xlim(-1, W + 1); ax.set_ylim(H + 1, -1); ax.set_aspect("equal"); ax.axis("off")


ppm = 0
if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    sheets = {}
    for spec in BOARDS:
        sheets[spec["name"]] = export_board(spec, f"out/board_{spec['name']}")
    fig, axes = plt.subplots(2, 2, figsize=(12, 11.8), dpi=170)
    ppm = 12 / 2 * 72 / (W + 2) * 0.86
    titles = {("A", "top"): "A самбар — дээд тал (OLED)", ("A", "bottom"): "A самбар — доод тал (ESP32-S3-Zero, TP4056, D1) · доороос харсан",
              ("B", "top"): "B самбар — дээд тал (J4 холбогч)", ("B", "bottom"): "B самбар — доод тал (MPU9250, C1) · доороос харсан"}
    for r, spec in enumerate(BOARDS):
        for c, view in enumerate(("top", "bottom")):
            draw(axes[r][c], spec, sheets[spec["name"]], view)
            axes[r][c].set_title(titles[(spec["name"], view)], fontsize=11)
    fig.suptitle(f"MotionCare v4 (ESP32-S3-Zero) — 2 давхар PCB ({W:.0f}×{H:.0f} мм), улбар шар: дээд зэс, цэнхэр: доод зэс", fontsize=13)
    fig.tight_layout()
    fig.savefig("out/pcb_v4_overview.png", facecolor="white")
    print("ok", os.listdir("out"))
