"""Exterior-only representation of the side fairings visible beside the museum gallery.

Based on the paired side and underside views in K. Popov, frames 4537 / 4548.
All the circles and stripes are blind surface impressions, not working openings.
"""

import Part

from sections import V, cut, poly


STATIONS = [
    # x, outboard face Y, lower inside edge, lower outer edge, crown
    (198.1, 19.30, 26.25, 27.05, 28.62),
    (201.0, 20.25, 25.84, 26.63, 29.84),
    (207.6, 22.45, 24.63, 25.90, 31.53),
    (214.4, 24.52, 23.54, 25.18, 32.90),
    (217.0, 24.75, 23.50, 25.14, 33.18),
    (233.2, 24.75, 23.80, 25.34, 33.32),
    (234.6, 24.48, 24.15, 25.62, 32.92),
]
SIDE_MARKS = (217.65, 222.15, 226.65, 231.15)


def relief_cup(centre, direction, radius, depth):
    # Convex bevel at each rim catches a highlight after a thin primer coat.
    lip = Part.makeCone(radius+.16, radius, .33, centre, direction)
    dish = Part.makeCylinder(radius, depth, centre+.30*direction, direction)
    return lip.fuse(dish)


def shoulder(side):
    def section(x, y, bottom, chine, top):
        points = [(17.45,bottom), (20.30 if y>21 else 18.10,bottom+.06),
                  (y-.30,chine-.16), (y,chine+.22), (y,top-.54),
                  (y-.21,top-.18), (y-.59,top), (17.45,top-.10)]
        return poly([V(x,side*a,b) for a,b in points])

    body = Part.makeLoft([section(*s) for s in STATIONS], True, True)
    marks = [relief_cup(V(x,side*25.03,29.60), V(0,-side,0), 1.23, .93)
             for x in SIDE_MARKS]
    marks.extend(relief_cup(V(234.93,side*y,z), V(-1,0,0), .91,.92)
                 for y,z in ((21.42,27.25),(21.96,30.19)))
    # A separate dark bevel can be seen from below. Keep it joined to the solid.
    marks.extend(relief_cup(V(x,side*22.65,23.68), V(0,-side*.28,.96), .94, 1.13)
                 for x in SIDE_MARKS)
    # Perituss (_26, VDNKh): a framed five-blade vent, and a large flush
    # circular field farther aft on the sloping cheek. Not a row of engines.
    def plane_y(x):
        return 20.25 + (x-201.) * (2.20/6.60)

    def slot(x0, x1, z, height, depth):
        pts = [(x0,plane_y(x0)-depth), (x1,plane_y(x1)-depth),
               (x1,plane_y(x1)+.70), (x0,plane_y(x0)+.70)]
        return Part.Face(poly([V(x,side*y,z) for x,y in pts])).extrude(V(0,0,height))

    for z in (26.70, 27.18, 27.66, 28.14, 28.62):
        marks.append(slot(202.45,207.20,z,.24,.32))
    marks.extend([slot(202.1,202.32,26.55,2.68,.24),slot(207.33,207.55,26.55,2.68,.24)])
    normal = V(.314, -side*.949, 0)
    for x, z, radius in ((211.8,30.54,1.22), (209.4,27.1,.43)):
        y = 22.45 + (x-207.6)*(24.52-22.45)/(214.4-207.6)
        start = V(x,side*y,z)-normal*.22
        rim = Part.makeCylinder(radius,.47,start,normal).cut(Part.makeCylinder(radius-.15,.5,start,normal))
        marks.append(rim)
    return cut(body,marks)


def color(x,y,z):
    v = abs(y)
    if x > 216.1 and v > 20.5:
        if 23.45 < z < 25.50 and x < 234.72:
            return '#43484c'
        if v > 23.2 and 27.8 < z < 31.25:
            if any((x-u)**2+(z-29.60)**2 < 1.25**2 for u in SIDE_MARKS):
                return '#2c3033'
        if x > 233.46 and any((v-a)**2+(z-b)**2 < .96**2 for a,b in ((21.42,27.25),(21.96,30.19))):
            return '#2c3033'
    if 202.42 < x < 207.25 and v > 20.20:
        if any(a-.015 < z < a+.255 for a in (26.70,27.18,27.66,28.14,28.62)):
            return '#565c60'
    return None
