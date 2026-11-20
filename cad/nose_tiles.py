"""Staggered thermal-surface courses, engraved into the actual loft (not a texture).

The museum sheet-metal lid panel and smooth cap remain uninterrupted. The
pitch/depth below are deliberately printable, not claimed individual tile IDs.
"""
from bisect import bisect_left
from functools import lru_cache
import math

import FreeCAD as App
import Part

from sections import V, box, compound, poly
from skin import belt_z

PITCH = 3.35
WIDTH = .23
DEPTH = .22
# Keep a positive step at T junctions. Equal-depth ruled floors can graze
# the curved course bottom and produce an untriangulable microface.
COURSE_DEPTH = .36


def _ceiling(x):
    # The closed cheek plate, cap shell and service hatch are sheet surfaces,
    # not patches on which to emboss the same tile pattern indiscriminately.
    if x < 30.8:
        return min(belt_z(x)-.48, 9.68)
    if 43.0 < x < 49.5:
        return min(belt_z(x)-.48, 12.4)
    return belt_z(x)-.48


def tile_tools(blank):
    sides = [f for f in blank.Faces if isinstance(f.Surface, Part.BSplineSurface)]
    surfaces = [(f.Surface, *f.ParameterRange[:2]) for f in sides]
    first = sides[0].Surface

    @lru_cache(None)
    def parameter(x):
        lo, hi = 0., 1.
        for _ in range(35):
            mid = (lo+hi)*.5
            if first.value(0., mid).x < x:
                lo = mid
            else:
                hi = mid
        return (lo+hi)*.5

    def contour(x):
        t = parameter(x)
        wire = Part.Wire([s.vIso(t).toShape(a,b) for s,a,b in surfaces])
        return Part.Face(wire)

    @lru_cache(None)
    def polar(x):
        t = parameter(x)
        # The exact loft may be several tenths away from a linear table
        # interpolation, enough to swallow a seam. Sample its actual YZ frame.
        pts = [s.value(a+(b-a)*i/30, t) for s,a,b in surfaces for i in range(30)]
        cz = .5*(max(p.z for p in pts) + min(p.z for p in pts))
        data = sorted((math.atan2(p.y,cz-p.z),math.hypot(p.y,p.z-cz)) for p in pts)
        angles = [v[0] for v in data]
        radii = [v[1] for v in data]
        return cz, angles, radii

    def corner(x, angle):
        cz, aa, rr = polar(x)
        i = bisect_left(aa, angle)
        a,b = aa[i-1],aa[i]
        r = rr[i-1] + (rr[i]-rr[i-1])*(angle-a)/(b-a)
        sn, cs = math.sin(angle), math.cos(angle)
        return V(x,r*sn,cz-r*cs), V(0,sn,-cs), V(0,cs,sn)

    # Cross courses are thin annuli from true isoparametric frames. They
    # stay open at the colour line and never run across the white fuselage.
    marks = [7.85 + i*PITCH for i in range(20)]
    rings = []
    for x in marks:
        floor = contour(x)
        bb = floor.BoundBox
        sz = 1.-2*COURSE_DEPTH/bb.ZLength
        sy = 1.-2*COURSE_DEPTH/bb.YLength
        m = App.Matrix()
        m.A22, m.A33 = sy, sz
        m.A14 = -WIDTH*.70
        m.A34 = (bb.ZMin+bb.ZMax)*.5*(1.-sz)
        inner = floor.transformGeometry(m).extrude(V(WIDTH*1.4,0,0))
        block = box(x-WIDTH*.5,-23,-2,WIDTH,46,_ceiling(x)+2)
        rings.append(block.cut(inner))

    # The longitudinal joints butt into the cross courses. Alternate rows
    # have a half-cell offset. Their blind floors follow the chine and keel,
    # instead of being flat XY or XZ cuts through a rounded solid.
    joints = []
    for row, (x0,x1) in enumerate(zip(marks, marks[1:]+[71.96])):
        if x1 <= x0:
            continue
        step = math.radians(12.0)
        for j in range(-13,14):
            angle = (j + (row%2)*.5)*step
            c0,n0,h0 = corner(x0,angle)
            c1,n1,h1 = corner(x1,angle)
            if c0.z+WIDTH > _ceiling(x0) or c1.z+WIDTH > _ceiling(x1):
                continue
            def edge(c,n,h):
                return poly([c+n*d+h*w for d,w in ((-DEPTH,-WIDTH/2),
                            (.78,-WIDTH/2),(.78,WIDTH/2),(-DEPTH,WIDTH/2))])
            joints.append(Part.makeLoft([edge(c0,n0,h0),edge(c1,n1,h1)],True,True))
    return compound(rings), compound(joints)
