"""2 давхаргатай grid A* router (45° чиглэл, via-тай) + shapely DRC."""
import heapq, itertools, math
import numpy as np
from scipy.ndimage import distance_transform_edt
from shapely.geometry import LineString, Point, box as sbox


def pad_layers(drill, layer):
    """Нүхтэй (THT) дэвсгэр хоёр талд, SMD (drill=0) зөвхөн өөрийн талд."""
    return (0, 1) if drill else (layer,)


def pad_geom(x, y, d):
    if isinstance(d, tuple):
        return sbox(x - d[0] / 2, y - d[1] / 2, x + d[0] / 2, y + d[1] / 2)
    return Point(x, y).buffer(d / 2, 32)


def pad_r(d):
    """Зорилтот хүрээ (дотор талын тойрог)"""
    return min(d) / 2 if isinstance(d, tuple) else d / 2
from design import CLEARANCE, VIA_PAD, VIA_DRILL, NET_W, MOUNT, MOUNT_D

RES = 0.1          # мм / нүд
MARGIN = 0.12      # растерийн алдааг нөхөх нэмэлт зай
VIA_COST = 60      # 6 мм-тэй тэнцэх зардал
EDGE = 0.6


class Board:
    def __init__(self, spec, size):
        self.spec = spec
        self.W, self.H = size
        self.nx, self.ny = int(round(self.W / RES)), int(round(self.H / RES))
        self.owner = [np.full((self.ny, self.nx), -1, np.int16) for _ in range(2)]  # 0=F, 1=B
        self.nets = {}
        self.traces = []   # (net, layer 'F'/'B', width, [(x,y)...])
        self.vias = []     # (net, x, y)
        self.pads = []     # (ref, name, x, y, d, drill, net)
        self.padlayer = {}  # (ref,name) → 0/1 (SMD-ийн тал)
        for ref, p in spec["parts"].items():
            for name, x, y, d, drill, net in p["pads"]:
                self.pads.append((ref, name, x, y, d, drill, net))
                self.padlayer[(ref, name)] = 1 if p["side"] == "bottom" else 0
        self.rawd = {(round(x, 4), round(y, 4)): d for ref, name, x, y, d, drill, net in self.pads}
        ys, xs = np.mgrid[0:self.ny, 0:self.nx]
        self.cx = (xs + 0.5) * RES
        self.cy = (ys + 0.5) * RES
        # Keepout: модулийн доод талын дэвсгэрүүд / TP4056-ийн ар тал зэсэнд хүрэхгүйн тулд
        for L, (x0, y0, x1, y1) in spec.get("keepouts", []):
            self._rect(L, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0, y1 - y0), self.nid("__keep__"))
        for ref, name, x, y, d, drill, net in self.pads:
            nid = self.nid(net or f"{ref}.{name}")
            for L in pad_layers(drill, self.padlayer[(ref, name)]):
                if isinstance(d, tuple):
                    self._rect(L, x, y, d, nid)
                else:
                    self._disc(L, x, y, d / 2, nid)
        for mx, my in MOUNT:
            for L in (0, 1):
                self._disc(L, mx, my, MOUNT_D / 2, self.nid("__hole__"))

    def nid(self, net):
        if net not in self.nets:
            self.nets[net] = len(self.nets)
        return self.nets[net]

    def _window(self, x0, y0, x1, y1):
        i0 = max(0, int((y0) / RES) - 1); i1 = min(self.ny, int((y1) / RES) + 2)
        j0 = max(0, int((x0) / RES) - 1); j1 = min(self.nx, int((x1) / RES) + 2)
        return i0, i1, j0, j1

    def _disc(self, L, x, y, r, nid):
        i0, i1, j0, j1 = self._window(x - r, y - r, x + r, y + r)
        m = (self.cx[i0:i1, j0:j1] - x) ** 2 + (self.cy[i0:i1, j0:j1] - y) ** 2 <= r * r
        self.owner[L][i0:i1, j0:j1][m] = nid

    def _rect(self, L, x, y, d, nid):
        w, h = d
        i0, i1, j0, j1 = self._window(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        m = (abs(self.cx[i0:i1, j0:j1] - x) <= w / 2) & (abs(self.cy[i0:i1, j0:j1] - y) <= h / 2)
        self.owner[L][i0:i1, j0:j1][m] = nid

    def _seg(self, L, a, b, r, nid):
        (x0, y0), (x1, y1) = a, b
        i0, i1, j0, j1 = self._window(min(x0, x1) - r, min(y0, y1) - r, max(x0, x1) + r, max(y0, y1) + r)
        px, py = self.cx[i0:i1, j0:j1], self.cy[i0:i1, j0:j1]
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy or 1e-9
        t = np.clip(((px - x0) * dx + (py - y0) * dy) / L2, 0, 1)
        m = (px - x0 - t * dx) ** 2 + (py - y0 - t * dy) ** 2 <= r * r
        self.owner[L][i0:i1, j0:j1][m] = nid

    def free_mask(self, L, nid, half):
        other = (self.owner[L] != -1) & (self.owner[L] != nid)
        dist = distance_transform_edt(~other) * RES
        ok = dist > half + CLEARANCE + MARGIN
        e = EDGE + half
        ok &= (self.cx > e) & (self.cx < self.W - e) & (self.cy > e) & (self.cy < self.H - e)
        return ok

    def route_net(self, net):
        nid = self.nid(net)
        w = NET_W[net]
        pins = [(x, y, pad_r(d) * 2, pad_layers(dr, self.padlayer[(ref, name)])) for ref, name, x, y, d, dr, n in self.pads if n == net]
        if len(pins) < 2:
            return
        free = [self.free_mask(L, nid, w / 2) for L in (0, 1)]
        vfree = self.free_mask(0, nid, VIA_PAD / 2) & self.free_mask(1, nid, VIA_PAD / 2)
        # Ойрын хос зүүнээс эхэлнэ (Prim)
        connected = [pins[0]]
        remaining = pins[1:]
        while remaining:
            remaining.sort(key=lambda p: min(math.dist(p[:2], c[:2]) for c in connected))
            tgt = remaining.pop(0)
            path = self._astar(nid, free, vfree, tgt, remaining)
            if path is None:
                raise RuntimeError(f"{self.spec['name']}: {net} замыг олсонгүй → {tgt}")
            allowed = free
            self._commit(net, nid, w, path, allowed)
            connected.append(tgt)

    def _astar(self, nid, free, vfree, tgt, remaining):
        tx, ty, td, tl = tgt
        own = [self.owner[L] == nid for L in (0, 1)]
        disc = (self.cx - tx) ** 2 + (self.cy - ty) ** 2 <= (td / 2 - 0.05) ** 2
        none = np.zeros_like(disc)
        tgt_masks = [(disc & free[L]) if L in tl else none for L in (0, 1)]   # SMD бол зөвхөн өөрийн талд; зөвхөн зайтай нүд
        unconn = np.zeros_like(disc)
        for rx, ry, rd, rl in remaining + [tgt]:
            raw = self.rawd.get((round(rx, 4), round(ry, 4)))
            if isinstance(raw, tuple):   # тэгш өнцөгт (SMD) дэвсгэр — бүтэн хэлбэрээр
                unconn |= (abs(self.cx - rx) <= raw[0] / 2 + 0.05) & (abs(self.cy - ry) <= raw[1] / 2 + 0.05)
            else:
                unconn |= (self.cx - rx) ** 2 + (self.cy - ry) ** 2 <= (rd / 2 + 0.05) ** 2
        # эхлэл: өөрийн сүлжээний зэс (зорилтот pad-аас бусад)
        starts = []
        for L in (0, 1):
            src = own[L] & ~unconn & free[L]   # төв шугам бусад сүлжээнээс зайтай байх ёстой
            ii, jj = np.nonzero(src)
            for i, j in zip(ii, jj):
                starts.append((L, i, j))
        tj, ti = int(tx / RES), int(ty / RES)
        def h(i, j):
            return math.hypot(i - ti, j - tj)
        openh, g, came = [], {}, {}
        for s in starts:
            g[s] = 0.0
            heapq.heappush(openh, (h(s[1], s[2]), s))
        moves = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
        closed = set()
        while openh:
            f, cur = heapq.heappop(openh)
            if cur in closed:
                continue
            closed.add(cur)
            L, i, j = cur
            if tgt_masks[L][i, j]:
                path = [cur]
                while path[-1] in came:
                    path.append(came[path[-1]])
                return path[::-1]
            gc = g[cur]
            nbrs = []
            for di, dj, c in moves:
                ni, nj = i + di, j + dj
                if 0 <= ni < self.ny and 0 <= nj < self.nx and (free[L][ni, nj] or tgt_masks[L][ni, nj]):
                    nbrs.append(((L, ni, nj), c))
            if vfree[i, j] and not own[L][i, j]:
                nbrs.append(((1 - L, i, j), VIA_COST))
            for nb, c in nbrs:
                ng = gc + c
                if ng < g.get(nb, 1e18):
                    g[nb] = ng
                    came[nb] = cur
                    heapq.heappush(openh, (ng + h(nb[1], nb[2]), nb))
        return None

    def _clear(self, allowed, a, b):
        n = max(2, int(math.dist(a, b) / (RES * 0.5)) + 1)
        for k in range(n + 1):
            t = k / n
            x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
            if not allowed[int(y / RES), int(x / RES)]:
                return False
        return True

    def _commit(self, net, nid, w, path, allowed):
        # давхарга солигдох цэгт via
        runs, cur = [], [path[0]]
        for a, b in zip(path, path[1:]):
            if a[0] != b[0]:
                runs.append(cur); cur = [b]
                x, y = (a[2] + 0.5) * RES, (a[1] + 0.5) * RES
                self.vias.append((net, x, y))
                for L in (0, 1):
                    self._disc(L, x, y, VIA_PAD / 2, nid)
            else:
                cur.append(b)
        runs.append(cur)
        for run in runs:
            if len(run) < 2:
                continue
            L = run[0][0]
            pts = [(float((c[2] + 0.5) * RES), float((c[1] + 0.5) * RES)) for c in run]
            # string pulling: харагдах хамгийн холын цэг рүү шууд
            simp, i = [pts[0]], 0
            while i < len(pts) - 1:
                j = len(pts) - 1
                while j > i + 1 and not self._clear(allowed[L], pts[i], pts[j]):
                    j -= 1
                simp.append(pts[j]); i = j
            self.traces.append((net, "FB"[L], w, simp))
            for a, b in zip(simp, simp[1:]):
                self._seg(L, a, b, w / 2, nid)

    # ------------------------------------------------------ DRC
    def drc(self):
        errs = []
        def items(layer):
            out = []
            for ref, name, x, y, d, dr, net in self.pads:
                if "FB".index(layer) in pad_layers(dr, self.padlayer[(ref, name)]):
                    out.append((net or f"{ref}.{name}", pad_geom(x, y, d), f"{ref}.{name}"))
            for net, x, y in self.vias:
                out.append((net, Point(x, y).buffer(VIA_PAD / 2, 32), f"via({net})"))
            for k, (net, ly, w, pts) in enumerate(self.traces):
                if ly == layer:
                    g = LineString(pts).buffer(w / 2, 16) if len(pts) > 1 else Point(pts[0]).buffer(w / 2)
                    out.append((net, g, f"trace#{k}({net})"))
            return out
        outline = sbox(0, 0, self.W, self.H)
        for layer in "FB":
            its = items(layer)
            for (n1, g1, d1), (n2, g2, d2) in itertools.combinations(its, 2):
                if n1 != n2 and g1.distance(g2) < CLEARANCE:
                    errs.append(f"[{layer}] {d1} ↔ {d2}: {g1.distance(g2):.3f}")
            for n, g, d in its:
                if g.distance(outline.exterior) < 0.4 or not outline.contains(g):
                    errs.append(f"[{layer}] {d} ирмэгт ойр")
                for mx, my in MOUNT:
                    if g.distance(Point(mx, my).buffer(MOUNT_D / 2)) < 0.4:
                        errs.append(f"[{layer}] {d} нүхэнд ойр")
        # keepout зөрчил (дэвсгэрээс бусад зэс)
        for L, kb in self.spec.get("keepouts", []):
            layer = "FB"[L]
            kg = sbox(*kb)
            for net, x, y in self.vias:
                if Point(x, y).buffer(VIA_PAD / 2).distance(kg) < CLEARANCE:
                    errs.append(f"[{layer}] via({net}) keepout-д")
            for net, ly, w, pts in self.traces:
                if ly == layer and len(pts) > 1:
                    tg = LineString(pts).buffer(w / 2, 16)
                    padu = [pad_geom(x, y, d).buffer(CLEARANCE) for r, nm, x, y, d, dr, n in self.pads if n == net]
                    rest = tg
                    for pg in padu:
                        rest = rest.difference(pg)
                    if rest.distance(kg) < CLEARANCE and rest.area > 1e-3:
                        errs.append(f"[{layer}] trace({net}) keepout-д")
        # холболт
        for net in self.spec["spec"]:
            objs = [("P" if dr else "FB"[self.padlayer[(ref, name)]], pad_geom(x, y, d)) for ref, name, x, y, d, dr, n in self.pads if n == net]
            objs += [("P", Point(x, y).buffer(VIA_PAD / 2, 32)) for n, x, y in self.vias if n == net]
            objs += [(ly, LineString(pts).buffer(w / 2, 16)) for n, ly, w, pts in self.traces if n == net and len(pts) > 1]
            parent = list(range(len(objs)))
            def f(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]; i = parent[i]
                return i
            for i, j in itertools.combinations(range(len(objs)), 2):
                a, b = objs[i], objs[j]
                if a[0] != "P" and b[0] != "P" and a[0] != b[0]:
                    continue
                if a[1].intersects(b[1]):
                    parent[f(i)] = f(j)
            if len({f(i) for i in range(len(objs))}) != 1:
                errs.append(f"{net} тасархай")
        actual = {}
        for ref, name, x, y, d, dr, net in self.pads:
            if net:
                actual.setdefault(net, set()).add(f"{ref}.{name}")
        if actual != self.spec["spec"]:
            errs.append(f"netlist зөрүү: {actual}")
        return errs
