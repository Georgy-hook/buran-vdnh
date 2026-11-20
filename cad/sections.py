"""Measured in model millimetres. X points aft, Y starboard, Z up."""

import FreeCAD as App
import Part

V = App.Vector
PORCELAIN = '#e9e7de'
TILES = '#32383d'
TILE_EDGE = '#475057'
GLASS = '#263c4c'
FRAME = '#454b4d'
RED = '#ba2c34'

# x, half-breadth, keel, lower chine, shoulder, crown. Not factory loft data.
NOSE = [
    (0, .65, 12.57, 13.00, 13.20, 13.76),
    (.54, 3.18, 10.58, 12.40, 13.68, 16.05),
    (2.20, 5.73, 8.86, 11.63, 14.85, 18.35),
    (5.50, 8.02, 7.06, 10.72, 16.29, 20.43),
    (13, 11.41, 4.80, 9.32, 18.35, 24.17),
    (23, 14.65, 2.80, 7.84, 20.48, 28.91),
    (31, 16.52, 1.57, 7.13, 22.02, 32.95),
    (39, 17.93, .68, 6.51, 23.61, 38.12),
    (46, 18.90, .21, 6.18, 24.90, 40.23),
    (54, 19.59, .03, 6.13, 25.96, 40.65),
    (63, 19.93, .00, 6.37, 26.69, 40.25),
    (68, 19.99, .00, 6.47, 26.94, 40.05),
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

    # Round cap and brow, broad floor only under the gear and flat bay roof aft.
    # Use the same law for the inset core and engraving limiter as for the skin.
    t = min(1., max(0., (x - 8.) / 58.))
    t = t*t*(3. - 2.*t)
    keel_flat = .07 + .30*t
    roof_flat = .035 + .115*t

    def p(y, z):
        return V(x, y * w, z)

    def flank(s):
        return [
            bezier(p(keel_flat*s, base), p((.57+.15*t)*s, base),
                   p(s, base+(.36-.08*t)*(chine-base)), p(s, chine)),
            Part.makeLine(p(s, chine), p(s, shoulder)),
            bezier(p(s, shoulder), p(s, shoulder+(.55+.12*t)*(crown-shoulder)),
                   p((.54+.02*t)*s, crown), p(roof_flat*s, crown)),
        ]

    near = flank(1)
    far = flank(-1)
    for edge in far:
        edge.reverse()
    return Part.Wire([
        Part.makeLine(p(-keel_flat, base), p(keel_flat, base)), *near,
        Part.makeLine(p(roof_flat, crown), p(-roof_flat, crown)), *reversed(far),
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
