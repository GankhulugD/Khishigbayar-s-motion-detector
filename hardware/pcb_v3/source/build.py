import itertools, sys, pickle
from design import BOARDS, BOARD
from router import Board

ORDERS = [["GND", "VBAT", "3V3", "SCL", "SDA"]] + [list(p) for p in itertools.permutations(["GND", "VBAT", "3V3", "SCL", "SDA"])]
results = {}
for spec in BOARDS:
    for order in ORDERS:
        bd = Board(spec, BOARD)
        try:
            for net in order:
                bd.route_net(net)
        except RuntimeError as e:
            continue
        errs = bd.drc()
        print(spec["name"], order, "vias:", len(bd.vias), "DRC:", "OK" if not errs else errs[:5])
        if not errs:
            results[spec["name"]] = bd
            break
pickle.dump({k: (v.traces, v.vias, v.pads) for k, v in results.items()}, open("routed.pkl", "wb"))
print("routed:", list(results))
