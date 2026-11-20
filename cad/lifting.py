"""БТС-001 на ВДНХ, 1:144. X — к хвосту, Y — вправо, Z — вверх (мм).

Силуэт, разрез руля и окраска: kpopov.ru/cosmos/buran_btc-001.htm,
кадры 4508, 4537 и 4548; членение элевонов также видно на макете, 4517.
Номинальные углы наплыва/консоли (78°/45°): buran.ru/htm/aerodina.htm.
Профили и малые зазоры адаптированы для настольной печати, не лётные.
"""

from bisect import bisect_right

import Part
from FreeCAD import Vector as V


IVORY = '#e4e1d6'
CARBON = '#292d30'
JOINT = '#383b3c'
BELLY = '#323539'

# y, носок, задняя кромка, высота профиля, хорда элевона, ширина носовой панели.
# Скруглённый переход между наплывом и основной консолью — не острый излом.
WING = (
    (20.0, 82.0, 224.0, 10.7, 21.6, 6.4),
    (27.5, 117.3, 222.7, 9.4, 20.8, 6.3),
    (30.5, 128.8, 222.2, 8.8, 20.4, 6.1),
    (33.5, 136.6, 221.7, 8.2, 20.0, 5.9),
    (37.0, 142.1, 221.1, 7.7, 19.4, 5.7),
    (40.0, 145.4, 220.6, 7.3, 19.0, 5.5),
    (64.0, 169.4, 216.5, 4.9, 15.0, 4.4),
    (78.0, 183.4, 213.9, 3.5, 12.2, 3.8),
    (80.3, 185.8, 213.4, 3.2, 11.6, 3.5),
    (82.0, 187.9, 212.8, 2.8, 11.2, 3.1),
    (83.0, 189.9, 212.0, 2.3, 10.4, 2.6),
    (83.3, 191.4, 211.5, 1.9, 9.4, 2.3),
)

# z, передняя кромка стабилизатора, его задняя кромка/ось руля, полутолщина.
FIN = (
    (40.0, 169.0, 227.8, 2.90),
    (43.5, 171.2, 226.8, 2.89),
    (46.6, 173.6, 220.0, 2.85),
    (49.3, 176.0, 206.0, 2.76),
    (52.0, 178.0, 207.1, 2.73),
    (87.7, 207.7, 222.0, 1.98),
    (93.6, 213.1, 224.45, 1.71),
    (95.7, 215.4, 225.32, 1.55),
    (97.0, 217.9, 225.85, 1.31),
)

# z, длина створки по X и удаление её края от плоскости симметрии.
BRAKE = (
    (49.6, 10.5, 5.8), (50.9, 13.8, 7.2),
    (52.0, 14.1, 7.3), (87.7, 10.4, 5.9),
    (93.6, 9.75, 5.65), (96.6, 9.4, 5.5),
)


def _interp(table, v):
    """Линейная интерполяция ряда размеров между соседними сечениями."""
    i = max(1, min(len(table) - 1, bisect_right(table, (v, float('inf')))))
    a, b = table[i - 1:i + 1]
    k = min(1., max(0., (v - a[0]) / (b[0] - a[0])))
    return tuple(x + k * (y - x) for x, y in zip(a[1:], b[1:]))


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
    # Линейно вдоль размаха, без выпучивания или перехлёста за малые хорды.
    return Part.makeLoft(wires, True, True)


def _poly(points):
    return Part.makePolygon([*points, points[0]])


def _wing_wire(y, groove=0.):
    nose, tail, t, flap, band = _interp(WING, y)
    h = tail - flap - nose  # Местная координата шарнира, от носка.
    c = tail - nose
    crest = max(band + .2, .40 * h)
    # Широкий, незаметный в сборке плоский участок снизу служит опорой печати.
    z0 = 8.0
    zend = .18 * t + .68
    zhinge = .37 * t + .42
    nose_z = .46 * t
    land = min(1.25, max(.60, .13 * (h - band)))
    d = min(.42, .10 * t)
    tip = (0., nose_z)
    return _contour(lambda x, z: V(nose + x, y, z0 + z), tip, [
        ((0., .78*t), (.45*band, .88*t-groove), (band, .90*t-groove)),
        ((band + .36*(crest-band), .94*t-groove),
         (crest - .22*(crest-band), t-groove), (crest, t-groove)),
        ((crest + .34*(h-crest), t-groove), (h-land-.6, zhinge+.5),
         (h-land, zhinge+.40)),
        ((h-.44, zhinge+.12),), ((h-.17, zhinge-d),),
        ((h+.17, zhinge-d),), ((h+.46, zhinge+.04),),
        ((h+.24*flap, zhinge), (c-.18*flap, zend+.68), (c, zend+.52)),
        ((c, zend-.52),),
        ((c-.22*flap, zend-.58), (h+.19*flap, .09*t), (h, .09*t)),
        ((h-.16*(h-crest), .09*t), (crest+.24*(h-crest), 0.),
         (crest+.20*(h-crest), 0.)),
        ((.76*crest, 0.),),
        ((.47*crest, 0.), (0., .14*t), tip),
    ])


def _wing_skin():
    # На верхней поверхности — неглубокие стыки крупных панелей/блоков носка.
    stations = {row[0]: 0. for row in WING}
    for y in (26.0, 34.8, 43.7, 53.8, 64.7, 73.6, 79.3):
        stations.update({y-.24: 0., y-.075: .20, y+.075: .20, y+.24: 0.})
    skin = _loft([_wing_wire(y, g) for y, g in sorted(stations.items())])
    # Сквозная щель только между внутренним и внешним элевонами.
    y = 52.0
    _, aft, _, flap, _ = _interp(WING, y)
    slit = Part.makeBox(32., .58, 20., V(aft - flap + .47, y - .29, 4.))
    return skin.cut(slit)


def _wing_paint(x, y, z):
    le, te, t, flap, band = _interp(WING, abs(y))
    q = (x - le) / (te - le)
    if z < 8. + (1.-q) * .46*t + q * (.18*t + .68):
        return BELLY
    if x < le + band:
        return CARBON
    h = te - flap
    if h - min(1.25, max(.60, .13*(h-le-band))) <= x <= h + .46:
        return JOINT
    return IVORY


def _key_wire(center, depth, wide, thick, embed):
    """Восьмиугольное сечение: снятые углы не упираются в скругления гнезда."""
    a, b = wide/2, thick/2
    f = min(.7, .43*b)
    profile = ((-a+f, -b), (a-f, -b), (a, -b+f), (a, b-f),
               (a-f, b), (-a+f, b), (-a, b-f), (-a, -b+f))
    return _poly([embed(center+x, s, depth) for x, s in profile])


def _key(x, width, thick, depth, embed, socket=False):
    # +0.20 на сторону, +0.45 по глубине. Фаска на входном конце шипа.
    if socket:
        return _loft([_key_wire(x, d, width+.4, thick+.4, embed)
                      for d in (-.6, depth+.45)])
    return _loft([_key_wire(x, d, width-2*r, thick-2*r, embed)
                  for d, r in ((-.52, 0.), (depth-.70, 0.), (depth, .39))])


def _fin_wire(z):
    nose, tail, r = _interp(FIN, z)
    c = tail - nose
    band = min(2.4, .18*c)
    aft = .44 * r
    tip = (0., 0.)
    return _contour(lambda x, y: V(nose+x, y, z), tip, [
        ((0., .55*r), (.48*band, .76*r), (band, .81*r)),
        ((.36*c, 1.12*r), (.54*c, r), (c-1.0, aft+.08)),
        ((c, aft),), ((c, -aft),), ((c-1.0, -aft-.08),),
        ((.54*c, -r), (.36*c, -1.12*r), (band, -.81*r)),
        ((.48*band, -.76*r), (0., -.55*r), tip),
    ])


def _blade_wire(z, sign, recess):
    _, hinge, _ = _interp(FIN, z)
    chord, spread = _interp(BRAKE, z)
    start = hinge - 1.20
    # Рамки чёрных панелей выступают с обеих сторон каждой створки.
    # Переменная толщина только поперёк створки; рамка — часть той же оболочки.
    xs = (0., 1.5, 1.78, chord-1.41, chord-1.13, chord)
    radii = (.64, .82, .82-recess, .82-recess, .82, .64)
    pts = []
    for side, pairs in ((1, list(zip(xs, radii))), (-1, list(zip(xs, radii))[::-1])):
        for x, r in pairs:
            axis = .72 + x/chord * (spread-.72)
            pts.append(V(start+x, sign*(axis + side*r), z))
    return _poly(pts)


def _blade(sign):
    # Отдельные светлые поля верхней и нижней половин; поперечная чёрная рамка.
    levels = {row[0]: .25 for row in BRAKE}
    levels.update({49.6: 0., 50.65: 0., 50.9: .25, 71.85: .25, 72.14: 0.,
                   73.48: 0., 73.76: .25, 95.22: .25, 95.50: 0., 96.6: 0.})
    body = _loft([_blade_wire(z, sign, r) for z, r in sorted(levels.items())])
    _, hinge, _ = _interp(FIN, 72.79)
    slit = Part.makeBox(20., 30., .48, V(hinge+1.25, -15., 72.55))
    return body.cut(slit)


def _fin_paint(x, y, z):
    le, hinge, _ = _interp(FIN, z)
    band = min(2.4, .18*(hinge-le))
    if x <= le + band or z > 96.98:
        return CARBON
    if z >= 49.58 and x >= hinge - 1.05:
        c, _ = _interp(BRAKE, z)
        u = x - (hinge - 1.20)
        if u < 1.78 or u > c-1.41 or z < 50.90 or z > 95.22 or 71.85 < z < 73.76:
            return CARBON
    return IVORY


def _mirror(shape):
    return shape.mirror(V(0, 0, 0), V(0, 1, 0))


def _part(name, label, shape, explode, orientation, paint, note):
    solid, = shape.Solids  # OCC может вернуть Compound-обёртку после объединения.
    return dict(id=name, label=label, group='Оперение', shape=solid,
                color=IVORY, explode=explode, orientation=orientation,
                note=note, paint=paint)


def build():
    """Три печатные детали и шесть инструментов для пазов в фюзеляже."""
    skin = _wing_skin()
    cutters = []
    parts = []
    for sign, name, label in ((-1, 'WingPort', 'Левая консоль крыла'),
                              (1, 'WingStarboard', 'Правая консоль крыла')):
        def along_y(x, z, d):
            return V(x, 20.-d, (13.1 if x < 150. else 12.0) + z)

        # Различаются длины сечений и интервалы: перепутать консоли нельзя.
        keys = [(114.+sign, 14.8, 4.3, 5.5), (193.-2*sign, 10.6, 3.2, 4.8)]
        solid = skin.multiFuse([_key(*k, along_y) for k in keys]).removeSplitter()
        sockets = [_key(*k, along_y, socket=True) for k in keys]
        if sign < 0:
            solid = _mirror(solid)
            sockets = [_mirror(s) for s in sockets]
        cutters.extend(sockets)
        parts.append(_part(name, label, solid, (0, 28*sign, 0), (32*sign, -14, 0), _wing_paint,
                           'Консоль уже наклонена от платформы, корень ниже законцовки. '
                           'Поддержки по внутренней и нижней стороне, не на линии элевонов '
                           'и не на кромках шпонок. Проверьте первые островки в слайсере.'))

    def along_z(x, y, d):
        return V(x, y, 40.-d)

    keys = [(184., 12.6, 3.35, 4.4), (215., 9.4, 2.35, 4.4)]
    fixed = _loft([_fin_wire(row[0]) for row in FIN])
    fin = fixed.multiFuse([_blade(-1), _blade(1), *[_key(*k, along_z) for k in keys]])
    cutters.extend(_key(*k, along_z, socket=True) for k in keys)
    parts.append(_part('Fin', 'Киль с раскрытым воздушным тормозом',
                       fin.removeSplitter(), (0, 0, 25), (10, -16, 0), _fin_paint,
                       'Опоры под корневую кромку и низ раскрытых створок. '
                       'Не ставьте контакты на рабочие грани шипов и тонкую заднюю кромку.'))
    return parts, cutters
