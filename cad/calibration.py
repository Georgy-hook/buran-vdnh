"""Small pin and stepped fit gauge, separate from the 12-piece assembly."""

import FreeCAD as App
import Part

from sections import V, box, cut, fuse, poly


def build():
    # As on the fuselage splice, the pin's long axis is X. One, two or three
    # embossed ticks identify the slots without making a tiny text label.
    gauge = box(0, -13.6, 0, 5.8, 27.2, 11.4)
    apertures, ticks = [], []
    for index, (y, clearance) in enumerate([(-8.6, .1), (0, .2), (8.6, .3)], 1):
        apertures.append(box(-.2, y-1.6-clearance, 3.7-clearance,
                             6.2, 3.2+2*clearance, 4.4+2*clearance))
        for n in range(index):
            ticks.append(box(5.65, y+(n-(index-1)/2)*1.05-.23, 8.93, .55, .46, 1.4))
    gauge = fuse(cut(gauge, apertures), ticks)
    grip = box(-3.6, -4, 0, 3.65, 8, 8.5)
    def face(x, wy, wz):
        return poly([V(x, i*wy/2, 4.25+j*wz/2) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]])
    pin = Part.makeLoft([face(-.2,3.2,4.4), face(5.7,3.2,4.4), face(6.4,2.35,3.55)], True, True)
    key = fuse(grip, [pin])
    return [(dict(id=key_id, shape=shape, label=label, orientation=(16,49,0)))
            for key_id, shape, label in [('FitGauge',gauge,'Гребёнка зазоров'), ('FitKey',key,'Пробная шпонка')]]
