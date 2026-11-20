"""Measured VDNKh wing plan and printable, staggered thermal-skin relief.

The lower surface is generated directly as conforming rows of tile faces,
not a painted line or a Boolean subtraction of intersecting cutters.
Dimensions in model mm; upper surfaces and the spar do not inherit the grid.
"""
from bisect import bisect_right
import math

import Part
from FreeCAD import Vector as V
from sections import PORCELAIN, TILES, mid, shell_blank

CARBON = '#292d30'
JOINT = '#383b3c'
# |y|, leading and trailing x, thickness, elevon chord, upper lip width.
# Moscow, Esri World Imagery 19/163696/316936 + neighbours, registered by
# nose and fuselage centreline; Google satellite z20 as a plan cross-check.
# Pixel edges (especially the leading-edge shadow) are not survey coordinates.
WING = (
    (20.0, 79.5, 204.0, 10.4, 21.8, 1.50),
    (24.0, 96.0, 203.5, 9.5, 21.1, 1.65),
    (29.0, 112.0, 202.8, 8.7, 20.6, 1.95),
    (33.0, 120.8, 202.1, 8.1, 20.0, 2.35),
    (38.0, 127.5, 201.3, 7.5, 19.4, 2.75),
    (50.0, 139.5, 199.3, 6.2, 17.8, 2.75),
    (65.0, 154.7, 196.8, 4.9, 15.5, 2.55),
    (75.0, 165.8, 195.0, 3.7, 13.7, 2.30),
    (80.0, 172.2, 194.1, 3.0, 12.9, 2.05),
    (82.3, 177.0, 193.5, 2.4, 12.3, 1.65),
    (83.3, 180.0, 192.9, 2.05, 10.8, 1.15),
)
# A physical 150 mm tile would span 1.04 mm at 1:144. The exhibit is a
# restored shell; surviving photographs do not resolve every tile boundary.
# Enlarge this *representative* pitch and the grooves for a washable resin print.
PITCH_X = 2.10
PITCH_Y = 1.72
GAP = .26
DEPTH = .15


def _mount(y):
    """Toe of the root enters the black chine; do not lower the wingtip.

    On the installed vehicle the upper edge of the lip meets the black belt
    in Commons BURAN_(mock_up)_(17433008202) and Buran_OK-TVA_VDNKh;
    the lateral view of the red flag gives a second, local vertical scale.
    """
    u = min(1., max(0., (abs(y)-20.)/63.3))
    return 3.0+5.*u, .72+.28*u


def section(y):
    i = max(1, min(len(WING)-1, bisect_right(WING, (abs(y), float('inf')))))
    a, b = WING[i-1:i+1]
    t = min(1., max(0., (abs(y)-a[0])/(b[0]-a[0])))
    return tuple(p+t*(q-p) for p, q in zip(a[1:], b[1:]))


def _bezier(a, b, c):
    curve = Part.BezierCurve()
    curve.setPoles([a, b, c])
    return curve.toShape()


def _profile(y, span_joint, phase, row_mid):
    le, te, thick, flap, lip = section(y)
    z0, thickness_factor = _mount(y)
    thick *= thickness_factor
    c = te-le
    h = c-flap
    hinge_top = .49*thick+.65
    end = .16*thick+1.
    front_belly = min(.12*c, .46*h)
    aft_belly = h+.45

    def point(x, z):
        return V(le+x, y, z0+z)

    # Shallow rolled lip instead of a rectangular upright black shoulder.
    upper = point(lip, .73*thick)
    lead = point(0, .40*thick)
    fore = point(front_belly, .035*thick)
    aft = point(aft_belly, .075*thick)
    trailing = point(c-.24, end-.52)
    trailing_low = point(c, end-.32)
    trailing_high = point(c, end+.32)
    upper_te = point(c-.48, end+.55)

    # Sample the tile corners on the curved lower section and wrap them
    # around the nose. Spanwise joints have one common profile on both sides.
    near_le = V(DEPTH, 0, 0)
    bottom = V(0, 0, DEPTH)
    zero = V()
    raw = [(upper, point(0, .70*thick), lead, zero, near_le),
           (lead, point(0, .075*thick), fore, near_le, bottom),
           (fore, point(.47*(front_belly+aft_belly), 0.), aft, bottom, bottom),
           (aft, point(.51*(aft_belly+c), .10*thick), trailing, bottom, bottom),
           (trailing, point(c, end-.51), trailing_low, bottom, zero)]
    mid_le, mid_te, mid_t, mid_f, mid_lip = section(row_mid)
    mid_t *= _mount(row_mid)[1]
    # Constant row-local parameterization keeps corresponding joints connected
    # on the two edges of a sloping row. Around the nose, use surface distance.
    mid_h = mid_te-mid_le-mid_f
    mid_front = min(.12*(mid_te-mid_le), .46*mid_h)
    lengths = [math.hypot(mid_lip, .50*mid_t), math.hypot(mid_front, .49*mid_t),
               mid_h+.45-mid_front, mid_f-.69, .3]
    tracks = []
    distance = phase*PITCH_X
    for (p0, p1, p2, v0, v1), length, samples in zip(raw, lengths, (6, 7, 8, 4, 2)):
        knots = {0., 1.}
        if not span_joint:
            for n in range(math.floor(distance/PITCH_X), math.ceil((distance+length)/PITCH_X)+1):
                for delta in (-GAP/2, 0., GAP/2):
                    t = (n*PITCH_X+delta-distance)/length
                    if .028 < t*length < length-.028:
                        knots.add(t)
        for i in range(1, samples):
            t = i/samples
            if span_joint or min(abs(t-u) for u in knots)*length > .04:
                knots.add(t)
        knots = sorted(knots)

        def shift(t):
            loc = distance+t*length
            frac = abs(loc/PITCH_X-round(loc/PITCH_X))*PITCH_X
            return 1. if span_joint else max(0., 1.-frac/(GAP/2))
        def base(t):
            return p0*((1.-t)**2) + p1*(2.*t*(1.-t)) + p2*(t*t)
        def relief(t):
            return (v0*(1.-t)+v1*t)*shift(t)
        tracks.append([(t, base(t)+relief(t)) for t in knots])
        distance += length

    land = min(1.55, .26*(h-lip))
    hinge_rear = point(h+.54, hinge_top)
    hinge_floor_r = point(h+.2, hinge_top-.34)
    hinge_floor_l = point(h-.31, hinge_top-.34)
    hinge_front = point(h-land, hinge_top+.34)
    crest = point(lip+.43*(h-land-lip), thick)
    edges = [Part.makeLine(trailing_low, trailing_high),
              _bezier(trailing_high, point(c, end+.53), upper_te),
              _bezier(upper_te, point(h+.51*flap, .53*(end+hinge_top)+.12), hinge_rear),
              Part.makeLine(hinge_rear, hinge_floor_r), Part.makeLine(hinge_floor_r, hinge_floor_l),
              Part.makeLine(hinge_floor_l, hinge_front),
              _bezier(hinge_front, point(h-land-.37*(h-land-crest.x+le), thick), crest),
              _bezier(crest, point(lip+.32*(crest.x-le-lip), thick), upper)]
    return tracks, edges


def _tiles(a, b):
    # This monotone strip triangulation tolerates different tile counts and
    # half-tile staggering. Neighbouring strips use exactly the same vertices
    # at their common edge; no near-coincident tiny trimming edges remain.
    i = j = 0
    while i < len(a)-1 or j < len(b)-1:
        p, q = a[i][1], b[j][1]
        fa = a[i+1][0] if i+1 < len(a) else 2.
        fb = b[j+1][0] if j+1 < len(b) else 2.
        if fa <= fb:
            i += 1
            tri = [p, a[i][1], q, p]
        else:
            j += 1
            tri = [p, b[j][1], q, p]
        yield Part.Face(Part.makePolygon(tri))


def _cap(profile):
    tracks, top = profile
    lower = [Part.makeLine(a[1], b[1]) for path in tracks for a, b in zip(path, path[1:])]
    return Part.Face(Part.Wire(lower+top))


def wing_skin():
    faces = []
    # Keep geometric planform breakpoints, registration of the elevon division,
    # and reasonably equal tile rows; never leave a tiny partial course at tip.
    spans = [r[0] for r in WING]
    stops = [spans[0]]
    for a, b in zip(spans, spans[1:]):
        n = max(1, round((b-a)/PITCH_Y))
        stops.extend(a+(b-a)*i/n for i in range(1, n+1))
    first = last = None
    for row, (a, b) in enumerate(zip(stops, stops[1:])):
        profiles = [_profile(y, seam, .23+.5*(row%2), (a+b)/2) for y, seam in
                    ((a, True), (a+GAP/2, False), (b-GAP/2, False), (b, True))]
        if first is None:
            first = profiles[0]
        for (lower_a, top_a), (lower_b, top_b) in zip(profiles, profiles[1:]):
            for track_a, track_b in zip(lower_a, lower_b):
                faces.extend(_tiles(track_a, track_b))
            faces.extend(Part.makeRuledSurface(e, f) for e, f in zip(top_a, top_b))
        last = profiles[-1]
    root = _cap(first)
    faces.extend((root, _cap(last)))
    shell = Part.makeShell(faces)
    shell.sewShape(.00002)
    solid = Part.makeSolid(shell.Shells[0])
    if solid.Volume < 0:
        solid.reverse()
    # The hull is narrower below the 6.5 mm chine. Fill the indrawn strip
    # with the exact negative of its frame; simply translating the old planar
    # root would leave daylight between the underside and the curved flank.
    # Relieve only this return by .06 mm; the flat shoulder above stays seated.
    flank = shell_blank([mid(72.), mid(210.)])
    flank.translate(V(0., .06, 0.))
    return_flange = root.extrude(V(0., -2.5, 0.)).cut(flank)
    solid = solid.fuse(return_flange)
    # Slot behind the hinge between inner and outer elevon only.
    y = 52.2
    _, te, _, flap, _ = section(y)
    start = te-flap+.85
    slot = Part.makeBox(te-start+2., .58, 22., V(start, y-.29, 0.))
    return solid.cut(slot)


def paint(x, y, z):
    le, te, t, flap, lip = section(y)
    z0, thickness_factor = _mount(y)
    t *= thickness_factor
    h = te-flap
    q = (x-le)/(te-le)
    if z < z0 + (1.-q)*.40*t + q*(.16*t+1.):
        return TILES
    if x <= le+lip+.002 or x >= te-.47:
        return CARBON
    if h-min(1.55, .26*(h-le-lip))-.002 <= x <= h+.54:
        return JOINT
    return PORCELAIN
