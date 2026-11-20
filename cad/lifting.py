"""VDNKh BTS-001 display, 1:144. X aft, Y starboard, Z up, model mm.

Ground views: kpopov.ru/cosmos/buran_btc-001.htm, 4508/4537/4548;
side outline: Commons File:Buran_at_VDNKh.jpg. The upper brow and lower
heel stay fixed. Four removable rudder/brake leaves rotate about two swept
axes. Pins and bearings are scale-print adaptations, not museum mechanisms.
"""
from bisect import bisect_right
from math import cos, radians, sqrt

import Part
from FreeCAD import Vector as V
from fin_cheeks import score as fin_scores
from sections import PORCELAIN
from wing_relief import CARBON, paint as wing_paint, wing_skin

# The scale of the profile comes from the height over the spine, NOT the
# nose-to-tail apparent length in the ground photographs (perspective).
# Commons 03 and 06 independently put the toe at the flag station and
# the end of the brow beyond the end of the lateral fairing.
AXLE_X = 217.2
SLOPE = .70
S = sqrt(1.+SLOPE**2)
AXIS = V(SLOPE/S, 0, 1./S)
CHORD = V(1./S, 0, -SLOPE/S)
OPEN = 32.0
# Extraction pockets must leave a continuous central septum: with axes
# closer than twice the counterbore radius the sky shows through the fin.
AXLE_Y = 2.09
PIN = .78
BORE = .98
HUB = 1.44
SEAT = 2.75


def pivot(sign):
    return V(AXLE_X, sign*AXLE_Y, 54.)


def _hinge_x(z):
    return AXLE_X+SLOPE*(z-54.)


# z, LE, aft edge of fixed fin, half thickness. The rising heel behind
# the load-carrying shoe is not an extension of the roof. The brow and
# the lower spur overhang the swept hinge line, independent of the leaves.
FIN = (
    (40.00, 192.00, 229.50, 5.65), (40.62, 192.10, 228.10, 5.05),
    (41.65, 192.22, 226.45, 4.32), (44.10, 192.36, 234.60, 3.59),
    (47.65, 192.85, 236.80, 3.25), (48.05, 192.98, 236.96, 3.20),
    (48.60, 193.16, 235.75, 3.15), (49.75, 193.61, 221.60, 3.04),
    (51.20, 194.42, _hinge_x(51.2)+1.73*S, 2.88),
    (54.00, 196.80, _hinge_x(54.0)+1.73*S, 2.72),
    (87.70, 226.99, _hinge_x(87.7)+1.73*S, 2.00),
    (92.25, 231.12, _hinge_x(92.25)+1.73*S, 1.84),
    (93.18, 232.06, 254.80, 1.72), (95.05, 233.94, 254.78, 1.55),
    (96.10, 235.43, 254.73, 1.46), (96.78, 237.12, 254.62, 1.30),
    (97.04, 239.12, 254.55, 1.09), (97.12, 240.85, 254.46, .89),
)


def _interp(table, v):
    i = max(1, min(len(table)-1, bisect_right(table, (v, float('inf')))))
    a, b = table[i-1:i+1]
    k = min(1., max(0., (v-a[0])/(b[0]-a[0])))
    return tuple(x+k*(y-x) for x, y in zip(a[1:], b[1:]))


def _curve(points):
    if len(points) == 2:
        return Part.makeLine(*points)
    c = Part.BezierCurve()
    c.setPoles(points)
    return c.toShape()


def _contour(embed, start, segments):
    edges = []
    for segment in segments:
        edges.append(_curve([embed(*p) for p in (start, *segment)]))
        start = segment[-1]
    return Part.Wire(edges)


def _loft(wires):
    return Part.makeLoft(wires, True, True)


def _poly(points):
    return Part.makePolygon([*points, points[0]])


def _key_wire(center, depth, wide, thick, embed):
    a, b = wide/2, thick/2
    f = min(.7, .43*b)
    profile = ((-a+f, -b), (a-f, -b), (a, -b+f), (a, b-f),
               (a-f, b), (-a+f, b), (-a, b-f), (-a, -b+f))
    return _poly([embed(center+x, s, depth) for x, s in profile])


def _key(x, width, thick, depth, embed, socket=False):
    if socket:
        return _loft([_key_wire(x, d, width+.4, thick+.4, embed)
                      for d in (-.6, depth+.45)])
    return _loft([_key_wire(x, d, width-2*r, thick-2*r, embed)
                  for d, r in ((-.52, 0.), (depth-.70, 0.), (depth, .39))])


def _fin_band(z, chord):
    return min(.18*chord, 1.36+2.05*max(0., 1.-(z-40.)/11.)**2)


def _fin_wire(z):
    nose, tail, r = _interp(FIN, z)
    c = tail-nose
    band = _fin_band(z, c)
    # Thin centre web behind the pivot prevents an open slot along the entire
    # hinge, while leaving clearance between the four independent leaves.
    aft = (.20 if 51.2 <= z <= 92.25 else .54)*r
    tip = (0., 0.)
    return _contour(lambda x, y: V(nose+x, y, z), tip, [
        ((0., .55*r), (.48*band, .76*r), (band, .81*r)),
        ((.36*c, 1.12*r), (.54*c, r), (c-.78, aft+.08)),
        ((c, aft),), ((c, -aft),), ((c-.78, -aft-.08),),
        ((.54*c, -r), (.36*c, -1.12*r), (band, -.81*r)),
        ((.48*band, -.76*r), (0., -.55*r), tip),
    ])


def _fin_paint(x, y, z):
    le, tail, _ = _interp(FIN, z)
    if x < le+_fin_band(z, tail-le) or z > 96.75:
        return CARBON
    # Dark lower liners on the overhanging brow and on the swept heel;
    # 2013 rear-quarter images show the light cheek ending above these.
    if z >= 93.18 and (x >= tail-.80 or z < 94.05 and x > _hinge_x(z)+.8):
        return CARBON
    heel_edge = 222.0+3.25*(z-41.45)
    if z < 51.2 and (x > tail-1.1 or 41.45 < z < 45.7 and x > heel_edge):
        return CARBON
    if 51.2 < z < 92.3 and x >= _hinge_x(z)-2.65:
        return CARBON
    return PORCELAIN


def _local(sign, u, y, w):
    return pivot(sign)+CHORD*u+V(0, y, 0)+AXIS*w


def _block(sign, u0, u1, y0, y1, w0, w1):
    face = Part.Face(_poly([_local(sign, u, y, w0) for u, y in
                            ((u0, y0), (u1, y0), (u1, y1), (u0, y1))]))
    return face.extrude(AXIS*(w1-w0))


# front z, rear z, aft u in the open display. The transverse split slopes
# distinctly towards the tail in side view. Above the split is the longer leaf.
LEVELS = (((54.0, 54.3, 14.15), (72.3, 68.8, 10.75)),
          ((73.15, 69.65, 10.65), (91.65, 91.8, 8.75)))
FRONT = 1.68


def _leaf_local(end, fraction):
    front_z, rear_z, rear_u = end
    open_u0 = FRONT*cos(radians(OPEN))
    u = FRONT+(rear_u-open_u0)*fraction/cos(radians(OPEN))
    w = (front_z+(rear_z-front_z)*fraction-54.)*S+SLOPE*u*cos(radians(OPEN))
    return u, w


def _layer(sign, segment, level, recess):
    low, high = LEVELS[segment]
    end = tuple(a+(b-a)*level for a,b in zip(low, high))
    # Curved outside, flatter mating face. The broad forward spar tapers
    # to a blunt printable trailing land; the perimeter stands proud of
    # the light insert. Mirroring is local, not a negative-scale mesh.
    fractions = (0., .042, .085, .115, .27, .57, .865, .902, .965, 1.)
    outer = (.56, .84, 1.05, 1.06-recess, 1.14-recess,
             .98-recess, .70-recess, .71, .55, .35)
    inner = (.50, .66, .74, .76-recess, .80-recess,
             .75-recess, .66-recess, .64, .52, .35)
    outline = []
    for side, widths, indices in ((sign, outer, range(len(outer))),
                                  (-sign, inner, reversed(range(len(inner))))):
        for i in indices:
            u, w = _leaf_local(end, fractions[i])
            outline.append(_local(sign, u, side*widths[i], w))
    return _poly(outline)


def _seat_w(segment):
    return _leaf_local(LEVELS[segment][0], 0.)[1]+6.6


def _leaf(sign, segment):
    seat = _seat_w(segment)
    body = _loft([_layer(sign, segment, z, relief) for z, relief in
                  ((0., 0.), (.045, 0.), (.063, .20), (.937, .20), (.955, 0.), (1., 0.))])
    neck = _block(sign, -.06, FRONT+.35, -.67, .67, seat, seat+2.10)
    collar = Part.makeCylinder(HUB, 2.10, _local(sign, 0, 0, seat), AXIS)
    shaft = Part.makeCylinder(PIN, SEAT+.1, _local(sign, 0, 0, seat-SEAT), AXIS)
    chamfer = Part.makeCone(.57, PIN, .35, _local(sign, 0, 0, seat-SEAT-.35), AXIS)
    leaf = body.multiFuse([neck, collar, shaft, chamfer]).removeSplitter()
    leaf.rotate(pivot(sign), AXIS, sign*OPEN)
    return leaf


def _bearing(sign, segment):
    w = _seat_w(segment)
    seat = Part.makeCylinder(1.48, SEAT+.56, _local(sign, 0, 0, w-SEAT-.56), AXIS)
    # The forward web reaches into the central airfoil; the ring is pierced
    # all the way through so liquid resin and trapped air can escape.
    neck = _block(sign, -4.0, .03, -1.03, 1.03, w-SEAT-.56, w)
    hole = Part.makeCylinder(BORE, SEAT+1., _local(sign, 0, 0, w-SEAT-.8), AXIS)
    return seat.fuse(neck).cut(hole).removeSplitter()


def _leaf_paint(sign, segment):
    from FreeCAD import Rotation
    undo = Rotation(AXIS, -sign*OPEN)
    low, high = LEVELS[segment]
    def paint(x, y, z):
        p = undo.multVec(V(x, y, z)-pivot(sign))
        u, w = p.dot(CHORD), p.dot(AXIS)
        if u < FRONT+.6:
            return CARBON
        def row(end):
            ua, wa = _leaf_local(end, 0.)
            ub, wb = _leaf_local(end, 1.)
            return wa+(wb-wa)*(u-ua)/(ub-ua)
        wl, wh = row(low), row(high)
        level = (w-wl)/(wh-wl)
        rear = _leaf_local(tuple(a+(b-a)*level for a,b in zip(low, high)), 1.)[0]
        fraction = (u-FRONT)/(rear-FRONT)
        # The inner faces seen from aft are light edge-to-edge; the thick
        # black rectangular surrounds seen broadside are on the outside.
        if p.y*sign < -.18 and fraction > .11 and .012 < level < .989:
            return '#d9dad4'
        if level < .061 or level > .94 or fraction < .11 or fraction > .88:
            return CARBON
        return PORCELAIN
    return paint


def _mirror(shape):
    return shape.mirror(V(0, 0, 0), V(0, 1, 0))


def _part(name, label, shape, explode, orientation, paint, note):
    solid, = shape.Solids
    return dict(id=name, label=label, group='Оперение', shape=solid,
                color=PORCELAIN, explode=explode, orientation=orientation,
                note=note, paint=paint)


def tail():
    def along_z(x, y, d):
        return V(x, y, 40.-d)
    keys = [(204., 10.4, 3.4, 4.4), (222., 7.2, 2.5, 4.4)]
    fixed = _loft([_fin_wire(row[0]) for row in FIN])
    fixed = fin_scores(fixed, lambda z: _interp(FIN, z)[0])
    # Counterbores include a 3.6 mm extraction stroke. Remove the open upper
    # leaf first, then the lower; reverse that order to assemble. In between
    # the bearings, the continuous dark fairing closes the hinge line.
    clearances = [Part.makeCylinder(HUB+.31, SEAT+6.92,
                                    _local(sign, 0, 0, _seat_w(i)-SEAT-.76), AXIS)
                  for sign in (-1, 1) for i in (0, 1)]
    fixed = fixed.cut(clearances[0].multiFuse(clearances[1:]))
    bearings = [_bearing(sign, i) for sign in (-1, 1) for i in (0, 1)]
    fin = fixed.multiFuse([*bearings, *[_key(*k, along_z) for k in keys]]).removeSplitter()
    sockets = [_key(*k, along_z, socket=True) for k in keys]
    parts = [_part('Fin', 'Неподвижный киль с четырьмя гнёздами', fin, (0, 0, 25),
                   (10, -16, 0), _fin_paint, 'Проверьте сквозные Ø1,96 мм лунки; не заливать смолой. '
                   'Не ставьте опоры на рабочие грани шипов киля.')]
    for sign, hand, name in ((-1, 'Port', 'левая'), (1, 'Starboard', 'правая')):
        for i, height, word in ((0, 'Lower', 'нижняя'), (1, 'Upper', 'верхняя')):
            p = _part('Brake'+hand+height, f'Створка руля · {name} {word}', _leaf(sign, i),
                      (9, 10*sign, 26+10*i), (15*sign, -24, 0), _leaf_paint(sign, i),
                      'Вставить штифт Ø1,56 мм вдоль оси в гнездо сверху. Для снятия в '
                      'открытом положении приподнять на 3,6 мм вдоль оси и отвести наружу. '
                      'Снять верхнюю первой. Не склеивать шарнир.')
            # All delivered BReps are in the open, assembled coordinates.
            p['articulation'] = dict(pivot=list(pivot(sign)), axis=list(AXIS), angle=-sign*OPEN, family='brake')
            parts.append(p)
    return parts, sockets


def build():
    skin = wing_skin()
    parts, cutters = [], []
    for sign, name, label in ((-1, 'WingPort', 'Левая консоль крыла'),
                              (1, 'WingStarboard', 'Правая консоль крыла')):
        def along_y(x, z, d):
            return V(x, 20.-d, (7.55 if x < 150. else 5.60)+z)
        # Shorter rear tab fits within the lowered root section, behind the
        # bogie mount; the old, taller tab would poke through the elevon.
        keys = [(114.+sign, 14.8, 4.0, 5.5), (185.+sign, 9.6, 2.15, 4.8)]
        solid = skin.multiFuse([_key(*k, along_y) for k in keys]).removeSplitter()
        sockets = [_key(*k, along_y, socket=True) for k in keys]
        if sign < 0:
            solid = _mirror(solid)
            sockets = [_mirror(s) for s in sockets]
        cutters.extend(sockets)
        parts.append(_part(name, label, solid, (0, 28*sign, 0), (32*sign, -14, 0), wing_paint,
                           'Опоры у корня и снизу вне шарнирного шва; не перекрыть микрорельеф '
                           'плиточных швов и рабочие грани шпонок. Проверить в слайсере.'))
    aft, sockets = tail()
    return parts+aft, cutters+sockets
