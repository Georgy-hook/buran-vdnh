"""Removable, keyed swing doors for the BTS-001 scale kit (CAD millimetres).

Closed exterior: Moscow, VDNKh. See Moscow_2026-03-31_24.jpg and _26.jpg
on Wikimedia Commons: transverse splice straps, a shoulder panel line above
another long sill line and isolated fittings, not a tile grid. The bearings,
travel stops and unladen bay lining are model engineering, not flight hardware.
"""

from bisect import bisect_left
import math

from FreeCAD import Vector as V
import Part

from bay_liner import FRONT, REAR, FRAMES, STRAPS, fixed_operations, roof_members
from sections import PORCELAIN, box, cut, fuse, inset, item, mid, shell_blank


EDGE_GAP = .30
HALF_CENTRE_GAP = .22
SILL = 26.44
HEM = 26.97
PIVOT_Y, PIVOT_Z = 19.45, 27.45
R_PIN, R_BORE = 1.42, 1.65
FLAT_HALF, MOUTH_HALF = .85, 1.07
OPEN, RELEASE = 112., 57.
CAM_FROM, CAM_TO, R_CAM = 223., 251., 3.30
EX = V(1, 0, 0)


def _ends(t0, t1):
    """Intervals measured into the door from each end, in ascending X."""
    return [(FRONT + t0, FRONT + t1), (REAR - t1, REAR - t0)]


def _pivot(s, x):
    return V(x, s * PIVOT_Y, PIVOT_Z)


def _cylinder(s, x0, x1, radius):
    return Part.makeCylinder(radius, x1 - x0, _pivot(s, x0), EX)


def _sector(s, x0, x1, r, lo, hi):
    """Circular fan. Angles run from the outboard radial towards the crown."""
    def rim(angle):
        a = math.radians(angle)
        return _pivot(s, x0) + V(0, s * r * math.cos(a), r * math.sin(a))

    axis = _pivot(s, x0)
    a, b = rim(lo), rim(hi)
    edges = [Part.makeLine(axis, a), Part.Arc(a, rim((lo + hi)/2), b).toShape(),
             Part.makeLine(b, axis)]
    return Part.Face(Part.Wire(edges)).extrude(V(x1 - x0, 0, 0))


def _mouth(s, x0, x1, half_height):
    y = PIVOT_Y if s > 0 else -PIVOT_Y - 6
    return box(x0, y, PIVOT_Z - half_height, x1 - x0, 6, 2 * half_height)


def operations(x0, x1):
    """For Work.apply AFTER the skin details, BEFORE cutting assembly sockets."""
    if x1 <= FRONT-3.57 or x0 >= REAR+3.57:
        return []

    left, right = max(x0, FRONT - EDGE_GAP), min(x1, REAR + EDGE_GAP)
    opening = [box(left, -27, SILL, right-left, 54, 24)] if right > left else []

    def local(t0, t1):
        return [(max(a, x0), min(b, x1)) for a, b in _ends(t0, t1)
                if a < x1 and b > x0]

    bosses, pockets = [], []
    for s in (-1, 1):
        for a, b in local(-3.57, -.31):
            blank = _cylinder(s, a, b, 2.55)
            # Flush-ended cheek, only 1.5 mm proud of the original side.
            bosses.append(blank.common(box(a - .1, -21.50, 20, b-a+.2, 43, 16)))
        for a, b in local(-3.48, 2.33):
            pockets.append(_cylinder(s, a, b, R_BORE))
        for a, b in local(-3.48, -1.52):
            pockets.append(_mouth(s, a, b, MOUTH_HALF))
        for a, b in local(-1.52, 2.33):
            pockets.append(_mouth(s, a, b, R_BORE))
        for a, b in local(-1.53, .18):
            pockets.append(_sector(s, a, b, R_CAM + .24, CAM_FROM - OPEN, CAM_TO))

    # Separate crown seats, independent of the wash-through end screens.
    pads = [box(a, -2.3, 36.9, b-a, 4.6, 1.0) for a, b in local(-.9, 1.65)]
    return [('cut', 'Грузовой отсек · сквозное раскрытие до промывочного канала', opening),
            ('add', 'Створки · торцевые щёки и опоры закрытого свода', bosses + pads),
            ('cut', 'Поворотные цапфы · замочные щели и секторные ограничители', pockets),
            *fixed_operations(x0, x1)]


def _shape(s):
    def trunk(a, b, side=0, top=0):
        return shell_blank([inset(mid(x), side, 0, top) for x in (a, b)])

    # Keep the section law exactly congruent with the adjacent fixed museum roof.
    outer = trunk(FRONT, REAR)
    inner = trunk(FRONT - .2, REAR + .2, 2.25, 2.10)
    y0 = HALF_CENTRE_GAP if s > 0 else -25
    half = box(FRONT - .2, y0, HEM, REAR - FRONT + .4, 25-HALF_CENTRE_GAP, 18)
    skin = outer.cut(inner).common(half)

    # Two distinct tiers, visible in Moscow_2026-03-31_26. Fine etching is
    # limited to the outer skin; the underside and print wall stay continuous.
    limiter = trunk(FRONT - .2, REAR + .2, .24, .24)
    tools = [box(FRONT - .1, -24, 30.70, REAR - FRONT + .2, 48, .25).cut(limiter)]
    straps = []
    for x in STRAPS:
        tools.append(box(x, -25, 30.7, .32, 50, 13).cut(limiter))
        # Thin doubler from the secondary shoulder line over the crown.
        stock = trunk(x-.80, x-.12, -.12, -.13)
        patch = stock.cut(inner).common(half).common(box(x-1, -25, 31.0, 1.2, 50, 12))
        straps.append(patch)
    # Lower rolled seam, independent of the crown straps; its shallow second
    # tier and discrete hinge keepers are visible above the VDNKh wordmark.
    tools.append(box(FRONT-.1, -25, 28.65, REAR-FRONT+.2, 50, .23).cut(limiter))
    for x in (85.1, 103.5, 121.0, 139.2, 157.4, 171.0, 184.9):
        y = 19.50 if s > 0 else -20.22
        straps.append(box(x-.46, y, 28.68, .92, .72, 1.13))
    skin = cut(fuse(skin, straps), tools)

    metal = []
    for a, b in _ends(-1.30, 2.10):
        metal.append(_cylinder(s, a, b, R_PIN))
    for a, b in _ends(-1.30, -.05):
        metal.append(_sector(s, a, b, R_CAM, CAM_FROM, CAM_TO))
    for a, b in _ends(-3.25, -1.20):
        cyl = _cylinder(s, a, b, R_PIN)
        # The two flats are parallel to the narrow, side-facing mouth ONLY
        # when the door is turned to its maintenance position.
        slab = box(a-.1, -25, PIVOT_Z - FLAT_HALF, b-a+.2, 50, 2*FLAT_HALF)
        slab.rotate(_pivot(s, a), EX, s * RELEASE)
        metal.append(cyl.common(slab))
    return fuse(skin, metal + roof_members(s))


# Approximated mid-thickness roof boundary for the face-palette classifier.
# This is sampled once, not a boolean or nearest-face search per GLB triangle.
def _roof_split():
    w, bottom, crown = 18.90, 26.30, 38.95
    rows = [(0., crown)]
    for n in range(65):
        t = 1 - n/64
        u = 1-t
        y = w*(u**3 + 3*u*u*t + 3*u*t*t*.56 + t**3*.15)
        z = bottom + (crown-bottom)*(3*u*u*t*.67 + 3*u*t*t + t**3)
        rows.append((y, z))
    return rows


_SPLIT = _roof_split()
_WIDTHS = tuple(y for y, z in _SPLIT)


def door_color(x, y, z):
    w = abs(y)
    if x < FRONT or x > REAR:
        return '#899396'
    if w > 20.04 and 28.60 < z < 29.87:
        return '#a6aaa4'
    i = max(1, bisect_left(_WIDTHS, w))
    if i < len(_SPLIT):
        a, h = _SPLIT[i-1]
        b, k = _SPLIT[i]
        if z < h + (k-h)*(w-a)/(b-a):
            if any(abs(x-f) < .36 for f in FRAMES):
                return '#bbc3bd'
            if any(lo-.02 < w < lo+.54 for lo in (3.25,6.1,8.9,11.7,14.2,16.15)):
                return '#acb6b2'
            return '#909e9e'
    if any(f-.82 < x < f-.10 for f in STRAPS) and z > 30.98:
        return '#d1d2ca'
    return PORCELAIN


def kit():
    parts = []
    for s, key, side in [(-1, 'BayDoorPort', 'левая'), (1, 'BayDoorStarboard', 'правая')]:
        part = item(key, 'Створка отсека · ' + side, _shape(s), PORCELAIN,
                    (0, s*29, 18), (s*27, -36, 0),
                    'Опоры на внутреннюю стенку, не на цапфы. Не красить щели. '
                    'Удерживая створку открытой на 57°, одновременно ввести обе '
                    'цапфы снаружи в торцевые пазы. Поворот до упора — 112°; '
                    'снимать только при 57°, без отгибания щёк.', paint=door_color)
        part['articulation'] = dict(family='bay', axis=[1, 0, 0],
                                    pivot=[FRONT, s*PIVOT_Y, PIVOT_Z], angle=-s*OPEN)
        parts.append(part)
    return parts
