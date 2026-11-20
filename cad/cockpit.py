"""Faceted external windscreen surround, with six inset solid glazing panels."""

import Part

from sections import V, GLASS, FRAME, poly, fuse, cut, shell_blank


def cockpit():
    half = [(30.5, 0), (33.8, 9.6), (42.2, 14.0), (53.8, 14.9),
            (61.5, 12.7), (66.3, 6.4), (67.0, 0)]
    footprint = half + [(x, -y) for x, y in reversed(half[1:-1])]
    base, sill, roof = [], [], []
    for x, y in footprint:
        base.append(V(x, y, 23.0))
        sill.append(V(x, y, 31.85 + .075*(x-30)))
        u, v = 52 + .65*(x-52) + 2.5, y*.65
        roof.append(V(u, v, 41.35+.075*(u-45)))
    # Ruled side facets deliberately remain planar where there is glazing.
    shape = Part.makeLoft([poly(base), poly(sill), poly(roof)], True, True)
    frames, cavities, panes = [], [], []
    count = len(footprint)
    for i in (0, 1, 2, count-3, count-2, count-1):
        j = (i+1) % count
        p, q, r, s = sill[i], sill[j], roof[j], roof[i]
        normal = (q-p).cross(s-p)
        normal.normalize()
        centre = (p+q+r+s)*.25
        if normal.dot(centre - V(50, 0, 30)) < 0:
            normal = -normal

        def patch(l, t, a, b, advance):
            def point(u, v):
                return (p*(1-u)+q*u)*(1-v) + (s*(1-u)+r*u)*v + advance*normal
            return Part.Face(poly([point(l, a), point(t, a), point(t, b), point(l, b)]))

        # A frame projects 0.22 mm; glass sits 0.35 mm below that lip.
        border = patch(.025, .975, .065, .96, -.16)
        frames.append(border.extrude(.38*normal))
        pane = patch(.105, .895, .15, .865, .33)
        cavities.append(pane.extrude(-.46*normal))
        panes.append((p, normal, pane, border, centre))
    # A shallow crown and a tapered fairing ease the canopy into the cargo roof.
    rings = []
    for factor, lift in [(1.0, -.08), (.81, .58), (.47, 1.02), (.13, 1.17)]:
        points = []
        for vertex in roof:
            x = 51.5+(vertex.x-51.5)*factor
            points.append(V(x, vertex.y*factor, 41.35+.075*(x-45)+lift))
        rings.append(poly(points))
    crown = Part.makeLoft(rings, True, False, False, 3)
    fillet = shell_blank([(54.7, 10.5, 26, 27.4, 34, 42.21), (60.3, 11.25, 26, 27.4, 34.1, 42.37),
                          (65.7, 9.2, 26, 27.4, 33.5, 41.8), (71.7, 4.35, 26, 27.4, 32, 39.72)])
    return cut(fuse(shape, [*frames, crown, fillet]), cavities), panes, list(zip(sill, roof))


def glazing_color(panes, p):
    # Planar polygon containment in the local windscreen plane, not emissive glass.
    for origin, n, pane, border, centre in panes:
        if (p-centre).Length > 12:
            continue
        d = (p-origin).dot(n)
        if -.17 <= d <= -.08:
            projected = p + (.33-d)*n
            if pane.isInside(projected, .025, True):
                return GLASS
        if .17 <= d <= .255 and border.isInside(p+(-.16-d)*n, .025, True):
            return FRAME
    return None
