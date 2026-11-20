"""Open exhibition-well reconstruction in mm; not survey data for the museum interior.

The centre well is the original hollow fuselage. Edge frames and stamped
lands grow from that wall; there is no inaccessible space under a second tub.
"""

from FreeCAD import Vector as V
import Part

from sections import box, cut, frame, fuse, inset, mid, poly

FRONT, REAR = 76.2, 187.0
A, B = FRONT + 1.8, REAR - 1.8
FRAMES = tuple(80.5 + 6.35 * n for n in range(17))
# Seven broad crown fields. Photos 09–11 resolve the paired lower sill
# and splice straps above the lettering, not every seam of both whole doors.
STRAPS = (91.6, 108.0, 124.8, 141.5, 158.4, 173.9)


def _profile(a, b, side, bottom, top):
    wire = frame(inset(mid(a), side, bottom, top))
    return Part.Face(wire).extrude(V(b - a, 0, 0))


def _prism(x, length, points):
    return Part.Face(poly([V(x, y, z) for y, z in points])).extrude(V(length, 0, 0))


def _arch(a, b, s, depth):
    stock = _profile(a, b, 2.06, 0., 1.9)
    core = _profile(a - .1, b + .1, 2.25 + depth, 0., 2.10 + depth)
    ymin = .95 if s > 0 else -21.
    return stock.cut(core).common(box(a-.1, ymin, 28.7, b-a+.2, 20.05, 13.))


def roof_members(s):
    """Light closely spaced crown hoops over a finer longitudinal sub-frame."""
    rib = _arch(A, A + .70, s, 1.02)
    ribs = [rib.translated(V(x - A - .35, 0, 0)) for x in FRAMES]
    lining = _arch(A, B, s, .43)
    for y in (3.25, 6.1, 8.9, 11.7, 14.2, 16.15):
        ymin = y if s > 0 else -(y + .52)
        ribs.append(lining.common(box(A-.1, ymin, 27., B-A+.2, .52, 13.)))
    return ribs


def _bulkhead(edge, direction):
    """A stitched end screen under the fixed collar, with two through scuppers."""
    # Face pointing into well. Keep it behind the lip, never in a door sweep.
    face = edge - direction * .74
    back = face - direction * 1.5
    web = _profile(min(back, face), max(back, face), 4.42, 2.62, 3.2)
    pads = []
    # Offset borders, a clipped stitch corner and a softly crowned central land.
    def patch(y, z, h):
        def stitch(dx, by, bz):
            width = 2.47 - by
            high = h / 2 - bz
            clip = min(.44, high/3)
            yz = [(-width+clip,-high), (width-clip,-high), (width,-high+clip),
                  (width,high-clip), (width-clip,high), (-width+clip,high),
                  (-width,high-clip), (-width,-high+clip)]
            return poly([V(face + direction*dx, y+i, z+j) for i,j in yz])
        return Part.makeLoft([stitch(-.16, 0, 0), stitch(.20, .04, .04),
                              stitch(.47, .39, .39), stitch(.55, .84, .84)], True, True)

    for j in range(6):
        y = (j-2.5) * 5.11
        top = (28.9, 33.4, 35.45, 35.45, 33.4, 28.9)[j]
        z = 9.2
        while top-z >= 2.10:
            h = min(4.91, top-z)
            pads.append(patch(y, z+h/2, h))
            z += 5.19
    web = fuse(web, pads)
    holes = [Part.makeCylinder(2.90, 4., V(min(face,back)-.9,y,9.4), V(1,0,0))
             for y in (-4.0, 4.0)]
    return cut(web, holes)


def _deck(a, b):
    """Reeded sheet with shallow transverse expansion joints and low edge channels."""
    points = [(-13.8,3.03), (-11.1,2.72), (11.1,2.72), (13.8,3.03),
              (13.8,6.40), (12.45,6.40), (11.25,5.17), (9.65,5.17), (8.95,5.66)]
    # Work from starboard to port without doubling back over a flute.
    for i in range(6, -7, -1):
        y = 1.30*i
        points.extend([(y+.24,5.66), (y+.10,5.43), (y-.10,5.43), (y-.24,5.66)])
    points.extend([(-8.95,5.66), (-9.65,5.17), (-11.25,5.17), (-12.45,6.40),
                   (-13.8,6.40)])
    sheet = _prism(a, b-a, points)
    joins = [box(x-.24, -13.5, 4.84, .48, 27., 2.) for x in FRAMES[1::2]
             if a+.25 < x < b-.25]
    return cut(sheet, joins)


def _wall(a, b, s):
    def member(x, length, contour):
        return _prism(x, length, [(s*y,z) for y,z in contour])

    # Tapered web has one large and three smaller *through* lightening fields.
    # Real voids in the web, not dark circles painted on an unbroken wall.
    contour = [(15.53,5.9), (15.53,25.70), (12.60,25.70), (12.24,24.50),
               (12.30,17.45), (11.58,13.45), (8.85,10.0), (7.67,8.9),
               (7.26,5.49), (10.9,4.95)]
    web = member(0., .78, contour)
    web = cut(web, [Part.makeCylinder(r, 1.08, V(-.15, s*y, z), V(1,0,0))
                    for y, z, r in ((11.30,8.1,1.79), (13.52,15.6,1.04),
                                    (13.69,20.05,.91), (13.69,23.16,.87))])
    pieces = [web.translated(V(x-.39,0,0)) for x in FRAMES if a+.39 < x < b-.39]
    # Honed rail and narrow open gutter under the lip. Separate low stringers
    # are pressed into the backing skin behind the ribs, not loose resin rods.
    for z in (12.20, 17.60, 21.58):
        pieces.append(member(a, b-a, [(15.5,z), (15.5,z+.64),
                                       (14.64,z+.64), (14.42,z+.26), (14.70,z)]))
    pieces.append(member(a, b-a, [(15.65,24.64), (15.65,26.25), (14.86,26.25),
                                   (14.68,25.72), (14.04,25.72), (13.81,26.24),
                                   (13.30,26.24), (13.09,25.89), (13.31,25.14)]))
    return pieces


def _shoe_cover(s):
    """Sloping, solid cover on the existing aft gear mount, not a sealed box.

    The underlying hardpoint is X163..179, |Y| >= 8.1, Z <= 12. None
    of it is cut away. The inner toe stays outside both wash-through bores.
    """
    def section(x, top):
        points = [(7.05, 4.55), (15.5, 4.55), (15.5, top), (8.80, top),
                  (8.04, top-.18), (7.12, 5.69)]
        return poly([V(x,s*y,z) for y,z in points])

    return Part.makeLoft([section(160.65, 6.27), section(162.97, 12.44),
                          section(179.03, 12.44), section(181.35, 6.27)], True, True)


def fixed_operations(x0, x1):
    ends = []
    for edge, d in ((FRONT, 1), (REAR, -1)):
        if x0 < edge < x1:
            ends.append(_bulkhead(edge, d))
    # Stop short of each end screen so both Ø5.8 mm scuppers remain full-bore.
    a, b = max(x0, A), min(x1, B)
    if b <= a:
        return []
    covers = [_shoe_cover(s) for s in (-1, 1)] if x0 == 160 else []
    return [('add', 'Отсек · торцевые экраны, стёганые поля и промывочные окна', ends),
            ('add', 'Отсек · профилированный настил с продольными желобами', [_deck(a,b)]),
            ('add', 'Отсек · покатые крышки над гнёздами основных стоек', covers),
            ('add', 'Отсек · облегчённые бортовые рамы, стрингеры и водостоки',
             _wall(a,b,-1) + _wall(a,b,1))]


def lining_color(x, y, z):
    """Material lookup for the real lands; None leaves the outer paint alone."""
    w = abs(y)
    if min(abs(x-FRONT), abs(x-REAR)) < 2.34 and w < 15.18 and 3.1 < z < 36.45:
        edge, d = (FRONT, 1) if x < A + 1 else (REAR, -1)
        relief = (x-edge)*d+.74
        if relief > .12 and z > 9.17:
            return '#bfc3bc' if relief > .36 else '#9da59f'
        return '#747f80'
    if not A-.01 < x < B+.01 or z <= 3.11 or z > 26.48 or w > 16.02:
        return None
    if w >= 13.04 and z > 24.57:
        return '#adb4ae' if z > 25.84 else '#667275'
    if 160.64 < x < 181.36 and 7.04 < w < 15.22 and 5.7 < z < 12.46:
        return '#869496'
    if w < 13.86 and z <= 6.41:
        if z < 5.31:
            return '#697477'
        return '#9ba5a4' if w > 9.10 else '#8e989b'
    if w < 15.24 and z < 25.78:
        if any(abs(x-f) < .40 for f in FRAMES):
            return '#707d80'
        return '#505e62' if w > 14.75 else '#828d8d'
    return None
