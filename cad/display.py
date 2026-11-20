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


# 4510: width of each main tyre is about .43 projected wheel diameters;
# the clear strip between them is about .32 diameters. No aircraft dimensions
# are inferred from the near edge of the strongly foreshortened door.
def _wheel_size(front):
    return (3.35, 2.28, 2.50) if front else (4.25, 3.62, 3.56)


def _tyre(x, y, z, r, w, inside):
    """One turned section; its exposed face is not a perforated brake rotor."""
    # Angles of the wheel axis are mirrored locally: +u always faces the strut.
    outer = [(0, -.54*w), (.18*r, -.54*w), (.23*r, -.46*w),
             (.42*r, -.43*w), (.47*r, -.53*w), (.53*r, -.53*w),
             (.56*r, -.49*w), (.70*r, -.52*w), (.83*r, -.50*w),
             (.94*r, -.44*w), (.985*r, -.37*w)]
    section = list(outer)
    for t in (-.245, 0, .245):
        u = t*w
        section.extend([(r, u-.15), (r-.16, u-.075), (r-.16, u+.075), (r, u+.15)])
    section.extend([(.985*r, .37*w), (.94*r, .44*w), (.83*r, .50*w),
                    (.70*r, .52*w), (.52*r, .49*w), (.48*r, .54*w),
                    (.45*r, .54*w), (.43*r, .61*w), (.36*r, .61*w),
                    (.34*r, .68*w), (.25*r, .68*w), (.23*r, .58*w), (0, .58*w)])
    face = Part.Face(_wire([(rad, u*inside, 0) for rad, u in section]))
    wheel = face.revolve(O, Y, 360)
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


def _panel(x, y, z, length, height, thick, sign, bevel):
    # Chamfer in the XZ plane, extrusion towards the aircraft centreline.
    outline = _rect(x, z, length, height, bevel)
    return Part.Face(_wire([(px, y, pz) for px, pz in outline])).extrude(V(0, -sign*thick, 0))


def _hook(x, sign, y, z, scale):
    # The three curved arms in 4510 stand away from the back of the panel.
    # A band with two *arcs* leaves daylight below the short upper rail.
    def pt(d, h):
        return V(x-.54*scale, sign*(y+d*scale), z+h*scale)
    a, b, c = pt(-2.5, 0), pt(-1.65, 0), pt(-.42, -4.2)
    d, e, f = pt(-.13, -4.5), pt(-.83, -4.69), pt(-1.23, -4.48)
    edges = [Part.makeLine(a, b), Part.Arc(b, pt(-1.80, -2.30), c).toShape(),
             Part.makeLine(c, d), Part.makeLine(d, e), Part.makeLine(e, f),
             Part.Arc(f, pt(-2.65, -2.3), a).toShape()]
    return Part.Face(Part.Wire(edges)).extrude(V(1.08*scale, 0, 0))


def _door(front, sign):
    # 4508, aft quarter: the OUTER (dark) door actually overlaps the wheel in
    # projection. 4510 shows a mostly plain green insert and the three hooks.
    # Only the visible forward panel is reproduced (4508 / 4542).
    x, y, top, bottom, length = ((53.6, 5.52, -3.16, -11.88, 12.4) if front else
                                 (165.4, 28.64, -3.30, -14.87, 24.6))
    z, height = (top+bottom)/2, top-bottom
    parts = [_panel(x, sign*y, z, length, height, .90, sign, .52),
             _panel(x, sign*(y-.82), z, length-.98, height-.86, .34, sign, .40)]
    # Thin stamped inspection cover, not generic rows of rivets. Flush outside.
    if not front:
        parts.append(_panel(x+2.5, sign*(y-1.13), z+1.8, 5.6, 4.8, .25, sign, .25))
    hinges = (x-length*.405, x-1.17, x+length*.405) if not front else (x-4.4, x+4.0)
    scale = .83 if front else 1.
    axis_y = y-2.12*scale
    hinge_z = -1.0
    parts.append(_cyl((hinges[0]-.26, sign*axis_y, hinge_z),
                      (hinges[-1]+.26, sign*axis_y, hinge_z), .59))
    for hx in hinges:
        parts.extend([_hook(hx, sign, y, hinge_z, scale),
                      _cyl((hx-.77, sign*axis_y, hinge_z),
                           (hx+.77, sign*axis_y, hinge_z), .76)])
    return parts


def _gear_paint(x, y, z, *, front, sign):
    cx, cy = (54, 0) if front else (169, sign*22)
    r, w, spacing = _wheel_size(front)
    radial = math.hypot(x-cx, z-(GROUND+r-.23))
    dy = abs(y-cy)
    if abs(dy-spacing) < w*.69+.01 and radial <= r+.02:
        if radial > .52*r:
            return '#232728'
        return '#456651' if dy < spacing else '#333b3b'
    edge = 5.52 if front else 28.64
    top = -3.16 if front else -3.30
    if z < top+.05 and abs(abs(y)-edge) < 1.50 and abs(y) > edge-1.52:
        # Exterior is dark belly TPS; the inner face and lip are green.
        if abs(y) >= edge-.05:
            return '#33393c'
        return '#557557'
    if z < GROUND+2.76:
        return '#555e60'
    return '#969e9c'


def _gear(front, sign=1):
    x, y = (54, 0) if front else (169, sign*22)
    r, w, spacing = _wheel_size(front)
    z = GROUND + r - .23
    wheels = [_tyre(x, y+k*spacing, z, r, w, -k) for k in (-1, 1)]
    floor = Part.makeBox(30, 30, 10, V(x-15, y-15, GROUND-10))
    pieces = [wheel.cut(floor) for wheel in wheels]
    pieces.extend([_cyl((x, y-spacing, z), (x, y+spacing, z), .80 if front else 1.02),
                   _pin(x, y)])
    # Exhibition jack between the wheels: broad tapered foot with screw neck.
    foot = _rect(x, y, 3.64, 2.80, .19)
    tip = _rect(x, y, 1.24, 1.20, .14)
    pieces.extend([_loft([(GROUND, foot), (GROUND+.31, foot), (z-1.0, tip)]),
                   _cyl((x, y, z-1.25), (x, y, z), .56)])
    shoe, cutter = _shoe(front, sign)
    pieces.append(shoe)
    top_y = 0 if front else sign*20.9
    top_x = 54.65 if front else 170.5
    a, b = (x, y, z-.16), (top_x, top_y, -.92)
    scale = .79 if front else 1.
    pieces.append(_cyl(a, b, .99*scale))
    for start, end, radius in [(0,.20,1.14), (.38,.93,1.16), (.375,.445,1.31),
                               (.738,.785,1.24), (.87,1.0,1.43)]:
        pieces.append(_cyl(_lerp(a,b,start), _lerp(a,b,end), radius*scale))
    # Stiff links and their visible pin joints are spread across the rail,
    # not all converging on the narrow CAD mount behind the belly.
    pin = _lerp(a, b, .28)
    shoulder_y = 0 if front else sign*12.72
    edge_y = 3.76 if front else sign*26.52
    span = 3.50 if front else 4.50
    if front:
        pieces.append(_cyl((top_x-span, 0, -.94), (top_x+span, 0, -.94), .73))
    for k in (-1, 1):
        xx = top_x+k*span
        knee = (xx, shoulder_y, -.94)
        upper = (xx, shoulder_y, 4.00)
        end = (xx, edge_y, -1.0)
        # Ends meet the upper plate *within* its socket footprint.
        pieces.extend([_cyl(upper, knee, .68 if front else .86),
                       _cyl(knee, end, .68 if front else .80)])
        if not front:
            pieces.append(_cyl(b, knee, .86*scale))
        target = knee if k == -1 else end
        pieces.extend([_cyl(pin, target, .67*scale),
                       _cyl(_lerp(pin,target,.10), _lerp(pin,target,.88), .82*scale)])
    # Short articulating link, aft of the axle, visible between the tyres.
    p0, p1 = _lerp(a,b,.03), _lerp(a,b,.32)
    knee = (x+2.37*scale, y, z+1.67*scale)
    pieces.extend([_cyl(p0, knee, .55*scale), _cyl(knee, p1, .55*scale),
                   _cyl((knee[0], y-.67, knee[2]), (knee[0], y+.67, knee[2]), .64*scale)])
    pieces.extend(_door(front, sign))
    # At the crossing of hinge pins and oleo links a simultaneous N-way
    # boolean can leave coincident trims. Weld the main unit progressively.
    shape = pieces[0]
    if front:
        shape = _union(pieces)
    else:
        for component in pieces[1:]:
            shape = shape.fuse(component).removeSplitter()
    label = 'Носовая опора' if front else ('Левая основная опора' if sign < 0 else 'Правая основная опора')
    return dict(id='GearFront' if front else ('BogiePort' if sign < 0 else 'BogieStarboard'),
                label=label, group=GROUP, shape=_single_solid(shape), color='#828c89',
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
    from plinth import hollow_deck

    small = _small_foot()
    foot_z = -28.4
    exterior = _loft([(foot_z, small), (-27.15, small), (-26.72, _OUTER),
                      (_RAIL_Z, _OUTER), (DECK, _TOP)])
    stations = [(54, 0, 11.4, 9.8), (169, -22, 15.6, 12.45), (169, 22, 15.6, 12.45)]
    base = hollow_deck(exterior, _TOP, foot_z, DECK, [(x, y) for x, y, _, _ in stations])
    pieces, holes = [base], []
    for x, y, length, width in stations:
        # 4510: the tyre flats and jack rest on a simple thin rectangular slab,
        # not a broad bevelled trophy boss. Retain both the rail and wheel levels.
        foot = _rect(x, y, length-.74, width-.74, .28)
        rim = _rect(x, y, length, width, .33)
        pieces.extend([_slab(foot, DECK-.08, GROUND-.85),
                       _slab(rim, GROUND-1.00, GROUND)])
        keyhole = _rect(x, y, 3.50, 2.85, .40)
        holes.append(_slab(keyhole, foot_z-.5, GROUND+.2))
    pieces.extend(_inscription())
    shape = _union(pieces).cut(Part.makeCompound(holes)).removeSplitter()
    return dict(id='Plinth', label='Полый стилобат с тремя цоколями', group=GROUP,
                shape=_single_solid(shape), color='#49595e', paint=_plinth_paint,
                explode=(0,0,-33), orientation=(8,59,0),
                note='Печатать с рафтом под наклоном. Поддержки ставить на нижнюю кромку и снизу под рёбра; '
                     'не перекрывать открытый низ и сквозные гнёзда. Не ставить контакты на рельеф и площадки шин. '
                     'Промыть рёбра с нижней стороны и пролить каждое гнездо насквозь до установки стоек. '
                     'Вначале вставить стойки в корпус, затем посадить три нижних ключа в цоколи.')


def build():
    parts, cutters = [], []
    for front, sign in [(True,1), (False,-1), (False,1)]:
        part, cutter = _gear(front,sign)
        parts.append(part)
        cutters.append(cutter)
    parts.append(_plinth())
    return parts, cutters
