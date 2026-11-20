"""The back of the Moscow display before its transfer, reconstructed in scale.

The modern VDNKh walkway hides this face. The July 2014 dismantling photo
(`demontage TVA 2`, Buran-Energia) and Commons `Moscow OK-TVA 2013-01 98`
show the two lower open-faced dummies, the oval boss and the blunt upper pod.
All impressions are blind. Nothing here represents an internal engine.
"""

import math
from bisect import bisect_right

import FreeCAD as App
import Part

from sections import V, bezier, cut, fuse, poly


BASE = 235.2
MOUTHS = (-9.35, 9.35)
MOUTH_Z = 13.05
GRAPHITE = '#33383b'
BUCKET = '#292e30'
OXIDE = '#713c39'


def _shield(x, half, keel, crown):
    """Broad lower cheeks, narrower curved head; the aft-most face is flat."""
    height = crown - keel

    def p(y, z):
        return V(x, half*y, keel+height*z)

    def flank(s):
        return [bezier(p(.66*s, 0), p(.84*s, 0), p(s, .18), p(s, .40)),
                bezier(p(s, .40), p(s, .63), p(.81*s, .91), p(.54*s, .96)),
                bezier(p(.54*s, .96), p(.39*s, 1.), p(.17*s, 1.), p(0., 1.))]

    other = flank(-1)
    for edge in other:
        edge.reverse()
    return Part.Wire([Part.makeLine(p(-.66, 0), p(.66, 0)), *flank(1), *reversed(other)])


def _turn(y, z, profile):
    wire = poly([V(x, y+r, z) for x, r in profile])
    return Part.Face(wire).revolve(V(0, y, z), V(1, 0, 0), 360.)


LINER = (((236.78,0.), (236.78,1.35), (237.60,2.94), (239.03,3.50)),
         ((239.03,3.50), (240.71,4.16), (242.43,4.74), (243.56,5.06)))


def _lathe(y, z, runs):
    edges = []
    for run in runs:
        points = [V(x,y+r,z) for x,r in run]
        edges.append(Part.makeLine(*points) if len(points)==2 else bezier(*points))
    return Part.Face(Part.Wire(edges)).revolve(V(0,y,z), V(1,0,0), 360.)


def _cup(y):
    # The archive shows a continuous, dark red sheet returning into shadow,
    # not a stack of rings. The scale part has a round, washable blind floor.
    return _lathe(y, MOUTH_Z, [((235.55,0.), (235.55,4.58)),
                  ((235.55,4.58), (238.37,4.30), (240.51,4.68), (243.24,5.43)),
                  ((243.24,5.43), (243.59,5.52), (243.78,5.32), (243.56,5.06)),
                  tuple(reversed(LINER[1])), tuple(reversed(LINER[0])),
                  ((236.78,0.), (235.55,0.))])


def _liner_section():
    points = []
    for run in LINER:
        for i in range(65):
            if points and i==0:
                continue
            t = i/64
            s = 1.-t
            weights = (s**3, 3*s*s*t, 3*s*t*t, t**3)
            points.append(tuple(sum(w*p for w,p in zip(weights,axis)) for axis in zip(*run)))
    return points


INNER = _liner_section()
RADII = [r for x,r in INNER]


def _on_liner(x, r):
    if r > RADII[-1]+.04:
        return False
    i = min(len(INNER)-2, max(0,bisect_right(RADII,r)-1))
    (a,b), (c,d) = INNER[i:i+2]
    return abs(x-a-(c-a)*(r-b)/(d-b)) < .21


def _dome():
    skin = _lathe(0., 0., [((238.56,0.), (238.56,9.04)),
                 ((238.56,9.04), (239.21,9.02), (239.46,8.91), (239.59,8.08)),
                 ((239.59,8.08), (239.83,6.53), (242.71,6.14), (242.71,0.)),
                 ((242.71,0.), (238.56,0.))])
    m = App.Matrix()
    m.A33, m.A34 = .632, 26.15
    dome = skin.transformGeometry(m)
    # Two small flush fastener impressions resolve in the pre-move close-up.
    seats = [Part.makeCylinder(.34, .49, V(242.75, y, 26.8), V(-1, 0, 0))
             for y in (-2.15, 2.15)]
    return cut(dome, seats)


def _upper_pod():
    return _turn(0., 36.57, [(234.35, 0.), (234.35, 3.18), (235.91, 3.18),
                             (236.20, 2.94), (237.17, 2.94), (237.34, 2.73),
                             (237.64, 2.73), (237.82, 2.89), (242.45, 2.88),
                             (245.08, 2.64), (245.91, 2.26), (246.55, 1.59),
                             (246.85, .72), (246.88, 0.)])


def _badge():
    # Inverted three-sided pressed field above the twin openings.
    points = [(-4.95, 21.7), (4.95, 21.7), (0., 15.9)]
    outer = Part.Face(poly([V(239.31, y, z) for y, z in points]))
    inner = Part.Face(poly([V(239.31, y*.90, 19.76+(z-19.76)*.90)
                            for y, z in points]))
    return outer.cut(inner).extrude(V(1.54, 0., 0.))


def restore(base):
    shield = Part.makeLoft([_shield(234.56, 18.58, 5.84, 33.90),
                            _shield(236.26, 18.12, 6.20, 33.24),
                            _shield(238.08, 17.27, 6.72, 32.66),
                            _shield(239.55, 15.53, 7.13, 31.72)], True, True)
    hollows = [Part.makeCone(6.52, 8.34, 5.8, V(236.28, y, MOUTH_Z), V(1, 0, 0))
               for y in MOUTHS]
    body = cut(fuse(base, [shield]), [*hollows, _badge()])
    return fuse(body, [_cup(y) for y in MOUTHS] + [_dome(), _upper_pod()])


def paint(x, y, z):
    if x < BASE-.04:
        return None
    if z > 33.2 and x > BASE+.15:
        return '#303537' if 237.24 < x < 237.76 else '#424648'
    for cy in MOUTHS:
        r = math.hypot(y-cy, z-MOUTH_Z)
        if x >= 236.63 and r < 5.65:
            if _on_liner(x,r):
                return OXIDE
            return '#4b4341' if x > 243.39 else BUCKET
        if x > 236.14 and r < 8.03:
            return '#252a2d'
    if x > 239.57 and 20.8 < z < 31.7:
        return '#373b3d'
    return GRAPHITE
