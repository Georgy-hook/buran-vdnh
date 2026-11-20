"""Installed BTS-001 wing, millimetres at 1:144. X aft, |Y| outboard.

Plan: Esri and Google views of the VDNKh exhibit; the satellite shadow is
not the leading edge. Profile: rounded black rim, white upper skin and two
elevons in the ground views. Relief is generated into the skin, not painted
onto a smooth triangle. Small courses are representative, not a tile survey.
"""
from bisect import bisect_right
from functools import lru_cache
import math

import Part
from FreeCAD import Vector as V
from sections import PORCELAIN, mid, shell_blank

CARBON = '#292d30'
JOINT = '#383b3c'
# |Y|, leading X, trailing X, section thickness, elevon chord, upper rim
# footprint (wider through the strake where a normal section cuts obliquely).
WING = (
    (20.0, 79.5, 204.0, 10.4, 21.8, 5.8),
    (24.0, 96.1, 203.5, 10.0, 21.3, 6.2),
    (29.0, 112.4, 202.8, 9.2, 20.6, 5.9),
    (33.0, 120.9, 202.1, 8.5, 20.0, 5.1),
    (38.0, 127.7, 201.3, 7.7, 19.4, 4.7),
    (50.0, 139.6, 199.3, 6.2, 17.8, 4.6),
    (65.0, 154.7, 196.8, 4.9, 15.5, 4.3),
    (75.0, 164.9, 195.0, 3.9, 13.7, 3.7),
    (80.0, 171.9, 194.1, 3.0, 12.9, 2.8),
    (82.3, 177.0, 193.5, 2.4, 12.3, 1.7),
    (83.3, 180.0, 192.9, 2.1, 10.8, .75),
)
DIVISION = 51.0  # transverse break in the two visible elevons
BELLY_PITCH = 2.65
BELLY_DEPTH = .245
BELLY_MOUTH = .46
COURSE_HALF_WIDTH = .23
# Five shallow pressed lines across the two elevons, not another tile field.
ELEVON_STAMPS = (4, 8, 16, 19, 22)
BELLY_LANDS = ('#414345', '#424546', '#3e4243', '#484a49', '#404343')


def _mount(y):
    u = min(1., max(0., (abs(y)-20.)/63.3))
    return 3.+5.*u, .72+.28*u


def _slope(i, j):
    """Shape-preserving Hermite tangent. No overshoot at the nose of the tip."""
    def slope(a, b):
        return (b[j]-a[j])/(b[0]-a[0])
    if i == 0:
        return slope(*WING[:2])
    if i == len(WING)-1:
        return slope(*WING[-2:])
    prev, here, nxt = WING[i-1:i+2]
    a, b = slope(prev, here), slope(here, nxt)
    return 2.*a*b/(a+b) if a*b > 0. else 0.


TANGENTS = [tuple(_slope(i, j) for j in range(1, 6)) for i in range(len(WING))]


@lru_cache(maxsize=8192)
def section(y):
    y = min(WING[-1][0], max(WING[0][0], abs(y)))
    i = max(1, min(len(WING)-1, bisect_right(WING, (y, float('inf')))))
    a, b = WING[i-1:i+1]
    dy = b[0]-a[0]
    t = (y-a[0])/dy
    blend = t*t*(3.-2.*t)
    return tuple(p+(q-p)*blend+dy*t*(1.-t)*((1.-t)*u-t*v)
                 for p, q, u, v in zip(a[1:], b[1:], TANGENTS[i-1], TANGENTS[i]))


# Pair adjoining panel strips with the SAME profile on the shared boundary.
# No intersecting cutter forest, no duplicated shell inside the wing.
def _courses():
    spans = [20., 28., 34., 41.5, DIVISION, 61., 71.5, 78.4, 81.6, 83.3]
    stops = [spans[0]]
    for a, b in zip(spans, spans[1:]):
        n = max(1, round((b-a)/2.5))
        stops.extend(a+(b-a)*i/n for i in range(1, n+1))
    return tuple(stops)


COURSES = _courses()


def _arc(p, q, r, t):
    return p*((1.-t)**2)+q*(2.*t*(1.-t))+r*(t*t)


def _track(p, q, r, resolution, depth, pitch=0., phase=0., span_seam=False,
           row_length=None, mouth=.30, floor=0., stamp=False):
    """Represent one curved run of tiles; seam width and depth in model mm."""
    length = max(row_length if row_length is not None else (r-p).Length, .02)
    half_gap = mouth/2.
    knots = {0., 1.}
    if pitch and not span_seam:
        n = 0
        while (n+phase)*pitch < length-half_gap-.08:
            centre = (n+phase)*pitch
            if centre > half_gap+.08:
                knots.update((centre+d)/length for d in (-half_gap, -floor/2., floor/2., half_gap))
            n += 1
    for i in range(1, resolution):
        t = i/resolution
        if min(abs(t-u) for u in knots)*length > .045:
            knots.add(t)
    result = []
    for t in sorted(knots):
        if pitch:
            u = t*length/pitch-phase
            amount = max(0., min(1., (half_gap-abs(u-round(u))*pitch)/(half_gap-floor/2.)))
        else:
            amount = 0.
        if span_seam:
            amount = 1.
        # Relief dies exactly at adjoining rim/spar lands, for a single shell.
        taper = min(1., t*length/.38, (1.-t)*length/.38)
        if stamp:
            # Die does not mark the hinge land or the thin trailing rim.
            taper *= max(0., min(1., (t-.10)/.12, (.90-t)/.12))
        result.append((t, _arc(p, q, r, t)+depth*(taper*amount)))
    return result


def _line(a, b):
    return [(0., a), (1., b)]


def _profile(y, row, boundary=None):
    le, te, nominal, flap, lip = section(y)
    base, scale = _mount(y)
    th = nominal*scale
    chord = te-le
    spar = chord-flap
    lip = min(lip, .40*spar)
    # A broad arched strake transitions into a finer compound-leading edge.
    # Outer elevon trails slightly below the inboard one, not a single plank.
    decline = .60*max(0., min(1., (y-DIVISION)/6.))
    end = .16*th+1.-decline
    hinge = .49*th+.69
    land = min(1.55, .26*(spar-lip))
    def p(x, z):
        return V(le+x, y, base+z)
    crown = p(lip, .74*th)
    nose = p(0., .40*th)
    shoe = p(min(1.24*lip, .50*spar), .10*th)
    low_spar = p(spar-.27, .075*th)
    gap = p(spar+.25, .075*th+.27)
    low_flap = p(spar+.68, .075*th+.09)
    low_end = p(chord-.40, end-.54)
    end_a, end_b = p(chord, end-.32), p(chord, end+.32)
    high_end = p(chord-.48, end+.55)
    high_flap = p(spar+.60, hinge-.09)
    groove_r, groove_l = p(spar+.16, hinge-.45), p(spar-.32, hinge-.45)
    high_spar = p(spar-land, hinge+.34)
    edge_seam = boundary is not None and boundary%2 == 0
    field_seam = boundary is not None
    phase = .25+.50*(row%2)
    # A swept, rapidly tapering row must share one parameter grid at BOTH
    # sides. Otherwise a tile can end at the left rail before its partner
    # even starts at the right rail, producing diagonal phantom ridges.
    midpoint = (COURSES[row]+COURSES[row+1])/2
    ml, mt, _, mf, mw = section(midpoint)
    mh = mt-ml-mf
    mw = min(mw, .40*mh)
    bottom_run = mh-.27-min(1.24*mw, .50*mh)
    top_run = mh-min(1.55, .26*(mh-mw))-mw
    # Entire smooth cap rolls under the edge. Sparse segment joints differ
    # from the finer staggered tile field between the cap and the elevon.
    return [
        _track(crown, p(.10*lip, .77*th), nose, 5, V(.33, 0, -.11), span_seam=edge_seam),
        _track(nose, p(.08*lip, .13*th), shoe, 5, V(.33, 0, .17), span_seam=edge_seam),
        _track(shoe, p((shoe.x+low_spar.x)/2.-le, -.04*th), low_spar, 6, V(0, 0, BELLY_DEPTH),
               pitch=BELLY_PITCH, mouth=BELLY_MOUTH, floor=.14, phase=phase, span_seam=field_seam,
               row_length=None if field_seam else bottom_run),
        _line(low_spar, gap), _line(gap, low_flap),
        _track(low_flap, p(spar+.51*flap, .08*th), low_end, 8, V(0, 0, .175),
               span_seam=boundary in ELEVON_STAMPS, stamp=True),
        _line(low_end, end_a), _line(end_a, end_b), _line(end_b, high_end),
        _track(high_end, p(spar+.54*flap, .53*(end+hinge)+.28), high_flap,
               5, V(0, 0, -.11), span_seam=boundary in (4, 9, 17, 21)),
        _line(high_flap, groove_r), _line(groove_r, groove_l), _line(groove_l, high_spar),
        _track(high_spar, p(lip+.50*(spar-land-lip), 1.28*th), crown, 8,
               V(0, 0, -.14), pitch=6.60, phase=phase, span_seam=field_seam,
               row_length=None if field_seam else top_run),
    ]


def _tiles(a, b):
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


def _cap(tracks):
    points = [point for track in tracks for _, point in track[:-1]]
    return Part.Face(Part.makePolygon([*points, points[0]]))


def wing_skin():
    faces = []
    first = last = None
    for row, (a, b) in enumerate(zip(COURSES, COURSES[1:])):
        profiles = [_profile(a, row, row), _profile(a+COURSE_HALF_WIDTH, row),
                    _profile(b-COURSE_HALF_WIDTH, row), _profile(b, row, row+1)]
        if first is None:
            first = profiles[0]
        for sect_a, sect_b in zip(profiles, profiles[1:]):
            for track_a, track_b in zip(sect_a, sect_b):
                faces.extend(_tiles(track_a, track_b))
        last = profiles[-1]
    root = _cap(first)
    shell = Part.makeShell([*faces, root, _cap(last)])
    shell.sewShape(.00002)
    solid = Part.makeSolid(shell.Shells[0])
    if solid.Volume < 0:
        solid.reverse()
    # Match the negative of the indrawn hull chine; keep the keys in the
    # original load-bearing wall, above the belly/undercarriage envelope.
    flank = shell_blank([mid(72.), mid(210.)])
    flank.translate(V(0., .06, 0.))
    root_return = root.extrude(V(0., -2.5, 0.)).cut(flank)
    solid = solid.fuse(root_return)
    _, te, _, flap, _ = section(DIVISION)
    start = te-flap+.62
    slot = Part.makeBox(te-start+2., .74, 22., V(start, DIVISION-.37, 0.))
    return solid.cut(slot)


def paint(x, y, z):
    y = abs(y)
    le, te, t, flap, lip = section(y)
    base, scale = _mount(y)
    t *= scale
    spar = te-flap
    lip = min(lip, .40*(spar-le))
    q = (x-le)/(te-le)
    row = min(len(COURSES)-2, max(0, bisect_right(COURSES, y)-1))
    boundary = row if y-COURSES[row] < COURSES[row+1]-y else row+1
    edge_dist = abs(y-COURSES[boundary])
    lower = z < base+(1.-q)*.4*t+q*(.16*t+1.-.60*max(0., min(1., (y-DIVISION)/6.)))
    shoe_x = le+min(1.24*lip, .5*(spar-le))
    if x < (shoe_x if lower else le+lip):
        if 0 < boundary < len(COURSES)-1 and boundary%2 == 0 and edge_dist < .14 and x > le+.10:
            return '#72736e'
        return ('#383b3c', CARBON, '#343b3e', '#323539')[(row//2)%4]
    if x >= te-.48:
        return CARBON
    if lower:
        if x >= spar-.27:
            f = (x-spar)/(te-spar)
            if boundary in ELEVON_STAMPS and edge_dist < .12 and .22 < f < .83:
                return '#626563'
            return '#343839'
        # The lower skin's quadratic section has linear chord abscissa.
        # Sample its actual cut depth: the pale finish is down inside the
        # grooves, not an independently drawn checker pattern on the lands.
        f = (x-shoe_x)/(spar-.27-shoe_x)
        land_z = base+t*(.10*(1.-f)**2-.08*f*(1.-f)+.075*f*f)
        if z-land_z > .115:
            return '#656967'
        column = math.floor((x-shoe_x)/BELLY_PITCH-.25-.5*(row%2))
        return BELLY_LANDS[(row*11+column*7+(row*column)%17)%len(BELLY_LANDS)]
    if spar-min(1.55, .26*(spar-le-lip)) <= x <= spar+.60:
        return JOINT
    if x >= spar:
        return '#e5e5df' if y < DIVISION else '#e9e9e2'
    return PORCELAIN
