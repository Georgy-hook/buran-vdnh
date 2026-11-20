"""Relief artwork, drawn in type coordinates from the lettering on the Moscow mock-up.

The lettering is tall and almost square-cornered, with long у/р descenders.
It isn't an italic system font. The same readable artwork faces out on both sides.
"""

import Part

from sections import V, box, fuse, poly


# advance, perimeter and optional counters. The common baseline is v=0.
GLYPHS = (
    (4.1, [(0,0),(2.86,0),(3.24,.13),(3.49,.50),(3.49,4.80),(3.35,5.13),
           (3.05,5.33),(1.33,5.33),(1.33,6.13),(3.58,6.13),(3.58,7.32),(0,7.32)],
           [[(1.31,1.10),(2.00,1.10),(2.10,1.26),(2.10,4.02),(1.99,4.17),(1.37,4.17),(1.31,4.0)]]),
    (3.94, [(0,5.95),(1.37,5.95),(1.37,1.35),(1.51,1.15),(1.98,1.15),
            (2.07,1.33),(2.07,5.95),(3.42,5.95),(3.42,-1.83),(3.28,-2.23),
            (2.96,-2.55),(2.04,-2.71),(2.04,0),(.74,0),(.30,.18),(0,.67)], []),
    (3.85, [(0,-2.68),(1.38,-2.68),(1.38,0),(2.75,0),(3.20,.20),(3.42,.62),
            (3.42,5.31),(3.24,5.76),(2.86,5.95),(0,5.95)],
            [[(1.34,1.15),(1.95,1.15),(2.07,1.33),(2.07,4.63),(1.94,4.80),(1.39,4.80),(1.34,4.62)]]),
    (3.84, [(0,0),(3.36,0),(3.36,5.28),(3.19,5.76),(2.81,5.95),(.22,5.95),
            (.22,4.80),(1.97,4.80),(2.05,4.65),(2.05,4.06),(1.00,4.06),
            (.48,3.90),(.13,3.50),(0,2.95)],
            [[(1.30,1.15),(2.05,1.15),(2.05,2.96),(1.47,2.96),(1.30,2.77)]]),
    (3.47, [(0,0),(1.39,0),(1.39,2.42),(2.04,2.42),(2.04,0),(3.44,0),
            (3.44,5.95),(2.04,5.95),(2.04,3.78),(1.93,3.62),(1.46,3.62),
            (1.39,3.78),(1.39,5.95),(0,5.95)], []),
)


def name_relief(side):
    xmid = 175.2
    baseline = 18.85
    cursor = 0.
    drawn = []
    for advance, outline, counters in GLYPHS:
        def wire(points):
            vertices = [V(xmid-side*((cursor+u+.155*v)-9.57)*1.16,
                          side*19.88, baseline+v*.88) for u,v in points]
            return poly(vertices)

        face = Part.makeFace([wire(outline), *[wire(h) for h in counters]],
                             'Part::FaceMakerBullseye')
        drawn.append(face.extrude(V(0,side*.35,0)))
        cursor += advance
    return drawn


def flag(side):
    """A shallow two-level badge. The hoist detail can be dry-brushed after priming."""
    field = box(190.1, 19.83 if side>0 else -20.33, 21.2, 7.15, .50, 3.80)
    # Coordinates run from the top, hoist side of each outward-facing flag.
    hoist = 190.52 if side < 0 else 196.84
    def relief(points):
        profile = poly([V(hoist-side*u, side*20.24, 24.70-v) for u,v in points])
        return Part.Face(profile).extrude(V(0, side*.29, 0))

    arc = relief([(.19,1.24),(.55,1.42),(.86,1.37),(1.07,1.20),(1.15,.91),
                  (1.09,.61),(.80,.34),(.93,.30),(1.23,.47),(1.40,.77),(1.41,1.09),
                  (1.28,1.42),(1.01,1.67),(.63,1.75),(.32,1.65),(.08,1.91),(0,1.79),(.18,1.46)])
    tool = relief([(.26,.89),(.68,.41),(.94,.55),(.73,.79),(1.21,1.44),
                   (1.04,1.56),(.55,.97),(.40,1.11)])
    return fuse(field, [arc, tool])
