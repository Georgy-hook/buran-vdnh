"""Relief for the open scale-model bay, not a survey of the museum interior.

All floor tiles, sidewall members and roof stiffeners grow directly out of an
existing print wall. There is no second skin with trapped space behind it.
"""

import FreeCAD
import Part

from sections import V, box, fuse, inset, mid, poly, shell_blank


A, B = 78.5, 153.5
FRAMES = (81., 91., 101., 111., 121., 131., 141., 151.)


def _trunk(a, b, side, top):
    return shell_blank([inset(mid(x), side, 0, top) for x in (a, b)])


def _arch(side, inset_y, inset_z):
    # Bond 0.18 mm into the inside of the original canopy. Never touch the
    # external contour or the two closed-position pads at the ends of the bay.
    cover = _trunk(A, B, 2.07, 1.92)
    core = _trunk(A-.2, B+.2, inset_y, inset_z)
    y = .93 if side > 0 else -22.
    mask = box(A-.1, y, 28.72, B-A+.2, 21.07, 13.)
    return cover.cut(core).common(mask)


def roof_members(side):
    """Eight transverse hat ribs, their feet, and one longitudinal seam."""
    foot = _arch(side, 2.60, 2.44)
    cap = _arch(side, 3.53, 3.29)
    members = []
    for x in FRAMES:
        members.append(foot.common(box(x-.85, -23, 28., 1.70, 46, 13)))
        members.append(cap.common(box(x-.44, -23, 28., .88, 46, 13)))
    y = 9.30 if side > 0 else -10.14
    members.append(foot.common(box(A+.44, y, 28., B-A-.88, .84, 13)))
    return members


def _prism(points, direction):
    return Part.Face(poly(points)).extrude(direction)


def _panel_wire(x0, x1, y0, y1, z, trim):
    x0, x1 = x0+trim, x1-trim
    y0, y1 = y0+trim, y1-trim
    c = .66
    return poly([V(x, y, z) for x, y in ((x0+c,y0), (x1-c,y0), (x1,y0+c),
                (x1,y1-c), (x1-c,y1), (x0+c,y1), (x0,y1-c), (x0,y0+c))])


def _deck():
    # A solid bed, not a false raised floor. Its entire lower face intersects
    # the old floor (the old inner keel is at z=3.0). None of the staggered
    # seams penetrate it. Ends slope down into the open cleaning channel.
    bed = _prism([V(x,-13.4,z) for x,z in ((A,2.65), (B,2.65), (B,3.55),
                 (B-2.0,6.28), (A+2.0,6.28), (A,3.55))], V(0,26.8,0))
    panels = []
    for j, (y0,y1) in enumerate(((-12.63,-4.63), (-4.20,4.20), (4.63,12.63))):
        # Offset the central row relative to its two neighbours. The reveal
        # is the bed itself, which stays accessible through the top opening.
        joints = (88., 103., 118., 133., 148.) if j == 1 else (93., 108., 123., 138.)
        bounds = [80.90, *joints, 151.10]
        for a, b in zip(bounds, bounds[1:]):
            wires = [_panel_wire(a+.19, b-.19, y0, y1, z, t)
                     for z,t in ((6.12,0.), (6.67,0.), (6.90,.23))]
            panels.append(Part.makeLoft(wires, True, True))
    return fuse(bed, panels)


def _sidewall(s):
    # The flat inner hull side is at |y|=15.2. The panels penetrate it to
    # 15.58; large open-faced sunken fields do not become hollow boxes.
    def yz_strip(x, width, coords):
        return _prism([V(x,s*y,z) for y,z in coords], V(width,0,0))

    members = []
    for x in FRAMES:
        members.append(yz_strip(x-.55, 1.10, [
            (15.60,4.16), (15.60,23.85), (13.57,23.85), (13.14,22.95),
            (13.43,10.16), (12.10,7.38), (11.76,6.36), (12.55,4.16)]))
    for z in (8.43, 21.94):
        members.append(yz_strip(79.7, B-A-2.4, [
            (15.58,z), (15.58,z+.88), (13.86,z+.88), (13.68,z+.58),
            (13.68,z+.25), (13.94,z)]))
    for a, b in zip(FRAMES, FRAMES[1:]):
        # Shallow embossed liners between the uprights with clipped corners.
        left, right = a+.83, b-.83
        z0, z1 = 9.62, 21.55
        xz = [(left+1.1,z0), (right-.7,z0), (right,z0+.70), (right,z1-1.5),
              (right-1.50,z1), (left+.66,z1), (left,z1-.66), (left,z0+1.1)]
        face = _prism([V(x,s*15.58,z) for x,z in xz], V(0,-s*.97,0))
        # A rib pressed into each panel, rather than a free-standing rod.
        crease = _prism([V(x,s*14.44,z) for x,z in ((left+1.,11.25),
                        (left+1.,12.40), (right-1.,19.95), (right-1.,18.80))],
                        V(0,s*.53,0))
        members.append(face.cut(crease))
    return members


def fixed_operations():
    return [('add', 'Отсек · сплошное основание и настил со ступенчатыми стыками', [_deck()]),
            ('add', 'Отсек · бортовые шпангоуты, стрингеры и штампованные поля',
             _sidewall(-1) + _sidewall(1))]
