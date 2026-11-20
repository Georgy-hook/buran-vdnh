"""Blind, conforming scores on the fixed fin. Comparable creases can be seen
on both the Moscow close views and the broad port cheek in the 2013 park view.
Widths/depths are enlarged to survive washing a 1:144 resin miniature.
"""
import Part
from FreeCAD import Vector as V


def _plate(points):
    points = [V(x, 0., z) for x, z in points]
    return Part.Face(Part.makePolygon([*points, points[0]]))


def _rim(x, z, width, height, sweep, stroke):
    # Make the inner and outer loops in the SAME skew coordinates. Scaling
    # two independent axis-aligned bounds can invert a narrow diagonal rim.
    def loop(d):
        f = min(.33, (width-2.*d)*.23)
        l, r, b, t = d, width-d, d, height-d
        profile = ((l+f, b), (r-f, b), (r, b+f), (r, t-f), (r-f, t),
                   (l+f, t), (l, t-f), (l, b+f))
        return _plate([(x+u+sweep*h, z+h) for u, h in profile])
    return loop(0.).cut(loop(stroke))


def score(skin, leading):
    # Fold at the back of the leading-edge cover. Its sweep straightens
    # progressively as it rises out of the curved root, as on the exterior.
    stations = (41.45, 44.10, 47.65, 49.75, 51.20, 54., 87.70, 92.25)
    track = [(leading(z)+3.45, z) for z in stations]
    strip = _plate([*track, *((x+.31, z) for x, z in reversed(track))])
    panels = [strip, _rim(197.20, 42.22, 1.15, 5.92, .51, .24),
              _rim(211.85, 42.37, 6.80, 7.13, .80, .31)]
    for z in (54.85, 74.45, 91.25):
        a = leading(z)+1.26
        panels.append(_plate([(a, z), (a+2.17, z), (a+2.40, z+.24), (a+.23, z+.24)]))
    cuts = []
    for side in (-1, 1):
        # Leave an identical, full second airfoil translated .17 mm inboard
        # as the hard cutting stop: no flat-bottomed divots on a convex skin.
        limit = skin.copy()
        limit.translate(V(0., -.17*side, 0.))
        cuts.extend(p.extrude(V(0., 8.*side, 0.)).cut(limit) for p in panels)
    return skin.cut(cuts, 1.e-7)
