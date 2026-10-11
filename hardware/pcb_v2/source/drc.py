"""Энгийн DRC: өөр сүлжээний зэс хоорондын зай, ирмэгийн зай, холболт бүрэн эсэх."""
import itertools
from shapely.geometry import LineString, Point, box as sbox
from shapely.ops import unary_union
from layout import parts, traces, BOARD, CLEARANCE, MOUNT, MOUNT_D

def copper(layer):
    items = []  # (net, geom, desc)
    for ref, p in parts.items():
        for name, x, y, d, drill, net in p["pads"]:
            items.append((net or f"{ref}.{name}", Point(x, y).buffer(d / 2, 32), f"{ref}.{name}"))
    for i, (net, ly, w, pts) in enumerate(traces):
        if ly == layer:
            items.append((net, LineString(pts).buffer(w / 2, 16), f"trace#{i}({net})"))
    return items

errors = []
for layer in "FB":
    items = copper(layer)
    for (n1, g1, d1), (n2, g2, d2) in itertools.combinations(items, 2):
        if n1 == n2:
            continue
        dist = g1.distance(g2)
        if dist < CLEARANCE:
            errors.append(f"[{layer}] {d1} ↔ {d2}: {dist:.3f} мм")
    edge = sbox(0, 0, *BOARD).exterior
    for n, g, d in items:
        if g.distance(edge) < 0.5 or not sbox(0, 0, *BOARD).contains(g):
            errors.append(f"[{layer}] {d} ирмэгт ойр ({g.distance(edge):.2f})")
        for mx, my in MOUNT:
            if g.distance(Point(mx, my).buffer(MOUNT_D / 2)) < 0.4:
                errors.append(f"[{layer}] {d} бэхэлгээний нүхэнд ойр")

# Холболт: сүлжээ бүр нэг бүрэлдэхүүн болох уу (THT pad хоёр давхаргыг холбоно)
nets = {}
for ref, p in parts.items():
    for name, x, y, d, drill, net in p["pads"]:
        if net:
            nets.setdefault(net, []).append(("pad", Point(x, y).buffer(d / 2, 32), f"{ref}.{name}"))
for net, ly, w, pts in traces:
    nets.setdefault(net, []).append((ly, LineString(pts).buffer(w / 2, 16), "trace"))
for net, items in nets.items():
    # union-find
    parent = list(range(len(items)))
    def f(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, j in itertools.combinations(range(len(items)), 2):
        a, b = items[i], items[j]
        if a[0] != "pad" and b[0] != "pad" and a[0] != b[0]:
            continue  # өөр давхаргын замууд шууд холбогдохгүй
        if a[1].intersects(b[1]):
            parent[f(i)] = f(j)
    groups = {f(i) for i in range(len(items))}
    if len(groups) > 1:
        errors.append(f"Сүлжээ {net} тасархай: {len(groups)} хэсэг")

# Холболтын хүснэгттэй тулгах
SPEC = {
    "VBAT": {"J1.OUT+", "C1.+", "U1.5V"},
    "GND": {"J1.OUT-", "C1.-", "U1.GND", "J2.GND", "J3.GND"},
    "3V3": {"U1.3V3", "J2.VCC", "J3.VCC"},
    "SDA": {"U1.IO6", "J2.SDA", "J3.SDA"},
    "SCL": {"U1.IO7", "J2.SCL", "J3.SCL"},
}
actual = {}
for ref, p in parts.items():
    for name, x, y, d, drill, net in p["pads"]:
        if net:
            actual.setdefault(net, set()).add(f"{ref}.{name}")
if actual != SPEC:
    errors.append(f"Netlist зөрүүтэй: {actual} != {SPEC}")
else:
    print("Netlist = холболтын хүснэгт ✓")
print("\n".join(errors) if errors else "DRC OK — алдаа алга")
widths = sorted({round(w / 0.0254) for _, _, w, _ in traces})
print("Дамжуулагчийн өргөн (mil):", widths)
