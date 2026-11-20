"""Exterior-only representation of the side fairings visible beside the museum gallery.

Based on the paired side and underside views in K. Popov, frames 4537 / 4548.
All the circles and stripes are blind surface impressions, not working openings.
"""

import Part

from sections import V, box, cut, poly


STATIONS = [
    # x, outboard face Y, lower inside edge, lower outer edge, crown
    (197.7, 19.32, 26.18, 26.75, 28.66),
    (201.0, 20.25, 25.54, 26.28, 29.86),
    (207.6, 22.45, 23.72, 25.47, 31.98),
    (213.4, 24.30, 22.72, 25.04, 33.43),
    (217.0, 25.72, 21.90, 24.82, 34.35),
    (219.5, 26.54, 21.62, 24.78, 34.56),
    (239.8, 26.54, 21.62, 24.78, 34.56),
    (241.2, 26.38, 21.84, 24.98, 34.30),
]
SIDE_MARKS = (221.40, 227.15, 232.90, 238.65)
END_MARKS = ((22.44, 26.47), (20.72, 30.99))


def _underside(y):
    # Inclined face below the last box, as seen from below on Popov 4548.
    return 21.70+(abs(y)-19.03)*.421


def relief_cup(centre, direction, radius, depth):
    # Convex bevel at each rim catches a highlight after a thin primer coat.
    lip = Part.makeCone(radius+.16, radius, .33, centre, direction)
    dish = Part.makeCylinder(radius, depth, centre+.30*direction, direction)
    return lip.fuse(dish)


def shoulder(side):
    def section(x, y, bottom, chine, top):
        inboard = 17.38 if x<228. else 17.38+min(1.55,(x-228.)*.17)
        skew = min(1., max(0., (x-218.)/19.0))
        foot = inboard+1.21*skew
        head = inboard-1.94*skew
        knee = min(y-.70, foot+1.58)
        points = [(foot,bottom), (knee,bottom+.08),
                  (y-.30,chine-.17), (y,chine+.20), (y,top-.58),
                  (y-.21-.57*skew,top-.18), (y-.64-1.30*skew,top), (head,top-.12)]
        return poly([V(x,side*a,b) for a,b in points])

    body = Part.makeLoft([section(*s) for s in STATIONS], True, True)
    marks = [relief_cup(V(x,side*26.79,29.62), V(0,-side,0), 1.59, 1.96)
             for x in SIDE_MARKS]
    marks.extend(relief_cup(V(241.40,side*y,z), V(-1,0,0), 1.30,1.47)
                 for y,z in END_MARKS)
    # A row on the inclined plate is distinct from the horizontal side row.
    inward = V(0,-side*.388,.922)
    marks.extend(relief_cup(V(x,side*22.70,_underside(22.70))-inward*.61,
                            inward, 1.24, 1.70) for x in SIDE_MARKS)
    # Panel seams continue over the cap and around the corners; the front
    # wedge and the louvre stay unbroken. Dismantling photo, July 2014.
    for x in (219.87,225.0,230.12,235.74,240.58):
        marks.append(box(x-.085, -27.2 if side<0 else 18.7,
                         34.28, .17, 8.50, 1.10))
    start_y = 26.33 if side>0 else -27.1
    for x in (219.9,224.26,230.02,235.76):
        marks.append(box(x-.085,start_y,25.12,.17,.77,8.97))
    # The rear opening is a two-piece angled cheek, not a flat rectangle.
    marks.append(box(240.98, 21.55 if side>0 else -26.65,
                     28.38, .66, 5.1, .18))
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
    if x >= 216.4 and v > 18.75:
        if x > 239.57 and any((v-a)**2+(z-b)**2 < 1.53**2 for a,b in END_MARKS):
            return '#2d3032'
        if v>24.46 and any((x-u)**2+(z-29.62)**2 < 1.80**2 for u in SIDE_MARKS):
            return '#262b2d' if v<25.24 else '#494c4e'
        if z < _underside(v)+.60:
            return '#4d5253'
        if z < _underside(v)+1.75 and any(abs(x-u)<1.43 for u in SIDE_MARKS) and 20.7<v<24.1:
            return '#272c2f'
        if 24.95 < z < 34.32 and v > 26.25 and v < 26.39:
            return '#abaea8'
        if 34.22 < z < 34.37 and v<25.75 and x>220.:
            return '#b0b2ac'
    if 202.42 < x < 207.25 and v > 20.20:
        if any(a-.015 < z < a+.255 for a in (26.70,27.18,27.66,28.14,28.62)):
            return '#565c60'
    return None
