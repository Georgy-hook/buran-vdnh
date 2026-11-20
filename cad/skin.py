"""Exterior surface work: paint boundaries, cargo panels and raised museum lettering."""

import math
import os
from pathlib import Path

import FreeCAD as App
import Part

from livery import flag, name_relief
from sections import V, NOSE, box, compound, frame, inset, mid, poly, shell_blank

# Upper boundary of dark nose tiles. The steps and irregular sill are visible on BTS-001.
BELT = [(-2,22.3), (7.8,22.3), (7.8,20.0), (9.65,19.4), (9.65,18.4),
        (11.5,17.68), (11.5,17.22), (13.0,16.92), (13.0,17.68), (14.9,17.70),
        (14.9,18.40), (17.0,18.30), (17.0,19.0), (19.2,18.92), (19.2,19.68),
        (21.3,19.60), (21.3,20.30), (22.45,20.2), (22.45,17.25), (24.55,17.0),
        (24.55,17.75), (26.9,17.67), (26.9,18.43), (29.15,18.15),
        (29.15,20.5), (31.5,20.19), (31.5,20.86), (33.7,20.80), (33.7,21.55),
        (36.,21.52), (36.,22.28), (38.5,22.0), (38.5,25.7), (40.75,25.45),
        (40.75,26.15), (43.05,26.12), (43.05,26.88), (45.35,26.85),
        (45.35,27.60), (46.4,27.55), (46.4,8.25), (47.5,8.25), (47.5,9.75),
        (48.9,9.75), (48.9,10.5), (50.2,10.5), (50.2,8.2), (51.8,8.2),
        (51.8,9.3), (53.0,9.3), (53.0,10.45), (54.3,10.45), (54.3,7.8),
        (55.5,7.8), (55.5,11.45), (57.0,11.45), (57.,6.5), (72.2,6.5)]


def belt_z(x):
    for (x0, a), (x1, b) in zip(BELT, BELT[1:]):
        if x0 <= x < x1:
            return a + (b-a)*(x-x0)/(x1-x0)
    return 6.5


def band(points, half_width):
    # Plane strip with mitred corners, extruded across both sides of the hull.
    normals = []
    for (x, z), (u, v) in zip(points, points[1:]):
        length = math.hypot(u-x, v-z)
        normals.append((-(v-z)/length, (u-x)/length))
    outer, inner = [], []
    for i, (x, z) in enumerate(points):
        a, b = normals[max(0, i-1)], normals[min(i, len(normals)-1)]
        f = half_width/(1+a[0]*b[0]+a[1]*b[1])
        dx, dz = f*(a[0]+b[0]), f*(a[1]+b[1])
        outer.append(V(x+dx, -32, z+dz))
        inner.append(V(x-dx, -32, z-dz))
    return Part.Face(poly(outer+list(reversed(inner)))).extrude(V(0, 64, 0))


def ring_y(x, z, r, width=.34):
    axis, origin = V(0, 1, 0), V(x, -28, z)
    return Part.makeCylinder(r, 56, origin, axis).cut(Part.makeCylinder(r-width, 56, origin, axis))


def nose_tools():
    # Actual upper boundary has TWO sawtooth runs separated by a deep reset.
    # 4543: flank plate bottom, service-panel outer line and small roof panel.
    hatch = [(44.77,24.12),(46.18,24.12),(47.77,23.20),(49.25,20.64),
             (49.25,18.70),(47.75,15.08),(45.4,15.08),(44.75,17.62)]
    outer = Part.Face(poly([V(x,-25,z) for x,z in hatch]))
    inner = Part.Face(poly([V(46.55+(x-46.55)*.90,-25,19.60+(z-19.60)*.947)
                            for x,z in hatch]))
    tools = [band(BELT, .105),
             band([(12.25,12.),(26.95,10.01),(26.95,20.0)],.11),
             outer.cut(inner).extrude(V(0,50,0))]
    for y in (-5.34,5.11):
        tools.append(box(8.23,y,19.,11.12,.23,9.9))
    tools.append(box(19.15,-5.3,22.,.20,10.6,7.))
    tools.extend([box(26.85,-25,10.05,.22,50,31),box(57.08,-25,5.88,.23,50,40)])
    # Limit cut depth on the changing 3-D contours, including near the round cap.
    limiter = shell_blank([inset(s, .34, .32, .32) for s in NOSE])
    return [tools[0].fuse(tools[1:]).cut(limiter).removeSplitter()]


def side_panel(x, z, w, h, side, width=.30):
    # The flush inspection covers in frame 4537 have eased or fully oblong ends.
    def contour(offset, radius):
        x0, x1 = x+offset, x+w-offset
        z0, z1 = z+offset, z+h-offset
        r = radius
        k = 2**-.5
        def v(u, h0):
            return V(u, side*20.45, h0)
        a, b, c, d = v(x0+r,z0), v(x1-r,z0), v(x1,z0+r), v(x1,z1-r)
        e, f, g, j = v(x1-r,z1), v(x0+r,z1), v(x0,z1-r), v(x0,z0+r)
        return Part.Wire([Part.makeLine(a,b), Part.Arc(b,v(x1-r+r*k,z0+r-r*k),c).toShape(),
                          Part.makeLine(c,d), Part.Arc(d,v(x1-r+r*k,z1-r+r*k),e).toShape(),
                          Part.makeLine(e,f), Part.Arc(f,v(x0+r-r*k,z1-r+r*k),g).toShape(),
                          Part.makeLine(g,j), Part.Arc(j,v(x0+r-r*k,z0+r-r*k),a).toShape()])
    radius = min(1.35,.40*h,.40*w)
    outer = Part.Face(contour(0,radius))
    inner = Part.Face(contour(width,radius-width))
    return outer.cut(inner).extrude(V(0,-side*.72,0))


def panel_tools(x0, x1):
    tools = []
    start, end = max(x0, 72), min(x1, 204)
    if end > start:
        tools.append(box(start-.01, -.26, 39.55, end-start+.02, .52, 2))
        for side in (-1, 1):
            y = 19.63 if side > 0 else -20.8
            tools.append(box(start, y, 25.55, end-start, 1.17, .42))
    for x in (76.7, 98.8, 121.5, 145, 180.8, 201.6, 225.5):
        if not x0+.6 < x < x1-.6:
            continue
        inner = Part.Face(frame(inset(mid(x-.1), .34, .32, .35))).extrude(V(.7, 0, 0))
        tools.append(box(x, -24, 26.7, .36, 48, 15).cut(inner))
    # Paired shallow fastener seats below the split lines of the visible side panels.
    # Only the large fittings are represented at 1:144; no indiscriminate rivet grid.
    for x in (82.4, 100.5, 123.2, 146.6, 161.7, 188.0, 202.8):
        if not x0+.6 < x < x1-.6:
            continue
        for side in (-1, 1):
            for offset in (0, .95):
                centre = V(x+offset,side*20.12,24.52)
                tools.append(Part.makeCylinder(.225, .34, centre, V(0,-side,0)))
    for x, z, w, h in [(79.6, 15.0, 4.5, 4.1), (85.6, 15.0, 4.5, 4.1),
                       (105.1, 20.5, 4.3, 1.7), (139.7, 20.5, 4.3, 1.7),
                       (146.8, 16.5, 3.5, 1.35), (158.0, 17.8, 1.4, 2.4),
                       (186.8, 19.1, 3.15, 1.32), (190.9, 15.9, 3.25, 1.45),
                       (201.0, 19.1, 1.15, 1.85), (205.2, 18.4, 5.0, 2.0),
                       (220.4, 13.0, 4.2, 6.6)]:
        if x0 < x and x+w < x1:
            tools.extend(side_panel(x, z, w, h, s) for s in (-1, 1))
    if x0 >= 160:
        # Perituss / Moscow 2026-03-31 25: two light panel scores below the
        # shoulder strap, with close-set pairs of small fasteners between.
        # Trace them on the fixed collar only. The separate bay roof turns.
        for side in (-1, 1):
            for x, end, z in ((160.2, 198.65, 26.82), (160.2, 198.65, 27.43),
                              (160.2, 198.28, 28.89)):
                y = 19.64 if side > 0 else -20.28
                tools.append(box(x, y, z, end-x, .64, .17))
            for x in (169.76, 170.19, 181.36, 181.79, 193.42, 193.85):
                for z in (27.04, 27.32):
                    tools.append(Part.makeCylinder(.088, .39, V(x,side*20.20,z), V(0,-side,0)))
        # Rounded cover with a circular centre, aft of the word and flag;
        # a second round cover is captured on both sides in 4508 and 4548.
        for xc, zc, r in ((222.5,16.5,.92),(212.0,19.8,1.18),(199.8,22.6,.85)):
            for side in (-1, 1):
                axis = V(0,-side,0)
                ctr = V(xc,side*20.30,zc)
                outer = Part.makeCylinder(r,.51,ctr,axis)
                tools.append(outer.cut(Part.makeCylinder(r-.17,.53,ctr,axis)))
    return tools


def hinges(x0, x1):
    shapes = []
    if x0 >= 160:
        # Distinct folded tabs on the fixed aft collar. Width and spacing
        # follow the photo relative to its 21.9 mm miniature wordmark.
        for x in (170.98, 185.43):
            for s in (-1, 1):
                y = 19.37 if s > 0 else -20.12
                shapes.append(box(x-.52, y, 28.93, 1.04, .75, .97))
                for dx in (-.51, .10):
                    shapes.append(Part.makeCylinder(.285, .42, V(x+dx,s*19.96,29.63), V(1,0,0)))
        return shapes
    for x in range(79, 199, 9):
        if not x0 < x < x1-3:
            continue
        for s in (-1, 1):
            y = 19.80 if s>0 else -20.15
            shapes.append(box(x-.16, y, 25.96, 2.88, .35, 1.04))
            for dx in (0, 1.42):
                shapes.append(Part.makeCylinder(.415, 1.1, V(x+dx,s*20.04,26.54), V(1,0,0)))
    return shapes


def lettering(text, size, x0, z0, side, width=None):
    # Small upright serif «СССР» under the flag, as distinct from the sloped wordmark.
    paths = [os.environ.get('BURAN_FONT', ''),
             '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf',
             '/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf',
             'C:/Windows/Fonts/timesbd.ttf']
    font = next((p for p in paths if p and Path(p).is_file()), None)
    if not font:
        raise FileNotFoundError('Set BURAN_FONT to a Cyrillic bold serif TrueType font')
    glyphs = Part.makeWireString(text, font, size)
    faces = [Part.makeFace(w, 'Part::FaceMakerBullseye') for w in glyphs if w]
    bb = compound(faces).BoundBox
    # Local glyph X follows screen-right on each side: never mirror the word itself.
    start = x0 if side < 0 else x0+(width or bb.XLength)
    stretch = (width or bb.XLength)/bb.XLength
    out = []
    for face in faces:
        face = face.copy()
        face.translate(V(-bb.XMin, -bb.YMin, 0))
        if abs(stretch-1) > .001:
            m = App.Matrix()
            m.A11 = stretch
            face = face.transformGeometry(m)
        face.rotate(V(), V(1, 0, 0), 90)
        if side > 0:
            face.rotate(V(), V(0, 0, 1), 180)
        face.translate(V(start, side*19.84, z0))
        out.append(face.extrude(V(0, side*.46, 0)))
    return out


def markings():
    shapes = []
    for s in (-1, 1):
        shapes.extend(name_relief(s))
        shapes.extend(lettering('СССР', 1.90, 190.2, 18.22, s, 6.8))
        shapes.append(flag(s))
    return shapes
