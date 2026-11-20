"""Scale exterior and open, keyed hull sections for the VDNKh BTS-001 display kit."""

import math
import Part

from cockpit import cockpit, glazing_color
from sections import (V, NOSE, PORCELAIN, TILES, TILE_EDGE, RED, box, compound,
                      cut, frame, fuse, inset, item, mid, poly, shell_blank, station_at)
from skin import belt_z, hinges, markings, nose_tools, panel_tools, ring_y, side_panel


class Work:
    """Record the same cutting tools for FreeCAD's native, editable feature history."""

    def __init__(self, stations):
        self.stations = stations
        self.shape = shell_blank(stations)
        self.operations = []

    def apply(self, kind, label, tools):
        if tools:
            self.shape = (cut if kind == 'cut' else fuse)(self.shape, tools)
            self.operations.append((kind, label, tools))

    def finish(self, *args, **kwargs):
        result = item(*args[:2], self.shape, *args[2:], **kwargs)
        result['construction'] = (self.stations, self.operations)
        return result


def keys(x, female=False, sign=1):
    # Different vertical centres prevent upside-down or 180-degree reassembly.
    clearance = .20 if female else 0
    shapes = []
    for yc, zc, wy, wz in [(-17.0, 14.0, 3.2, 4.4), (17.0, 21.2, 3.2, 4.4)]:
        def wire(t, dy, dz):
            return poly([V(x+t*sign, yc+i*dy/2, zc+j*dz/2)
                         for i, j in [(-1,-1), (1,-1), (1,1), (-1,1)]])
        if female:
            shapes.append(Part.makeLoft([wire(-.30, wy+2*clearance, wz+2*clearance),
                                         wire(5.05, wy+2*clearance, wz+2*clearance)], True, True))
        else:
            shapes.append(Part.makeLoft([wire(-.65, wy, wz), wire(3.90, wy, wz),
                                         wire(4.60, wy-.85, wz-.85)], True, True))
    return shapes


def local_tools(tools, x0, x1):
    return [s for s in tools if s.BoundBox.XMin < x1 and s.BoundBox.XMax > x0]


def nose_color(panes):
    def paint(x, y, z):
        if 29 < x < 60 and z > 30:
            shade = glazing_color(panes, V(x, y, z))
            if shade:
                return shade
        if z <= belt_z(x)+.03 or x < 2.5:
            return TILE_EDGE if x < 2.5 else TILES
        return PORCELAIN
    return paint


def shell_color(x, y, z):
    if abs(y) >= 19.94 and 163.0 < x < 187 and 17.4 < z < 25.3:
        if abs(y) > 20.015:
            return '#23272b'
    if 190.0 < x < 197.4 and abs(y) > 20.01 and 18.0 < z < 25.1:
        return RED
    if abs(y) > 21.0 and x > 200 and z > 23:
        for u in (216.8, 221.4, 226, 230.6):
            if (x-u)**2+(z-29.6)**2 < 1.52**2 or (x > 233 and abs(y)>21.7 and z<31):
                return '#343b3e'
    if z < 6.51 or (x >= 219 and z < min(15.1, 6.5+math.floor((x-218)/2.1)*1.3)):
        return TILES
    if abs(y)>19.94 and 26.1 < z < 27.05:
        return '#c7c7bd'
    return PORCELAIN


def fore(tools):
    work = Work(NOSE)
    inside = [inset(station_at(x), 4.8, 3.0, 3.6) for x in (14, 22, 34, 49, 62, 72, 73)]
    # The large keyed end is open; the second, vented opening is low on the nose.
    # Core starts aft of the cap, and leaves material locally for the nose gear socket.
    core = shell_blank(inside)
    core = core.cut(box(47, -5.6, -1, 14.8, 11.2, 13))
    drain = Part.makeCylinder(2.4, 18, V(15.1, 0, -3), V(0, 0, 1))
    work.apply('cut', 'Открытая полость и слив в нижней панели', [core, drain])
    window_block, panes, _ = cockpit()
    # Only the external canopy shell is added: do not close up the hollow interior.
    work.apply('add', 'Гранёный фонарь · рамки и углублённые стёкла', [window_block.cut(core)])
    work.apply('cut', 'Ступенчатая маска, окантовки и стыки носа', nose_tools())
    work.apply('add', 'Передний разъём · две шпонки с заходными фасками', keys(72))
    work.apply('cut', 'Ложе носовой стойки', local_tools(tools, 0, 72))
    return work.finish('Nose', 'Нос и кабина экипажа', PORCELAIN, (-37,0,5), (12,52,0),
                       'Поддержки — на торце и снизу, не на стёклах. Промыть из открытого торца через слив Ø4,8 мм.',
                       paint=nose_color(panes))


def shoulder(side):
    outline = [(198, 26.5), (209, 24.1), (231.9, 24.1), (234.6, 25.1),
               (234.6, 32.8), (231.8, 34.0), (210, 33.3), (199.4, 30.2)]
    inner = poly([V(x, side*17.6, z) for x,z in outline])
    # The outboard side of the fairing has a tapered front and a flat face aft.
    # Build as an x-z extrusion clipped by a vertical wedge (planar end faces).
    block = Part.Face(inner).extrude(V(0, side*7.5, 0))
    footprint = [(197, 17), (235.5, 17), (235.5, 24.4), (212.2, 24.4), (197, 19.9)]
    plan = Part.Face(poly([V(x, side*y, 21) for x,y in footprint])).extrude(V(0,0,16))
    block = block.common(plan)
    sockets = [Part.makeCylinder(1.38, 1.35, V(x, side*24.72, 29.6), V(0,-side,0))
               for x in (216.8, 221.4, 226.0, 230.6)]
    sockets.extend(Part.makeCylinder(.96, 1.43, V(234.95, side*21.8, z), V(-1,0,0))
                   for z in (27.2, 30.3))
    return cut(block, sockets)


def trunk(tools, aft):
    x0, x1 = (160, 232) if aft else (72, 160)
    work = Work([mid(x0), mid(x1)])
    inner = [inset(mid(x), 4.8, 3.0, 3.6) for x in (x0-1, x1+1)]
    core = shell_blank(inner)
    if aft:
        bosses = [box(163, y, -1, 16, 9.7, 13) for y in (-17.8, 8.1)]
        core = cut(core, bosses)
    work.apply('cut', 'Сквозной промывочный канал', [core])
    work.apply('cut', 'Расшивка створок, люков и днища', panel_tools(x0,x1))
    work.apply('add', 'Наружные петли створок', hinges(x0,x1))
    if aft:
        work.apply('add', 'Бортовая надпись и флаг · обе стороны', markings())
        work.apply('add', 'Кормовые накладки · глухие лунки 4 + 2', [shoulder(-1), shoulder(1)])
    else:
        work.apply('add', 'Задний разъём · две шпонки', keys(x1))
    joint_tools = keys(x0, female=True) + local_tools(tools, x0,x1)
    if aft:
        joint_tools += keys(232, female=True, sign=-1)
    work.apply('cut', 'Приёмные гнёзда секций и навесных узлов', joint_tools)
    if aft:
        return work.finish('Aft', 'Кормовая секция с бортовой маркировкой', PORCELAIN, (29,0,2), (13,-53,0),
                           'Защищайте буквы и боковые накладки. Сквозь оба торца промыть и досветить полость до сборки.', paint=shell_color)
    return work.finish('Bay', 'Центроплан и створки грузового отсека', PORCELAIN, (0,0,3), (16,49,0),
                       'Печатать открытым торцом вниз под наклоном. Опоры на нижние кромки; шпонки и пазы оставить без краски.', paint=shell_color)


def flap_parts():
    # Neutral removable back wall: the museum gallery hides this area in photographs.
    skin = shell_blank([mid(232), (235.2, 19.8, .18, 6.5, 26.5, 39.45)])
    # The fixed fairings extend past the hull joint. Give the cover two cutaways.
    skin = cut(skin, [box(231.8, y, 23.0, 3.2, 6.5, 11.9) for y in (-23,16.5)])
    skin = fuse(skin, keys(232, sign=-1))
    rear = box(234.65, -11, 10.2, 1.0, 22.0, 20.0)
    rear_inner = box(234.5, -10.45, 10.75, 1.4, 20.90, 18.90)
    skin = cut(skin, [rear.cut(rear_inner)])
    # A pair of rectangular spigots couples the removable lower panel to the back wall.
    skin = cut(skin, [box(231.8, y-.20, 2.55-.20, 4, 4.4, 2.7) for y in (-10,6)])
    cover = item('Stern', 'Кормовая заглушка музейного перехода', skin, PORCELAIN,
                 (51,0,0), (7,-40,5), 'Центральный торец на фото скрыт переходом: здесь нейтральная замыкающая панель. Опоры с внутренней стороны.', paint=shell_color)
    def foil(x, span, bottom, thick):
        return poly([V(x,-span+1,bottom), V(x,span-1,bottom), V(x,span,bottom+.48),
                     V(x,span-.2,bottom+thick), V(x,-span+.2,bottom+thick), V(x,-span,bottom+.48)])
    flap = Part.makeLoft([foil(235.2, 14.9, 1.9, 3.75), foil(246.6, 14.6, 2.15, 2.1),
                          foil(252.75, 13.4, 2.80, 1.05)], True, True)
    flap = fuse(flap, [box(232.1, y, 2.55, 3.6, 4, 2.30) for y in (-10,6)])
    flap = cut(flap, [box(238.0, -16, 4.55, .38, 32, 1.5), box(239,-.21,4.15,13,.42,1.9)])
    panel = item('LowerFlap', 'Нижний кормовой щиток', flap, TILES, (69,0,-8),
                 (32,12,0), 'Начать с внутренней кромки; не ставить опоры на два шипа.')
    return cover, panel


def build(tools):
    return [fore(tools), trunk(tools, False), trunk(tools, True), *flap_parts()]
