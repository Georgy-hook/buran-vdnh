"""Scale exterior and open, keyed hull sections for the VDNKh BTS-001 display kit."""

import math
import Part

from cockpit import cockpit, glazing_color
from nose_detail import cover_color, covers, tip_cap, tip_color
from nose_tiles import DevelopedBelly
from forebody_skin import laminations, panel_color
from fairing import color as fairing_color, shoulder
from museum_stern import paint as stern_finish, restore as restore_stern
from belly import belly_color, engravers, flap_tools, skirt_height, skirt_tools
from bay_liner import lining_color
from baydoors import operations as bay_opening
from sidewall import color as sidewall_color, lids as flank_lids, seams as flank_seams
from sections import (V, NOSE, PORCELAIN, TILES, TILE_EDGE, RED, box, compound,
                      cut, fuse, inset, item, mid, poly, shell_blank, station_at)
from skin import belt_z, hinges, markings, nose_tools, panel_tools


class Work:
    """Record the same cutting tools for FreeCAD's native, editable feature history."""

    def __init__(self, stations):
        self.stations = stations
        self.shape = shell_blank(stations)
        self.operations = []

    def apply(self, kind, label, tools):
        if tools:
            if kind == 'engrave':
                # Disjoint grooves are one compound operand. Keep the planar
                # cutting faces; refining all tile lands changes no geometry.
                self.shape = self.shape.cut(tools, 1.e-7)
            else:
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
            # The rear side cheek extends past this joint. Clear the heel
            # of the cover key there, not just the inserted length of the pin.
            lead = .90 if sign < 0 else .30
            shapes.append(Part.makeLoft([wire(-lead, wy+2*clearance, wz+2*clearance),
                                         wire(5.05, wy+2*clearance, wz+2*clearance)], True, True))
        else:
            shapes.append(Part.makeLoft([wire(-.65, wy, wz), wire(3.90, wy, wz),
                                         wire(4.60, wy-.85, wz-.85)], True, True))
    return shapes


def local_tools(tools, x0, x1):
    return [s for s in tools if s.BoundBox.XMin < x1 and s.BoundBox.XMax > x0]


def nose_color(panes, lids, belly):
    def paint(x, y, z):
        # Through the open Ø4.8 drain one sees the hollow casting's inner
        # roof and front bulkhead. This envelope lies INSIDE the separate
        # core loft (4.8 mm narrower and 3.6 mm below the external crown).
        # It must not darken the external six-lid tray or the curved brow.
        if 13.99 <= x <= 28. and z > 7.:
            _, width, _, _, _, roof = station_at(x)
            if abs(y) < width - 4.5 and z < roof - 3.25:
                return '#373c3f'
        if 28 < x < 57 and z > 26:
            shade = glazing_color(panes, V(x, y, z))
            if shade:
                return shade
        if 7.5 < x < 49.0 and z > 9.40:
            shade = cover_color(lids, V(x,y,z))
            if shade:
                return shade
        if x < 7.8:
            shade = tip_color(x, y, z)
            if shade:
                return shade
        dark = z <= belt_z(x)+.03
        shade = panel_color(x, y, z, dark)
        if shade:
            return shade
        if dark:
            return belly.paint(x, y, z)
        return PORCELAIN
    return paint


def shell_color(x, y, z):
    if abs(y)<16.03 and 73.8<x<189.4 and z>3.1:
        inside = lining_color(x,y,z)
        if inside:
            return inside
    if abs(y) > 20.015 and 162.5 < x < 187.5 and 13.2 < z < 22.72:
        return '#23272b'
    if 190.0 < x < 197.4 and abs(y) > 20.01 and 18.0 < z < 25.1:
        return '#d1ad71' if abs(y) > 20.35 else RED
    if x > 200 and abs(y) > 18.75 and z > 21.43:
        accent = fairing_color(x,y,z)
        if accent:
            return accent
    if z < skirt_height(x)+.04:
        return belly_color(x,y,z) if z<6.55 and 72.<=x<=232. else TILES
    if 72.<x<232. and abs(y)>19.5:
        face = sidewall_color(x,y,z)
        if face:
            return face
    if abs(y)>20.025 and 26.1 < z < 27.05:
        return '#c7c7bd'
    return PORCELAIN


def fore(tools):
    work = Work(NOSE)
    window_cuts, panes = cockpit(work.shape)
    lid_cuts, lids = covers(work.shape)
    belly = DevelopedBelly(work.shape)
    courses, joints = belly.cuts()
    cup, reveal = tip_cap(work.shape)
    crown, cheek = laminations(work.shape)
    inside = [inset(station_at(x), 4.8, 3.0, 3.6) for x in (14, 22, 34, 49, 62, 72, 73)]
    # The large keyed end is open; the second, vented opening is low on the nose.
    # Core starts aft of the cap, and leaves material locally for the nose gear socket.
    core = shell_blank(inside)
    core = core.cut(box(47, -5.6, -1, 14.8, 11.2, 13))
    drain = Part.makeCylinder(2.4, 18, V(15.1, 0, -3), V(0, 0, 1))
    work.apply('add', 'Гнутые листы лба и свода · фартук под остеклением', crown)
    # The metal doubler laps the painted mask, not the reverse. Cutting its
    # sawtooth through the doubler would slit a smooth sheet into fragments.
    work.apply('cut', 'Маска в два уступа, люки и стыки листовых панелей', nose_tools())
    work.apply('add', 'Щёчные щиты, накладки люков и силовой пояс кабины', cheek)
    work.apply('add', 'Овальный колпак с выступающей кромкой', [cup])
    work.apply('cut', 'Наклонная кольцевая канавка вокруг колпака', [reveal])
    work.apply('cut', 'Открытая полость и слив в нижней панели', [core, drain])
    work.apply('cut', 'Остекление кабины · глухие плоские выборки в обводе и тонкий переплёт', window_cuts)
    work.apply('engrave', 'Днище носа · продольные пояса по развёртке к центроплану', [courses])
    work.apply('engrave', 'Днище носа · короткие поперечные стыки вразбежку', [joints])
    work.apply('cut', 'Глухие крышки бортовых панелей и верхние два ряда', lid_cuts)
    work.apply('add', 'Передний разъём · две шпонки с заходными фасками', keys(72))
    work.apply('cut', 'Ложе носовой стойки', local_tools(tools, 0, 72))
    return work.finish('Nose', 'Нос и кабина экипажа', PORCELAIN, (-37,0,5), (12,52,0),
                       'Поддержки — на торце и снизу, не на стёклах. Промыть из открытого торца через слив Ø4,8 мм.',
                       paint=nose_color(panes,lids,belly))


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
    work.apply('cut', 'Пояса бортовых листов, стыки и глухие продолговатые окна', flank_seams(x0,x1))
    work.apply('add', 'Съёмные бортовые крышки с отбортовкой и углублённым крепежом', flank_lids(x0,x1))
    if aft:
        work.apply('cut', 'Ступенчатое поле под кормовой накладкой', skirt_tools(x0,x1))
    work.apply('add', 'Наружные петли створок', hinges(x0,x1))
    for kind, label, shapes in bay_opening(x0, x1):
        work.apply(kind, label, shapes)
    if aft:
        work.apply('add', 'Бортовая надпись и флаг · обе стороны', markings())
        work.apply('add', 'Кормовые накладки · рельеф боковин, скоса и торца', [shoulder(-1), shoulder(1)])
    else:
        work.apply('add', 'Задний разъём · две шпонки', keys(x1))
    joint_tools = keys(x0, female=True) + local_tools(tools, x0,x1)
    if aft:
        joint_tools += keys(232, female=True, sign=-1)
    work.apply('cut', 'Приёмные гнёзда секций и навесных узлов', joint_tools)
    courses, cross = engravers(x0, x1)
    work.apply('engrave', 'Теплозащита · пояса по дуге днища', [courses])
    work.apply('engrave', 'Теплозащита · короткие швы со сдвигом в полплитки', [cross])
    if aft:
        return work.finish('Aft', 'Кормовая секция с бортовой маркировкой', PORCELAIN, (29,0,2), (13,-53,0),
                           'Защищайте буквы и боковые накладки. Сквозь оба торца промыть и досветить полость до сборки.', paint=shell_color)
    return work.finish('Bay', 'Центроплан и створки грузового отсека', PORCELAIN, (0,0,3), (16,49,0),
                       'Печатать открытым торцом вниз под наклоном. Опоры на нижние кромки; шпонки и пазы оставить без краски.', paint=shell_color)


def flap_parts():
    # The modern walkway hides the back; the transfer photographs show it bare.
    skin = shell_blank([mid(232), (235.2, 19.8, .18, 6.5, 26.5, 39.45)])
    # The fixed fairings extend past the hull joint. Give the cover two cutaways.
    skin = cut(skin, [box(231.8, y, 21.24, 4.0, 6.5, 13.67) for y in (-23,16.5)])
    skin = cut(skin, skirt_tools(232.,235.2))
    skin = fuse(skin, keys(232, sign=-1))
    skin = restore_stern(skin)
    # A pair of rectangular spigots couples the removable lower panel to the back wall.
    skin = cut(skin, [box(231.8, y-.20, 2.55-.20, 4, 4.4, 2.7) for y in (-10,6)])
    cover = item('Stern', 'Кормовой щит музейного макета', skin, PORCELAIN,
                 (51,0,0), (7,-40,5), 'Облик торца до переезда на ВДНХ: две глухие чаши, овальный щит и верхний обтекатель. '
                 'На ВДНХ за переходом торец не виден. Опоры ставить на внутреннюю сторону, чаши промыть.',
                 paint=lambda x,y,z: stern_finish(x,y,z) or shell_color(x,y,z))
    def foil(x, span, bottom, thick):
        return poly([V(x,-span+1,bottom), V(x,span-1,bottom), V(x,span,bottom+.48),
                     V(x,span-.2,bottom+thick), V(x,-span+.2,bottom+thick), V(x,-span,bottom+.48)])
    flap = Part.makeLoft([foil(235.2, 14.9, 1.9, 3.75), foil(246.6, 14.6, 2.15, 2.1),
                          foil(252.75, 13.4, 2.80, 1.05)], True, True)
    flap = fuse(flap, [box(232.1, y, 2.55, 3.6, 4, 2.30) for y in (-10,6)])
    flap = cut(flap, [box(238.0, -16, 4.55, .38, 32, 1.5), box(239,-.21,4.15,13,.42,1.9)])
    flap = cut(flap, flap_tools())
    panel = item('LowerFlap', 'Нижний кормовой щиток', flap, TILES, (69,0,-8),
                 (32,12,0), 'Начать с внутренней кромки; не ставить опоры на два шипа.')
    return cover, panel


def build(tools):
    return [fore(tools), trunk(tools, False), trunk(tools, True), *flap_parts()]
