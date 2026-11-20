"""Съёмное шасси БТС-001 и цельный выставочный стилобат. Размеры в мм.

Оси сборки: X к корме, Y поперёк фюзеляжа, Z вверх. Фото ВДНХ:
https://www.kpopov.ru/cosmos/buran_btc-001.htm (4508, 4510, 4542).
Имена деталей и углы печати используются общей сборкой проекта.
"""
import math
import os
from functools import partial

import FreeCAD as App
import Part

V = App.Vector
O = V(0, 0, 0)
Z = V(0, 0, 1)
Y = V(0, 1, 0)
GROUND = -19.5
DECK = -21.45
SEAT = 5.8
GROUP = 'Шасси и стенд'


def _wire(points):
    points = [V(*p) for p in points]
    return Part.makePolygon(points + points[:1])


def _layer(points, z):
    return _wire([(x, y, z) for x, y in points])


def _slab(points, z0, z1):
    return Part.Face(_layer(points, z0)).extrude(V(0, 0, z1 - z0))


def _loft(layers):
    return Part.makeLoft([_layer(points, z) for z, points in layers], True, True)


def _rect(x, y, length, width, bevel):
    a, b = length / 2, width / 2
    return [(x + i, y + j) for i, j in (
        (-a + bevel, -b), (a - bevel, -b), (a, -b + bevel), (a, b - bevel),
        (a - bevel, b), (-a + bevel, b), (-a, b - bevel), (-a, -b + bevel))]


def _union(pieces):
    return pieces[0].multiFuse(pieces[1:]).removeSplitter()


def _single_solid(shape):
    solids = shape.Solids
    if len(solids) != 1:
        raise ValueError('Шасси и стенд: ожидается одно связное тело на деталь')
    solid = solids[0]
    # Intersecting braces can seal a sub-millimetre pocket at the main axle.
    # Keep the exterior and fill all inaccessible pockets for resin printing.
    return Part.makeSolid(solid.OuterShell) if len(solid.Shells) > 1 else solid


def _pin(x, y, gap=0):
    # The peg between the two tyre flats does not carry the model's weight.
    outer = _rect(x, y, 3.1 + 2*gap, 2.45 + 2*gap, .40)
    if gap:
        return _slab(outer, GROUND - 3.05, GROUND + .20)
    tip = _rect(x, y, 2.55, 1.90, .30)
    return _loft([(GROUND - 2.60, tip), (GROUND - 2.22, outer),
                  (GROUND + .42, outer)])


def _cyl(a, b, radius, extra=.08):
    a, b = V(*a), V(*b)
    direction = b - a
    length = direction.Length
    direction.normalize()
    return Part.makeCylinder(radius, length + 2*extra, a - direction*extra, direction)


def _lerp(a, b, t):
    return tuple(i + (j - i)*t for i, j in zip(a, b))


def _tyre(x, y, z, r, w, front):
    """Turn the sidewall, bead seat, hub, round shoulder and tread in one profile."""
    # (radial, axial) pairs in a meridian; outward facing rim is recessed.
    side = [(0, .51*w), (.12*r, .51*w), (.15*r, .59*w), (.24*r, .59*w),
            (.265*r, .505*w), (.445*r, .505*w), (.46*r, .57*w),
            (.50*r, .57*w), (.54*r, .51*w), (.59*r, .55*w),
            (.76*r, .54*w), (.875*r, .49*w), (.96*r, .40*w), (.985*r, .33*w)]
    section = [(rad, -u) for rad, u in side]
    for t in (-.225, 0, .225):
        u = t*w
        section.extend([(r, u-.12), (r-.15, u-.055), (r-.15, u+.055), (r, u+.12)])
    section.extend(reversed(side))
    face = Part.Face(_wire([(rad, u, 0) for rad, u in section]))
    wheel = face.revolve(O, Y, 360)
    bores = []
    count = 5 if front else 6
    for i in range(count):
        angle = math.tau*i/count
        dx, dz = .355*r*math.cos(angle), .355*r*math.sin(angle)
        for sign in (-1, 1):
            bores.append(Part.makeCylinder(.21 if front else .30, .68,
                         V(dx, sign*(w*.505-.37), dz), V(0, sign, 0)))
    wheel = wheel.cut(Part.makeCompound(bores)).removeSplitter()
    wheel.translate(V(x, y, z))
    return wheel


def _shoe(front, sign):
    x = 54 if front else 170.75
    y = 0 if front else sign*12.7
    length, width = (10, 7.6) if front else (11.5, 7.4)
    pad = _rect(x, y, length, width, .74)
    # A slightly off-centre upper key prevents reversing a gear unit.
    kx = x - 1.0
    key = _rect(kx, y, 5.5, 3.8, .64)
    tip = _rect(kx, y, 4.9, 3.2, .50)
    solid = _union([_slab(pad, 3.74, SEAT),
                    _loft([(SEAT-.10, key), (9.26, key), (9.65, tip)])])
    mouth = _rect(x, y, length+.4, width+.4, .78)
    socket = _rect(kx, y, 5.9, 4.2, .68)
    cutter = _union([_slab(mouth, -9.0, SEAT), _slab(socket, SEAT-.12, 10.10)])
    return solid, cutter


def _door(sign):
    # A thickened inboard bay door, lowered on two hinge lugs. The opening
    # between door and strut is not boxed in: resin and wash can escape.
    outline = [(163.9, -2), (175.8, -2), (176.35, -2.65), (175.9, -9.95),
               (175.35, -10.55), (163.8, -10.55), (163.2, -9.95), (163.35, -2.65)]
    def inner(z):
        return 11.05 + (-z - 2)*.21
    face = Part.Face(_wire([(x, sign*inner(z), z) for x, z in outline]))
    pieces = [face.extrude(V(0, sign*1.12, 0))]
    for x in (165.7, 174.55):
        pieces.append(_cyl((x, sign*12.3, -2.45), (x, sign*15.0, -2.45), .74))
        pieces.append(_cyl((x, sign*14.9, -2.45), (x, sign*13.2, 3.95), .74))
        # Low ribs on the inside face echo the stamped panel in 4510.
        pieces.append(_cyl((x, sign*(inner(-2.5)+1.12), -2.5),
                           (x, sign*(inner(-9.95)+1.12), -9.95), .31))
    return pieces


def _gear_paint(x, y, z, *, front, sign):
    cx, cy = (54, 0) if front else (169, sign*22)
    r, w, spacing = (3.35, 2.45, 2.55) if front else (4.25, 3.15, 3.30)
    radial = math.hypot(x-cx, z-(GROUND+r-.23))
    nearest = abs(abs(y-cy)-spacing)
    if nearest <= w*.61+.012 and radial <= r+.015:
        return '#232a2b' if radial > .54*r else '#456651'
    if not front and -10.58 <= z <= -1.94 and 163.15 < x < 176.4:
        if abs(y) < 12.6 + (-z-2)*.21:
            return '#63765c'
    if z <= GROUND+2.45:
        return '#606769'
    # Give the chrome only to the exposed piston surface. A simple threshold
    # on global Z would cut obliquely across its triangular display facets.
    ax, ay, az = cx, cy, GROUND+r-.32
    bx, by = (53.6, 0) if front else (171.0, sign*12.6)
    dx, dy, dz = bx-ax, by-ay, 4.30-az
    t = ((x-ax)*dx + (y-ay)*dy + (z-az)*dz) / (dx*dx + dy*dy + dz*dz)
    if .19 < t < .345:
        rho = math.sqrt((x-ax-t*dx)**2 + (y-ay-t*dy)**2 + (z-az-t*dz)**2)
        if rho < (1.03*(.86 if front else 1) + .02):
            return '#a4aeac'
    return '#828c89'


def _gear(front, sign=1):
    x, y = (54, 0) if front else (169, sign*22)
    r, w, spacing = (3.35, 2.45, 2.55) if front else (4.25, 3.15, 3.30)
    z = GROUND + r - .23
    wheels = [_tyre(x, y+k*spacing, z, r, w, front) for k in (-1, 1)]
    # Two broad coplanar tyre flats form an actual bearing surface on the plinth.
    floor = Part.makeBox(30, 30, 10, V(x-15, y-15, GROUND-10))
    wheels = [wheel.cut(floor) for wheel in wheels]
    pieces = wheels + [_cyl((x, y-spacing, z), (x, y+spacing, z), .87 if front else 1.12)]
    pieces.append(_pin(x, y))
    base = _rect(x, y, 3.75, 2.7, .34)
    neck = _rect(x, y, 1.72, 1.62, .23)
    pieces.append(_loft([(GROUND, base), (GROUND+.37, base), (z+.14, neck)]))
    shoe, cutter = _shoe(front, sign)
    pieces.append(shoe)
    a = (x, y, z-.09)
    b = (53.6, 0, 4.30) if front else (171.0, sign*12.6, 4.30)
    # Main telescopic oleo, collars and axle knuckle.
    scale = .86 if front else 1.0
    pieces.append(_cyl(a, b, 1.03*scale))
    for t0, t1, radius in [(.00,.20,1.38), (.34,.91,1.43), (.33,.39,1.59),
                           (.69,.735,1.54), (.89,.99,1.64)]:
        pieces.append(_cyl(_lerp(a,b,t0), _lerp(a,b,t1), radius*scale))
    # Spread V-braces land inside the plate's rim; both remain >=1.2 mm diameter.
    for direction in (-1, 1):
        start = _lerp(a, b, .20)
        end = ((54+direction*3.9, direction*2.46, 4.24) if front else
               (170.75+direction*4.55, sign*(12.5+direction*1.04), 4.24))
        pieces.append(_cyl(start, end, .63 if front else .76))
        pieces.append(_cyl(_lerp(start,end,.20), _lerp(start,end,.88), .79 if front else .91))
    # Articulated torque link with visible knee on the aft face of the column.
    t0, t1 = _lerp(a,b,.10), _lerp(a,b,.46)
    knee = (x+2.7*scale, (t0[1]+t1[1])/2, (t0[2]+t1[2])/2)
    pieces.extend([_cyl(t0,knee,.60*scale), _cyl(knee,t1,.60*scale),
                   _cyl((knee[0],knee[1]-.61,knee[2]),
                        (knee[0],knee[1]+.61,knee[2]),.70*scale)])
    if not front:
        pieces.extend(_door(sign))
    label = 'Носовая опора' if front else ('Левая основная опора' if sign < 0 else 'Правая основная опора')
    return dict(id='GearFront' if front else ('BogiePort' if sign < 0 else 'BogieStarboard'),
                label=label, group=GROUP, shape=_single_solid(_union(pieces)), color='#828c89',
                paint=partial(_gear_paint,front=front,sign=sign),
                explode=(0, 0 if front else sign*9, -16),
                orientation=(151 if sign > 0 or front else -151, 17, 0),
                note='Средние поддержки под плечо монтажной площадки, лёгкие — с внутренней стороны шин и под подкосы. '
                     'Не ставить контакты на диски, боковые грани ключей и пятна шин. Смыть смолу из канавок и за створкой. '
                     'Верхний шип входит в карман корпуса до упора площадки; нижний — между шинами в цоколь.'), cutter


# Outer rail and deck meet in a sloping fascia. The straight museum label
# occupies its long southern edge; the north side narrows toward the nose.
_OUTER = [(32,-9), (37,-15), (65,-36), (72,-38), (171,-38), (182,-29),
          (182,28.5), (174,36.5), (151,36.5), (127,25), (70,15), (39,12), (32,6)]
_TOP = [(35,-8), (40,-13), (66,-29.2), (72.8,-31.2), (169.7,-31.2), (179,-26),
        (179,26.5), (172,33), (151,33), (128,22.4), (71,12.5), (40,9.5), (35,5.3)]
_RAIL_Z = -25.85
_FASCIA_ANGLE = math.degrees(math.atan2(DECK-_RAIL_Z, 6.8))


def _small_foot():
    # A shadow reveal above a continuous flat foot, not short freestanding legs.
    return [(109+(x-109)*.970, y*.941) for x,y in _OUTER]


def _relief_text(text, height, tracking):
    paths = ['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
             '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
             'C:/Windows/Fonts/arialbd.ttf']
    font = next((p for p in paths if os.path.isfile(p)), None)
    if not font:
        raise FileNotFoundError('Для подписи постамента нужен Arial Bold или DejaVu Sans Bold')
    glyphs = Part.makeWireString(text, os.path.dirname(font)+os.sep,
                                 os.path.basename(font), height, tracking)
    return [Part.makeFace(wires, 'Part::FaceMakerBullseye').extrude(V(0,0,.44))
            for wires in glyphs if wires]


def _on_fascia(shape, x, v):
    # In-plane coordinates before rotation. Hide 0.08 mm of the extrusion;
    # at full height relief is still a geometric 0.36 mm, not painted text.
    shape.translate(V(0,v,-.08))
    shape.rotate(O,V(1,0,0),_FASCIA_ANGLE)
    shape.translate(V(x,-38,_RAIL_Z))
    return shape


def _inscription():
    pieces = []
    for text, x, v, size, track in [('БУРАН',84.5,1.52,5.40,.32),
                                    ('БТС-001 • ВДНХ',118,2.18,3.72,.16)]:
        for glyph in _relief_text(text,size,track):
            pieces.append(_on_fascia(glyph,x,v))
    # Flight-test livery flash and thin divider, integral to the fascia.
    for x in (74.3,76.9,79.5):
        slash = _slab([(0,0),(1.18,0),(2.55,3.93),(1.37,3.93)],0,.46)
        pieces.append(_on_fascia(slash,x,2.08))
    rule = _slab([(0,0),(.48,0),(.48,4.9),(0,4.9)],0,.41)
    pieces.append(_on_fascia(rule,113.6,1.60))
    return pieces


def _plinth_paint(x,y,z):
    if y < -31.12 and 73 < x < 167:
        normal_height = (z-_RAIL_Z - (y+38)*(DECK-_RAIL_Z)/6.8) * math.cos(math.radians(_FASCIA_ANGLE))
        if normal_height > .025:
            return '#bb805b' if x < 83 or 113.5 < x < 114.2 else '#f1dfba'
    if z > DECK+.02:
        return '#b7b7ac'
    if z < -26.86:
        return '#242f34'
    return '#37474e' if z < DECK-.04 else '#49595e'


def _plinth():
    small = _small_foot()
    base = _loft([(-28.4,small),(-27.15,small),(-26.72,_OUTER),
                  (_RAIL_Z,_OUTER),(DECK,_TOP)])
    pieces, holes = [base], []
    for x, y, length, width in [(54,0,12,12.5),(169,-22,15.5,15.0),(169,22,15.5,15.0)]:
        bottom = _rect(x,y,length+.86,width+.86,1.09)
        rim = _rect(x,y,length,width,.82)
        pieces.append(_loft([(DECK-.12,bottom), (DECK+.40,bottom),
                             (GROUND-.34,rim),(GROUND,rim)]))
        holes.append(_pin(x,y,.20))
    pieces.extend(_inscription())
    shape = _union(pieces).cut(Part.makeCompound(holes)).removeSplitter()
    return dict(id='Plinth',label='Стилобат с тремя цоколями',group=GROUP,shape=_single_solid(shape),
                color='#49595e',paint=_plinth_paint,explode=(0,0,-33),orientation=(8,59,0),
                note='Печатать отдельно, с рафтом и опорами по нижней плоскости и вдоль нижнего ребра. '
                     'Лицевую фаску с рельефом и верх цоколей оставлять без контактов. '
                     'Открытые сверху карманы промыть пипеткой; не заполнять краской. '
                     'Вначале вставить стойки в корпус, затем посадить сразу три нижних ключа в цоколи.')


def build():
    parts, cutters = [], []
    for front, sign in [(True,1), (False,-1), (False,1)]:
        part, cutter = _gear(front,sign)
        parts.append(part)
        cutters.append(cutter)
    parts.append(_plinth())
    return parts, cutters
