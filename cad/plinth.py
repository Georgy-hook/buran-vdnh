"""Open-backed SLA underframe for the single-piece display plinth (mm)."""
import math

import FreeCAD as App
import Part

V = App.Vector
ROOF = 2.0
WEB = 1.65


def _inset(points, dist):
    """Intersect consecutive inward-offset lines; the source deck is CCW."""
    normals = []
    for a, b in zip(points, points[1:] + points[:1]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        normals.append((-dy/length, dx/length))
    outline = []
    for i, (x, y) in enumerate(points):
        a, b = normals[i-1], normals[i]
        k = dist / (1 + a[0]*b[0] + a[1]*b[1])
        outline.append((x+k*(a[0]+b[0]), y+k*(a[1]+b[1])))
    return outline


def _ring(points, z):
    return Part.makePolygon([V(x,y,z) for x, y in points + points[:1]])


def hollow_deck(exterior, top, foot_z, deck_z, stations):
    # A single unobstructed mouth. Both rings derive from the same polygon;
    # positive draft toward the open bottom, no blind corner under the foot.
    ceiling = deck_z - ROOF
    mouth = _inset(top, 1.5)
    inner = _inset(top, 2.2)
    void = Part.makeLoft([_ring(mouth, foot_z-.30), _ring(inner, ceiling)], True, True)
    skin = exterior.cut(void)

    # Shallow intersecting beams (not bulkheads). Connected bays can all drain
    # downward; even under a web there is 2.25 mm of clear height to the rim.
    low = foot_z + 2.25
    high = ceiling + .14
    beams = [Part.makeBox(150, WEB, high-low, V(32, -WEB/2, low))]
    for x in (54, 80, 106, 132, 155, 169):
        beams.append(Part.makeBox(WEB, 85, high-low, V(x-WEB/2, -42, low)))
    # Clip at the inner wall, not the exterior lettering or shadow reveal.
    clip = Part.makeLoft([_ring(_inset(top, 1.22), low),
                          _ring(_inset(top, 1.86), high)], True, True)
    network = beams[0].multiFuse(beams[1:]).common(clip)

    bosses = []
    for x, y in stations:
        # Broad face at roof to spread load. A through-keyway is cut in the
        # final operation: the socket has neither a false floor nor a resin cup.
        start = foot_z + .85
        bosses.append(Part.makeCone(3.76, 5.30, high-start, V(x, y, start)))
    return skin.multiFuse([network, *bosses]).removeSplitter()
