"""Engraved, staggered heat-shield courses wrapped around the miniature's belly.

Rows follow distance around the outer chine, not a grid projected in plan. The
pitch is a print interpretation of the visible tile field, not a serial tile map.
Two cutter families terminate inside each other's grooves at different depths.
The surface between grooves is the original skin. Millimetres in the CAD frame.
"""
import math

import Part

from sections import V, box, poly

COURSE = 1.85
PITCH = 2.10
DEPTH = .155
MOUTH = .20


def _chin(t):
    # Same keel and lower cubic as sections.frame(mid(x)) for x >= 72.
    s = 1. - t
    y = 7.40*s**3 + 3*14.4*s*s*t + 3*20*s*t*t + 20*t**3
    z = 3*1.82*s*t*t + 6.5*t**3
    return y, z


def _perimeter():
    half = [_chin(i/96) for i in range(97)]
    pts = [(-y, z) for y, z in reversed(half)] + half
    arc = [0.]
    for (u, v), (y, z) in zip(pts, pts[1:]):
        arc.append(arc[-1] + math.hypot(y-u, z-v))
    return pts, arc


_CONTOUR, _ARC = _perimeter()


def _surface_point(u, depth):
    from bisect import bisect_right
    i = min(len(_ARC)-2, max(0, bisect_right(_ARC, u)-1))
    a, b = _CONTOUR[i:i+2]
    length = _ARC[i+1] - _ARC[i]
    t = (u - _ARC[i]) / length
    dy, dz = (b[0]-a[0])/length, (b[1]-a[1])/length
    return a[0]+t*(b[0]-a[0])-depth*dz, a[1]+t*(b[1]-a[1])+depth*dy


def engravers(x0, x1):
    """Two disjoint families. The parent surface itself remains the tile land."""
    extent = _ARC[-1]
    rows = round(extent / COURSE)
    step = extent / rows
    perimeter, cross = [], []

    def blade(x, width, rim):
        section = poly([V(x, *_surface_point(u, depth)) for u, depth in rim])
        return Part.Face(section).extrude(V(width, 0, 0))

    # Deep narrow floors ensure that the next set of shallow knives ends in
    # air at each T-junction. Sidewalls are tapered to hold a wash after paint.
    for j in range(1, rows):
        u = j * step
        rim = [(u-.12, -.28), (u-.09, .036), (u-.036, .218),
               (u+.036, .218), (u+.09, .036), (u+.12, -.28)]
        perimeter.append(blade(x0-.22, x1-x0+.44, rim))
    for j in range(rows):
        u, v = j*step, (j+1)*step
        us = [u, u+step*.25, u+step*.50, u+step*.75, v]
        rim = [(s, DEPTH) for s in us] + [(s, -.23) for s in reversed(us)]
        shift = (j % 2) * PITCH / 2
        for i in range(math.ceil((x0-shift)/PITCH), math.ceil((x1-shift)/PITCH)):
            x = i*PITCH + shift
            if x0+.20 < x < x1-.20:
                cross.append(blade(x-MOUTH/2, MOUTH, rim))
    return Part.makeCompound(perimeter), Part.makeCompound(cross)


def skirt_height(x):
    return 6.50 if x < 219. else min(15.10, 6.50+math.floor((x-218.)/2.10)*1.30)


def skirt_tools(x0, x1):
    """Shallow joints on the staircase below the tail cheek (Perituss, 26)."""
    tools = []
    row = 1.30
    for side in (-1, 1):
        for j in range(7):
            z = 6.50+row*j
            start = max(x0, 218.+2.10*(j+1))
            end = min(x1, 235.18)
            if end-start < .25:
                continue
            def score(a,b,h,k):
                # The last collar tapers 0.2 mm on each side.
                def y(x):
                    return 20.-.20*min(1., max(0., (x-232.)/3.20))
                q = [(a,side*(y(a)-.14)), (b,side*(y(b)-.14)),
                     (b,side*(y(b)+.42)), (a,side*(y(a)+.42))]
                return Part.Face(poly([V(x,v,h) for x,v in q])).extrude(V(0,0,k))
            top = min(15.1,z+row)
            tools.append(score(start,end,z,.16))
            t = 218.+(j%2)*1.05
            for i in range(math.ceil((start-t)/2.1),math.ceil((end-t)/2.1)):
                a = t+i*2.1
                if a+.17 < end-.04:
                    tools.append(score(a,a+.17,z+.14,top-z-.11))
    return tools


def flap_tools():
    """Top and underside courses on the removable lower tail panel, not a decal."""
    stations = [(235.2,1.9,5.65), (246.6,2.15,4.25), (252.75,2.80,3.85)]
    def z_at(x, k):
        a,b = stations[:2] if x < stations[1][0] else stations[1:]
        return a[k]+(b[k]-a[k])*(x-a[0])/(b[0]-a[0])
    tools = []
    for k,sign in [(1,-1.),(2,1.)]:
        def score(x0,x1,y0,y1):
            xs = [x0] + ([246.6] if x0<246.59 and x1>246.61 else []) + [x1]
            border = [(x,z_at(x,k)+sign*.50) for x in xs]
            border += [(x,z_at(x,k)-sign*.115) for x in reversed(xs)]
            return Part.Face(poly([V(x,y0,z) for x,z in border])).extrude(V(0,y1-y0,0))
        for j in range(-7,8):
            y = j*1.90
            tools.append(score(236.0,252.55,y-.08,y+.08))
            for i in range(8):
                x = 236.95+i*2.04+(j%2)*1.02
                if x > 252.15:
                    continue
                tools.append(score(x-.08,x+.08,y+.065,min(14.82,y+1.845)))
    return tools
