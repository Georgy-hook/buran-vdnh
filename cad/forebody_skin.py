"""Lapped sheets around the BTS-001 cabin. Distances refer to the 1:144 print.

The Moscow close-ups show broad skins and a short sill apron, not open RCS
ports. The grouped courses and exaggerated laps interpret these for resin;
they are not a map of individual flight tiles. No image is used as a texture.
"""
from collections import defaultdict
from functools import lru_cache
import math

import Part

from sections import V, compound, poly

# Upper-panel coordinates are in plan, side-panel coordinates in elevation.
# Each bowed transverse edge uses two straight runs per half-width. Keep
# the abrupt full-height structural joint at X=26.96 and the old six-lid tray.
# x on centreline, x at mid-width, x at shoulder, half-width.
FORE = ((19.65, 20.05, 21.85, 13.90),
        (23.20, 23.75, 24.94, 14.95),
        (26.96, 26.96, 26.96, 15.65),
        (29.68, 30.70, 32.85, 16.41),
        (31.74, 34.46, 38.70, 17.22))
AFT = ((45.62, 46.12, 55.72, 16.70),
       (50.38, 51.95, 59.30, 17.10),
       (54.62, 55.93, 62.48, 17.45))
WHITE = ('#e9e8e2', '#e2e2de', '#eeede8', '#e5e5e0')
REVEAL = .29


def _edge(station, t):
    centre, mid, end, span = station
    u = abs(t)
    if u <= .50:
        x = centre + (mid-centre)*u*2
    else:
        x = mid + (end-mid)*(u*2-1)
    return x, t*span


def _inset(points, gap):
    """Positive gap on all sides; mitre in the drawing plane, in mm."""
    area = sum(a*d-b*c for (a,b), (c,d) in zip(points, points[1:] + points[:1]))
    normals = []
    for (x,y), (u,v) in zip(points, points[1:] + points[:1]):
        scale = math.copysign(1., area)/math.hypot(u-x,v-y)
        normals.append(((y-v)*scale,(u-x)*scale))
    outline = []
    for i,(x,y) in enumerate(points):
        (a,b), (c,d) = normals[i-1], normals[i]
        length = gap/(1+a*c+b*d)
        outline.append((x+(a+c)*length,y+(b+d)*length))
    return outline


def _course_rows(stations):
    for row,(front,aft) in enumerate(zip(stations, stations[1:])):
        # Short running joints in successive sheets meet a course, rather
        # than a full grid of crossing grooves: some straddle the centreline.
        ends = (-1., -.55, -.18, .18, .55, 1.) if row%2 == 0 else (-1., -.73, -.34, .34, .73, 1.)
        for col,(left,right) in enumerate(zip(ends, ends[1:])):
            stops = [left, *(i for i in (-.5,0.,.5) if left < i < right), right]
            points = [_edge(front,i) for i in stops] + [_edge(aft,i) for i in reversed(stops)]
            yield _inset(points, REVEAL/2), WHITE[(col+row*2)%4]


def _upper_drawings():
    # The forward six closed discs sit in a sheet by themselves, with a
    # surrounding pair of short, splayed cheek leaves. No checker over them.
    for side in (-1, 1):
        # Stretch the outside of each leaf around the flank, while its short
        # inboard edge still terminates against the rectangular roof tray.
        for x0,x1,out0,out1 in ((12.10,15.65,9.65,11.44),(15.93,19.42,11.48,13.45)):
            yield .21, [(x0,side*5.68),(x1,side*5.68),(x1+1.74,side*out1),
                        (x0+1.03,side*out0)], WHITE[0]
    for stations in (FORE,AFT):
        for pts, shade in _course_rows(stations):
            yield .25, pts, shade
    # Distinct, short flared apron at the sill; no material over the verified
    # glass planes or the white central post. Keep each joint as an open reveal.
    rails = (((33.93,0.), (37.62,8.99), (41.99,16.13), (51.59,17.43)),
             ((32.03,0.), (35.88,9.76), (40.67,17.53), (51.55,18.44)))
    for side in (-1,1):
        for i in range(3):
            inner, outer = rails
            pts = [inner[i], inner[i+1], outer[i+1], outer[i]]
            yield .39, [(x,y*side) for x,y in _inset(pts,.095)], '#dfdfd9'


# A narrow doubler crosses the black/white paint boundary. It is one sheet,
# not a staircase in the underlying structure (Popov 4543). Large hatch at its
# lower rear is also part black, part white; only the smaller insert is dark.
# Terminate against the sloping sheet, rather than just grazing the tiny
# horizontal lands on the painted sawtooth at stations 30–34.
WAIST = [(27.26,23.09),(38.75,26.68),(46.32,28.22),(56.75,27.53),
         (56.75,26.16),(46.52,26.50),(38.98,24.84),(27.26,21.31)]
CARRIER = [(11.95,18.49),(14.83,19.34),(22.12,20.60),(26.63,20.33),
           (26.63,10.43),(12.34,12.44)]
HATCH = [(44.95,23.89),(46.13,23.89),(47.60,23.03),(49.02,20.58),
         (49.02,18.77),(47.60,15.30),(45.58,15.30),(44.99,17.72)]


def _column(points, side):
    if side:
        start = [V(x,side*6,z) for x,z in points]
        axis = V(0,side*18,0)
    else:
        start = [V(x,y,16) for x,y in points]
        axis = V(0,0,32)
    return Part.Face(poly(start)).extrude(axis)


def _laminate(blank, panels, delta):
    # Clip the actual translated loft against all disjoint footprints at once.
    # These solids are united BEFORE coring the fuselage; there is no enclosed
    # air gap under a plate and no shell overlapping the finished inner wall.
    offset = blank.copy()
    offset.translate(delta)
    return offset.common(compound(panels))


def laminations(blank):
    heights = defaultdict(list)
    for height, outline, _ in _upper_drawings():
        heights[height].append(_column(outline,0))
    upper = [_laminate(blank,columns,V(0,0,dz)) for dz,columns in heights.items()]
    sides = []
    for side in (-1,1):
        sides.append(_laminate(blank, [_column(p,side) for p in (CARRIER, HATCH, WAIST)], V(0,side*.28,0)))
    return upper, sides


def _contains(points, x, y):
    inside = False
    for (u,v),(s,t) in zip(points,points[1:]+points[:1]):
        if (v>y) != (t>y) and x < (s-u)*(y-v)/(t-v)+u:
            inside = not inside
    return inside


@lru_cache(maxsize=1)
def _palette():
    # One small bucket per integer station; consulted also by the native BRep
    # painter, so exclude the belly/core explicitly in the public callback.
    bins = defaultdict(list)
    for _, outline, shade in _upper_drawings():
        xs,ys = zip(*outline)
        bounds = (min(xs),max(xs),min(ys),max(ys))
        for i in range(int(bounds[0]), int(bounds[1])+1):
            bins[i].append((bounds,outline,shade))
    return bins


def panel_color(x,y,z,dark):
    if not dark and z > max(18., min(29., .42*x+14.)):
        for (x0,x1,y0,y1),points,shade in _palette().get(int(x), ()):
            if x0 <= x <= x1 and y0 <= y <= y1 and _contains(points,x,y):
                return shade
    if abs(y) > 8. and 10. < z < 28.25:
        if _contains(CARRIER,x,z) or _contains(HATCH,x,z):
            return '#41474b' if dark else '#dfdfdb'
        if _contains(WAIST,x,z):
            return '#41484c' if dark else '#deded9'
    return None
