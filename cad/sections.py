"""Measured in model millimetres. X points aft, Y starboard, Z up."""

import FreeCAD as App
import Part

V = App.Vector
PORCELAIN = '#e9e7de'
TILES = '#32383d'
TILE_EDGE = '#475057'
GLASS = '#263c4c'
FRAME = '#626b70'
RED = '#ba2c34'

# x, half-breadth, keel, lower chine, shoulder, crown. Not factory loft data.
NOSE = [
    (0, .68, 12.55, 12.8, 13.45, 13.75),
    (.43, 2.52, 10.98, 11.7, 14.45, 15.5),
    (1.8, 5.1, 9.1, 11.4, 16.4, 19.1),
    (5.5, 7.6, 7.0, 10.3, 17.5, 21.1),
    (13, 10.6, 4.8, 9.1, 19.0, 24.5),
    (23, 13.8, 2.8, 7.8, 20.9, 28.6),
    (36, 16.9, 1.1, 6.8, 23.2, 33.3),
    (49, 19.1, 0.15, 6.1, 25.3, 37.2),
    (62, 19.93, 0.0, 6.35, 26.6, 39.5),
    (72, 20.0, 0.0, 6.5, 27.0, 40.0),
]


def mid(x):
    return (x, 20.0, 0.0, 6.5, 27.0, 40.0)


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, V(x, y, z))


def poly(points):
    return Part.makePolygon([*points, points[0]])


def bezier(*points):
    curve = Part.BezierCurve()
    curve.setPoles(list(points))
    return curve.toShape()


def frame(station):
    x, w, base, chine, shoulder, crown = station

    def p(y, z):
        return V(x, y * w, z)

    def flank(s):
        return [
            bezier(p(.37*s, base), p(.72*s, base), p(s, base+.28*(chine-base)), p(s, chine)),
            Part.makeLine(p(s, chine), p(s, shoulder)),
            bezier(p(s, shoulder), p(s, shoulder+.67*(crown-shoulder)), p(.56*s, crown), p(.15*s, crown)),
        ]

    near = flank(1)
    far = flank(-1)
    for edge in far:
        edge.reverse()
    return Part.Wire([
        Part.makeLine(p(-.37, base), p(.37, base)), *near,
        Part.makeLine(p(.15, crown), p(-.15, crown)), *reversed(far),
    ])


def inset(station, side, bottom, top):
    x, w, keel, chine, shoulder, crown = station
    height = crown - keel
    factor = (height - bottom - top) / height
    return (x, w-side, keel+bottom, keel+bottom+(chine-keel)*factor,
            keel+bottom+(shoulder-keel)*factor, crown-top)


def station_at(x):
    if x >= 72:
        return mid(x)
    for a, b in zip(NOSE, NOSE[1:]):
        if a[0] <= x <= b[0]:
            t = (x-a[0])/(b[0]-a[0])
            return tuple(i*(1-t) + j*t for i, j in zip(a, b))
    raise ValueError(x)


def shell_blank(stations):
    wires = [frame(s) for s in stations]
    if len(wires) == 2 and stations[0][1:] == stations[1][1:]:
        return Part.Face(wires[0]).extrude(V(stations[1][0]-stations[0][0], 0, 0))
    return Part.makeLoft(wires, True, False, False, 3)


def compound(shapes):
    return shapes[0] if len(shapes) == 1 else Part.makeCompound(shapes)


def fuse(base, shapes):
    if not shapes:
        return base
    return base.fuse(shapes, 1.e-7).removeSplitter()


def cut(base, shapes):
    if not shapes:
        return base
    return base.cut(shapes, 1.e-7).removeSplitter()


def item(key, label, shape, color, explode, orientation, note, paint=None):
    return dict(id=key, label=label, shape=shape, group='Фюзеляж', color=color,
                explode=explode, orientation=orientation, note=note, paint=paint)
