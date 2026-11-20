"""Scale relief of the fixed flank below the payload doors. Dimensions in mm.

The museum close-ups resolve broad butt-jointed sheets and a few distinct
access lids, not rows of raised rivets across the entire white fuselage.
Keep the wing seating land, the name and the flag free of blind pockets.
"""

import Part

from sections import V, box, cut


LIDS = (
    (79.6, 15.0, 4.5, 4.1), (85.6, 15.0, 4.5, 4.1),
    (146.8, 16.5, 3.5, 1.35), (186.8, 19.1, 3.15, 1.32),
    (190.9, 15.9, 3.25, 1.45), (205.2, 18.4, 5.0, 2.0),
    (220.4, 13.0, 4.2, 6.6),
)
SLOTS = (105.1, 139.7)


def _outline(x, z, w, h, side, level, inset):
    a, b = x+inset, x+w-inset
    c, d = z+inset, z+h-inset
    r = min(.81, (d-c)*.34, (b-a)*.34)
    k = .70710678

    def p(u, v):
        return V(u, side*(20.+level), v)

    pts = [p(a+r,c), p(b-r,c), p(b,c+r), p(b,d-r),
           p(b-r,d), p(a+r,d), p(a,d-r), p(a,c+r)]
    mids = [p(b-r+r*k,c+r-r*k), p(b-r+r*k,d-r+r*k),
            p(a+r-r*k,d-r+r*k), p(a+r-r*k,c+r-r*k)]
    edges = []
    for j, m in enumerate(mids):
        i = 2*j
        edges.append(Part.makeLine(pts[i], pts[i+1]))
        edges.append(Part.Arc(pts[i+1], m, pts[(i+2)%8]).toShape())
    return Part.Wire(edges)


def lids(x0, x1):
    pieces = []
    for x,z,w,h in LIDS:
        if not x0 < x < x1-w:
            continue
        for side in (-1, 1):
            lip = Part.makeLoft([_outline(x,z,w,h,side,level,margin)
                                 for level,margin in ((-.11,.30), (.13,.33), (.235,.48))],
                                True, True)
            holes = []
            if h>2.8:
                for u in (x+.90, x+w-.90):
                    for v in (z+.90, z+h-.90):
                        holes.append(Part.makeCylinder(.144, .21, V(u,side*20.29,v), V(0,-side,0)))
            if x==220.4:
                ctr = V(x+w*.50,side*20.28,z+h*.52)
                axis = V(0,-side,0)
                holes.append(Part.makeCylinder(.82,.20,ctr,axis).cut(Part.makeCylinder(.64,.22,ctr,axis)))
            pieces.append(cut(lip,holes) if holes else lip)
    return pieces


def seams(x0, x1):
    knives = []
    for side in (-1, 1):
        sy = 19.84 if side>0 else -20.34

        def score(a,b,z,h):
            a, b = max(x0,a), min(x1,b)
            if b>a:
                knives.append(box(a,sy,z,b-a,.5,h))

        # The sill walks upward aft of the flag. Avoid the wing seat at Z7.12.
        for a,b,z in ((72,87.91,10.12), (87.91,142.60,9.66), (142.60,198.4,9.29),
                      (198.4,218.31,10.60), (218.31,232.,12.17)):
            score(a,b,z,.19)
        for x, low, high in ((77.12,10.12,25.30), (92.75,9.66,25.30),
                             (109.92,9.66,25.30), (129.84,9.66,25.30),
                             (147.25,9.66,15.83), (157.15,9.29,25.30),
                             (162.17,9.29,25.30), (188.10,9.29,18.56),
                             (198.40,9.29,25.30), (209.47,10.60,18.06),
                             (218.31,10.60,23.30), (227.86,12.17,21.30)):
            score(x,x+.17,low,high-low)
        # Only two dark, oblong fields read in the nose-left profile. Both
        # have a blind, recessed floor; the opposite side carries pale lids.
        for x in SLOTS:
            if x0 < x and x+4.3 < x1:
                rim = _outline(x,20.5,4.3,1.7,side,.33,.26)
                knives.append(Part.Face(rim).extrude(V(0,-side*.65,0)))
    return knives


def color(x, y, z):
    w = abs(y)
    if w>19.55 and 20.65<z<22.02 and any(a+.21<x<a+4.09 for a in SLOTS):
        if w<19.80:
            return '#33383a' if y<0 else '#b8bcb9'
    if 19.77<w<19.91 and 8.96<z<25.45:
        return '#afb2ad'
    if 20.05<w<20.25 and any(a<x<a+b and c<z<c+d for a,c,b,d in LIDS):
        return '#daded7' if w<20.17 else '#e6e7df'
    return None
