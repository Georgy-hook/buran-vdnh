"""Exterior covers of the Moscow display. All recesses have integral blind floors.

K. Popov 4541–43 resolves the plate in front of the paired lids and the paired /
large / large / paired grouping. Commons 25051381498 resolves both roof rows.
The step heights are modelling allowances, not dimensions of flight hardware.
"""
import Part

from sections import V, bezier

TIP_Y = 5.56
TIP_Z = 4.35
TIP_CENTRE_Z = 11.12
ROOF_LID = '#e4e4de'

# Along the side: front rounded rectangle, six lids, small trailing lid,
# elongated secondary covers below the panel, and the mask/white hatch overlap.
# x, z, half axes, shoulder fullness, shade
SIDE = (
    (10.4, 15.15, 1.48, 1.92, .85, '#444a50'),
    (14.25, 17.28, 1.28, 1.37, .55, '#42484e'),
    (14.36, 14.32, 1.28, 1.37, .55, '#41474d'),
    (17.70, 15.82, 1.70, 2.78, .55, '#41474d'),
    (21.48, 15.96, 1.63, 2.80, .55, '#41474d'),
    (24.76, 17.55, 1.32, 1.40, .55, '#41474d'),
    (24.94, 14.36, 1.32, 1.43, .55, '#41474d'),
    (28.93, 15.93, 1.34, 1.48, .55, '#40464b'),
    (18.84, 11.78, .95, .50, .79, '#43494d'),
    (25.92, 11.04, .47, .91, .77, '#43494d'),
)


def _unit(a):
    return a * (1. / a.Length)


def _oval(c, a, b, k):
    # Cubics allow an oval or a nearly rectangular inspection lid without
    # singular corners. a and b are 3D half-axis vectors in the lid plane.
    return Part.Wire([bezier(c+p, c+p+k*q, c+q+k*p, c+q)
                      for p, q in ((a,b), (b,-a), (-a,-b), (-b,a))])


def tip_cap(blank):
    """Small oval cup, joined across its entire back, not a disconnected part.

    Front views 00/04 distinguish the lip from the much larger black radome.
    On 4541 its lower edge sits aft of the upper edge. Intersecting an oval
    with the real asymmetric loft keeps both the front outline and that rake.
    """
    def envelope(extra):
        wire = _oval(V(-2, 0, TIP_CENTRE_Z), V(0, TIP_Y + extra, 0),
                     V(0, 0, TIP_Z + extra), .55228475)
        return Part.Face(wire).extrude(V(10, 0, 0))

    rim = envelope(0)
    cup = rim.common(blank)
    cup.translate(V(-.28, 0, 0))
    floor = blank.copy()
    floor.translate(V(.30, 0, 0))
    groove = envelope(.25).cut(rim).cut(floor)
    return cup, groove


def tip_color(x, y, z):
    if x >= 7.8:
        return None
    h = z - TIP_CENTRE_Z
    if (y/TIP_Y)**2 + (h/TIP_Z)**2 <= 1.002:
        return '#292d32'
    if (y/(TIP_Y+.25))**2 + (h/(TIP_Z+.25))**2 < 1.:
        return '#232629'
    return None


def covers(blank):
    tools, materials = [], []

    def make(point, u, v, n, a, b, fullness, color, depth):
        # A flat lid sits below the curved, changing contour, with an annular
        # rebate one step deeper than the lid. Both are one blind subtraction.
        rebate = .16 if color == ROOF_LID else .24
        lip = .22 if color == ROOF_LID else min(.29, a*.31, b*.31)
        c = point - n*depth
        outer = Part.Face(_oval(c-n*rebate, u*a, v*b, fullness))
        inner = Part.Face(_oval(c-n*rebate, u*(a-lip), v*(b-lip), fullness))
        rim = outer.cut(inner).extrude(n*2.8)
        cap = Part.Face(_oval(c, u*a, v*b, fullness)).extrude(n*2.8)
        tools.append(cap.fuse(rim).removeSplitter())
        materials.append((c, n, u, v, a, b, color, rebate))

    def ray(x, t, surface, side=1):
        # Work only from intersections on the exact exterior loft.
        if surface == 'roof':
            probe = Part.makeLine(V(x,t,50), V(x,t,1))
            return max((v.Point for v in blank.section(probe).Vertexes), key=lambda p:p.z)
        probe = Part.makeLine(V(x,side*24,t), V(x,0,t))
        return max((v.Point for v in blank.section(probe).Vertexes), key=lambda p:abs(p.y))

    def tangent(x, t, surf, sign):
        p = ray(x,t,surf,sign)
        u = _unit(ray(x+.08,t,surf,sign)-ray(x-.08,t,surf,sign))
        w = ray(x,t+.08,surf,sign)-ray(x,t-.08,surf,sign)
        v = _unit(w-u*w.dot(u))
        n = u.cross(v)
        if (n.z if surf=='roof' else sign*n.y) < 0:
            n = -n
        return p, u, v, n

    for side in (-1, 1):
        for x,z,a,b,k,shade in SIDE:
            make(*tangent(x,z,'side',side), a,b,k,shade,.23)
        # Only the little round field is dark. The much larger service panel
        # straddles the abrupt colour change; it is not a large black hole.
        make(*tangent(46.40,19.90,'side',side), 1.69,1.77,.55,'#383d41',.22)
    # The two rows of three are closed lids on the white museum skin.
    # Each lies on its own locally tilted tangent plane.
    for x in (10.6, 17.0):
        for y in (-3.43, 0., 3.43):
            make(*tangent(x,y,'roof',1), 1.53,1.52,.55,ROOF_LID,.14)
    return tools, materials


def cover_color(materials, point):
    for c, n, u, v, a, b, color, rebate in materials:
        d = point-c
        if abs(d.x)>a+1 or abs(d.z)>max(b,2.6)+1 or abs(d.y)>b+1:
            continue
        if abs(d.dot(u)) > a+.04 or abs(d.dot(v)) > b+.04:
            continue
        h = d.dot(n)
        if abs(h) < .013:
            # The museum lids are nearly flush against the surrounding mask.
            return color
        if abs(h+rebate) < .015:
            return '#aaa9a3' if color == ROOF_LID else '#676d70'
    return None
